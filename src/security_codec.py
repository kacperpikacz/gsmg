"""Security, encoding, and decoding helpers for the GSMG puzzle."""

from __future__ import annotations

import hashlib
import re
import subprocess


DEFAULT_CIPHER = "aes-256-cbc"
DEFAULT_DIGEST = "sha256"
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def compact(text: str) -> str:
    return "".join(text.split())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_checksum_bits(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in sha256_bytes(data))


def decrypt_openssl_blob(
    blob: str,
    password: str,
    cipher: str = DEFAULT_CIPHER,
    digest: str = DEFAULT_DIGEST,
    pbkdf2: bool = False,
) -> str:
    plaintext = decrypt_openssl_blob_bytes(
        blob,
        password,
        cipher=cipher,
        digest=digest,
        pbkdf2=pbkdf2,
    )
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError:
        return plaintext.decode("latin1")


def decrypt_openssl_blob_bytes(
    blob: str,
    password: str,
    cipher: str = DEFAULT_CIPHER,
    digest: str = DEFAULT_DIGEST,
    pbkdf2: bool = False,
) -> bytes:
    cmd = [
        "openssl",
        "enc",
        "-d",
        "-a",
        "-A",
        f"-{cipher}",
        "-md",
        digest,
    ]
    if pbkdf2:
        cmd.append("-pbkdf2")
    cmd.extend(["-pass", f"pass:{password}"])

    proc = subprocess.run(cmd, input=compact(blob).encode(), capture_output=True)
    if proc.returncode != 0:
        error = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(error or "OpenSSL decryption failed")
    return proc.stdout


def is_openssl_blob(text: str) -> bool:
    value = compact(text)
    return value.startswith("U2FsdGVkX1") and bool(re.fullmatch(r"[0-9A-Za-z+/=]+", value))


def message_bits_for_puzzle(message: str) -> str:
    payload = message.encode("utf-8")
    return "".join(f"{byte:08b}" for byte in payload)


def decode_ascii_prefix_from_bits(bits: str) -> str:
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i: i + 8]
        if len(byte) != 8:
            break
        value = int(byte, 2)
        if value < 32 or value > 126:
            break
        chars.append(chr(value))
    return "".join(chars)


def decode_spiral_grid_text(grid_text: str, one: str = "b", zero: str = "y") -> str:
    lines = [line.strip() for line in grid_text.splitlines() if line.strip()]
    out: list[str] = []

    while lines:
        left, lines = _take_left(lines)
        out.extend(left)
        if not lines:
            break
        bottom, lines = _take_bottom(lines)
        out.extend(bottom)
        if not lines:
            break
        right, lines = _take_right(lines)
        out.extend(right)
        if not lines:
            break
        top, lines = _take_top(lines)
        out.extend(top)

    bits = "".join(out).replace(one, "1").replace(zero, "0")
    return decode_ascii_prefix_from_bits(bits)


def _take_top(lines: list[str]) -> tuple[str, list[str]]:
    return lines[0][::-1], lines[1:]


def _take_left(lines: list[str]) -> tuple[str, list[str]]:
    return "".join(line[0] for line in lines), [line[1:] for line in lines]


def _take_bottom(lines: list[str]) -> tuple[str, list[str]]:
    return lines[-1], lines[:-1]


def _take_right(lines: list[str]) -> tuple[str, list[str]]:
    return "".join(line[-1] for line in reversed(lines)), [line[:-1] for line in lines]


def decode_ebcdic_mojibake(text: str | bytes) -> str:
    if isinstance(text, bytes):
        text = text.decode("latin1")
    return text.encode("cp273", errors="replace").decode("latin1")


def beaufort_decrypt(ciphertext: str, key: str) -> str:
    out = []
    key = key.lower()
    key_i = 0
    for char in ciphertext.lower():
        if "a" <= char <= "z":
            c = ord(char) - ord("a")
            k = ord(key[key_i % len(key)]) - ord("a")
            out.append(chr((k - c) % 26 + ord("a")))
            key_i += 1
        else:
            out.append(char)
    return "".join(out)


def make_checkerboard(alphabet: str, row_digits: str) -> dict[str, str]:
    if len(row_digits) != 2 or len(set(row_digits)) != 2:
        raise ValueError("row_digits must contain two unique digits")

    columns = "0123456789"
    if any(d not in columns for d in row_digits):
        raise ValueError("row_digits must only contain decimal digits")

    expected_len = 8 + 10 * len(row_digits)
    if len(alphabet) != expected_len:
        raise ValueError(f"alphabet must contain {expected_len} characters")

    table: dict[str, str] = {}
    chars = iter(alphabet.upper())
    for col in columns:
        if col not in row_digits:
            table[col] = next(chars)
    for row in row_digits:
        for col in columns:
            table[row + col] = next(chars)
    return table


def checkerboard_decrypt(digits: str, alphabet: str, row_digits: str) -> str:
    table = make_checkerboard(alphabet, row_digits)
    out = []
    i = 0
    while i < len(digits):
        if digits[i] in row_digits:
            token = digits[i : i + 2]
            i += 2
        else:
            token = digits[i]
            i += 1
        try:
            out.append(table[token])
        except KeyError as exc:
            raise ValueError(f"invalid checkerboard token at offset {i}: {token!r}") from exc
    return "".join(out)


def is_digit_riddle(text: str) -> bool:
    value = compact(text)
    return len(value) >= 50 and value.isdigit()


def is_mojibake_block(text: str) -> bool:
    if len(text) < 100 or is_digit_riddle(text) or is_openssl_blob(text):
        return False
    value = compact(text)
    non_ascii = sum(not char.isascii() for char in value)
    punctuation = sum(not char.isalnum() for char in value)
    ascii_letters = sum(char.isascii() and char.isalpha() for char in value)
    return non_ascii > 20 and punctuation > ascii_letters


def is_readable_block(text: str) -> bool:
    if is_digit_riddle(text) or is_openssl_blob(text) or is_mojibake_block(text):
        return False
    return sum(char.isalpha() for char in text) >= 20 and text.count(" ") >= 3


def base58_encode(data: bytes, alphabet: str = BASE58_ALPHABET) -> str:
    value = int.from_bytes(data, "big")
    encoded = ""
    while value:
        value, rem = divmod(value, 58)
        encoded = alphabet[rem] + encoded

    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    return alphabet[0] * leading_zeroes + (encoded or alphabet[0])


def ripemd160(data: bytes) -> bytes:
    digest = hashlib.new("ripemd160")
    digest.update(data)
    return digest.digest()


def hash160(data: bytes) -> bytes:
    return ripemd160(sha256_bytes(data))


def base58check_encode(prefix: bytes, payload: bytes) -> str:
    versioned_payload = prefix + payload
    checksum = sha256_bytes(sha256_bytes(versioned_payload))[:4]
    return base58_encode(versioned_payload + checksum)
