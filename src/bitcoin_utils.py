"""Bitcoin, secp256k1, and BIP39 helpers for GSMG reports."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from ecdsa import SECP256k1

import phase_api
import security_codec


DEFAULT_BIP39_WORDLIST = "bip39-english.txt"
HALF_PRIVATE_KEY_HEX = "dadd32d754e583d4143e1cca2de6acb50cf988b8776667e283f32b0168d26f6a"
SECP256K1_GENERATOR = SECP256k1.generator
SECP256K1_ORDER = SECP256k1.order


def normalized_ascii_letters(text: str) -> str:
    return "".join(char for char in text.lower() if "a" <= char <= "z")


def find_default_bip39_wordlist(explicit_path: Path | None = None) -> Path | None:
    if explicit_path:
        return explicit_path if explicit_path.exists() else None

    candidates = [
        phase_api.project_path("assets", DEFAULT_BIP39_WORDLIST),
        phase_api.project_path(DEFAULT_BIP39_WORDLIST),
        Path(__file__).with_name(DEFAULT_BIP39_WORDLIST),
    ]
    return next((path for path in candidates if path.exists()), None)


def load_bip39_words(path: Path) -> list[str]:
    words = [
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(words) != 2048:
        raise ValueError(f"expected 2048 BIP39 words in {path}, found {len(words)}")
    return words


def count_bip39_word_tokens(text: str, words: list[str]) -> Counter[str]:
    word_set = set(words)
    tokens = re.findall(r"[a-z]+", text.lower())
    return Counter(token for token in tokens if token in word_set)


def architect_word_tokens(word_message: str) -> list[str]:
    return re.findall(r"[a-z]+", word_message.lower())


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False

    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2

    return True


def prime_bip39_hits(word_message: str, words: list[str]) -> list[tuple[int, str, int, int]]:
    word_index = {word: i for i, word in enumerate(words)}
    return [
        (position, token, word_index[token], word_index[token] + 1)
        for position, token in enumerate(architect_word_tokens(word_message), start=1)
        if is_prime(position) and token in word_index
    ]


def format_prime_bip39_token_analysis(word_message: str, words: list[str]) -> str:
    tokens = architect_word_tokens(word_message)
    hits = prime_bip39_hits(word_message, words)
    if not hits:
        return "\n".join(
            [
                "1-based positions",
                f"{len(tokens)} total architect word tokens.",
                "0 BIP39 tokens at prime word positions.",
            ]
        )

    lines = [
        "1-based positions",
        f"{len(tokens)} total architect word tokens.",
        f"{len(hits)} BIP39 tokens at prime word positions.",
        "",
        "Sequence:",
        " ".join(token for _, token, _, _ in hits),
        "",
        "Hits:",
    ]
    lines.extend(
        f"{position}: {token} (bip39 0-based {index0}, 1-based {index1})"
        for position, token, index0, index1 in hits
    )
    return "\n".join(lines)


def format_prime_bip39_sha256_aes_attempt(
    word_message: str,
    words: list[str],
    aes_blob: str,
) -> str:
    sequence_words = [token for _, token, _, _ in prime_bip39_hits(word_message, words)]
    combined = "".join(sequence_words)
    sha256_hex = security_codec.sha256_text(combined)
    cipher = "aes-256-cbc"
    digest = "md5"

    lines = [
        f"Combined words: {combined}",
        f"SHA-256: {sha256_hex}",
        f"AES settings: {cipher}, md={digest}, pbkdf2=False",
    ]

    try:
        plaintext = security_codec.decrypt_openssl_blob_bytes(
            aes_blob,
            sha256_hex,
            cipher,
            digest,
            False,
        )
    except ValueError as exc:
        lines.append(f"AES decrypt attempt: Failed: {exc}")
    else:
        lines.extend(["AES decrypt attempt: Success", plaintext.decode("utf-8", errors="replace")])

    return "\n".join(lines)


def entropy_to_bip39_mnemonic(entropy: bytes, words: list[str]) -> str:
    entropy_bits_len = len(entropy) * 8
    if entropy_bits_len not in {128, 160, 192, 224, 256}:
        raise ValueError("BIP39 entropy must be 128, 160, 192, 224, or 256 bits")

    entropy_bits = "".join(f"{byte:08b}" for byte in entropy)
    checksum_bits = security_codec.sha256_checksum_bits(entropy)[: entropy_bits_len // 32]
    mnemonic_bits = entropy_bits + checksum_bits
    indexes = [int(mnemonic_bits[i : i + 11], 2) for i in range(0, len(mnemonic_bits), 11)]
    return " ".join(words[index] for index in indexes)


def bip39_mnemonic_to_entropy(mnemonic: str, words: list[str]) -> bytes:
    mnemonic_words = mnemonic.split()
    word_count_to_entropy_bits = {12: 128, 15: 160, 18: 192, 21: 224, 24: 256}
    entropy_bits_len = word_count_to_entropy_bits.get(len(mnemonic_words))
    if entropy_bits_len is None:
        raise ValueError("BIP39 mnemonic must contain 12, 15, 18, 21, or 24 words")

    word_index = {word: i for i, word in enumerate(words)}
    try:
        bits = "".join(f"{word_index[word]:011b}" for word in mnemonic_words)
    except KeyError as exc:
        raise ValueError(f"word is not in the BIP39 wordlist: {exc.args[0]}") from exc

    entropy_bits = bits[:entropy_bits_len]
    checksum_bits = bits[entropy_bits_len:]
    entropy = int(entropy_bits, 2).to_bytes(entropy_bits_len // 8, "big")
    expected_checksum = security_codec.sha256_checksum_bits(entropy)
    if checksum_bits != expected_checksum[: len(checksum_bits)]:
        raise ValueError("BIP39 checksum mismatch")

    return entropy


def private_key_to_bip39_mnemonic(private_key: int, words: list[str]) -> str:
    if private_key < 0 or private_key >= 1 << 256:
        raise ValueError("private key must fit in 256 bits")

    entropy = private_key.to_bytes(32, "big")
    mnemonic = entropy_to_bip39_mnemonic(entropy, words)
    recovered_private_key = int.from_bytes(bip39_mnemonic_to_entropy(mnemonic, words), "big")
    if recovered_private_key != private_key:
        raise ValueError("BIP39 mnemonic round-trip failed")
    return mnemonic


def private_key_to_bip39_report(private_key: int, words: list[str]) -> str:
    mnemonic = private_key_to_bip39_mnemonic(private_key, words)
    recovered_private_key = int.from_bytes(bip39_mnemonic_to_entropy(mnemonic, words), "big")
    return "\n".join(
        [
            "12-word BIP39 mnemonic: impossible for exact reversible storage of this 256-bit private key",
            "24-word BIP39 mnemonic from private-key entropy:",
            mnemonic,
            "",
            f"Recovered private dec: {recovered_private_key}",
            f"Round-trip ok: {recovered_private_key == private_key}",
        ]
    )


def validate_bip39_mnemonic_report(mnemonic: str, words: list[str]) -> str:
    normalized = " ".join(re.findall(r"[a-z]+", mnemonic.lower()))
    mnemonic_words = normalized.split()

    try:
        entropy = bip39_mnemonic_to_entropy(normalized, words)
    except ValueError as exc:
        return "\n".join(
            [
                f"Mnemonic: {normalized}",
                f"Word count: {len(mnemonic_words)}",
                "Valid: False",
                f"Reason: {exc}",
            ]
        )

    private_key = int.from_bytes(entropy, "big")
    return "\n".join(
        [
            f"Mnemonic: {normalized}",
            f"Word count: {len(mnemonic_words)}",
            "Valid: True",
            f"Entropy hex: {entropy.hex()}",
            f"Entropy/private dec: {private_key}",
        ]
    )


def valid_bip39_mnemonic(words: list[str], word_index: dict[str, int]) -> bool:
    word_count_to_entropy_bits = {12: 128, 15: 160, 18: 192, 21: 224, 24: 256}
    entropy_bits_len = word_count_to_entropy_bits.get(len(words))
    if entropy_bits_len is None:
        return False

    bits = "".join(f"{word_index[word]:011b}" for word in words)
    entropy_bits = bits[:entropy_bits_len]
    checksum_bits = bits[entropy_bits_len:]
    entropy = int(entropy_bits, 2).to_bytes(entropy_bits_len // 8, "big")
    expected_checksum = security_codec.sha256_checksum_bits(entropy)
    return checksum_bits == expected_checksum[: len(checksum_bits)]


def find_contiguous_bip39_mnemonics(text: str, words: list[str]) -> list[tuple[int, int, list[str]]]:
    """Find checksum-valid BIP39 mnemonics embedded without spaces."""

    normalized = normalized_ascii_letters(text)
    word_index = {word: i for i, word in enumerate(words)}
    word_set = set(words)
    transitions: dict[int, list[tuple[int, str]]] = {}

    for i in range(len(normalized)):
        matches = []
        for length in range(3, 9):
            word = normalized[i : i + length]
            if word in word_set:
                matches.append((i + length, word))
        if matches:
            transitions[i] = matches

    valid: list[tuple[int, int, list[str]]] = []
    for start in range(len(normalized)):
        stack: list[tuple[int, list[str]]] = [(start, [])]
        while stack:
            pos, phrase = stack.pop()
            if len(phrase) in {12, 15, 18, 21, 24} and valid_bip39_mnemonic(phrase, word_index):
                valid.append((start, pos, phrase))
            if len(phrase) >= 24:
                continue
            for next_pos, word in transitions.get(pos, []):
                stack.append((next_pos, phrase + [word]))

    return valid


def format_bip39_counts(counts: Counter[str], mode: str = "substring") -> str:
    total = counts.total()
    if total == 0:
        return f"0 total BIP39 {mode} matches; 0 unique words."

    matches = ", ".join(
        f"{word}:{count}"
        for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )
    return f"{total} total BIP39 {mode} matches; {len(counts)} unique words.\n{matches}"


def format_bip39_mnemonics(matches: list[tuple[int, int, list[str]]]) -> str:
    if not matches:
        return "0 checksum-valid contiguous BIP39 mnemonics found."

    return "\n".join(
        f"{start}-{end} ({len(words)} words): {' '.join(words)}"
        for start, end, words in matches
    )


def pubkey_to_address(pubkey: bytes) -> str:
    return security_codec.base58check_encode(b"\x00", security_codec.hash160(pubkey))


def compress_pubkey(point) -> bytes:
    prefix = b"\x02" if point.y() % 2 == 0 else b"\x03"
    return prefix + point.x().to_bytes(32, "big")


def private_key_to_public_point(private_key: int):
    return private_key * SECP256K1_GENERATOR


def private_key_to_address(private_key: int) -> str:
    return pubkey_to_address(compress_pubkey(private_key_to_public_point(private_key)))


def parse_private_key_hex(private_key_hex: str) -> int:
    normalized = private_key_hex.strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("private key hex is empty")
    if not re.fullmatch(r"[0-9a-f]+", normalized):
        raise ValueError("private key must be hexadecimal")
    if len(normalized) > 64:
        raise ValueError("private key hex must be at most 32 bytes / 64 hex characters")

    private_key = int(normalized, 16)
    if not 0 < private_key < SECP256K1_ORDER:
        raise ValueError("private key must be in the secp256k1 range 1..n-1")
    return private_key


def private_key_hex_to_address_report(private_key_hex: str) -> str:
    private_key = parse_private_key_hex(private_key_hex)
    return "\n".join(
        [
            f"Private hex: {private_key:064x}",
            f"Private dec: {private_key}",
            f"Compressed address: {private_key_to_address(private_key)}",
        ]
    )


def initial_wallet_lines(bip39_words: list[str] | None = None, show_mnemonics: bool = False) -> str:
    half_private_key = int(HALF_PRIVATE_KEY_HEX, 16)
    better_half_private_key = (SECP256K1_ORDER - half_private_key) % SECP256K1_ORDER
    half_mnemonic = None
    better_half_mnemonic = None

    if show_mnemonics and bip39_words:
        half_mnemonic = private_key_to_bip39_mnemonic(half_private_key, bip39_words)
        better_half_mnemonic = private_key_to_bip39_mnemonic(better_half_private_key, bip39_words)

    lines = [
        "VISIBLE HALF WALLET",
        f"Private hex: {half_private_key:#x}",
        f"Private dec: {half_private_key}",
        f"Address: {private_key_to_address(half_private_key)}",
        *(["Mnemonic: " + half_mnemonic] if half_mnemonic else []),
        "",
        "HIDDEN BETTER HALF WALLET",
        f"Private hex: {better_half_private_key:#x}",
        f"Private dec: {better_half_private_key}",
        f"Address: {private_key_to_address(better_half_private_key)}",
        *(["Mnemonic: " + better_half_mnemonic] if better_half_mnemonic else []),
        "",
        "PUZZLE CLUE RELATIONS",
        "half + better_half private scalars = curve order",
        str((half_private_key + better_half_private_key) % SECP256K1_ORDER == 0),
    ]

    if show_mnemonics and not bip39_words:
        lines.extend(["", "BIP39 private-key mnemonics", f"Skipped: could not find {DEFAULT_BIP39_WORDLIST}."])

    return "\n".join(lines)
