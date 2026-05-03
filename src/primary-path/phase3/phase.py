"""Phase 3 information/API helpers.

Phase 3 is stored as the second OpenSSL blob in the phase2 source page.
This folder intentionally does not contain an extracted HTML file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import phase_api
import security_codec


PHASE2_DIR = PHASE_DIR.parent / "phase2"
SOURCE_HTML_PATH = PHASE2_DIR / "phase.html"
ARCHITECT_WORD_MESSAGE_PATH = PHASE_DIR / "assets" / "architect_word_message.txt"

PASSWORD_PARTS = (
    "causality",
    "Safenet",
    "Luna",
    "HSM",
    "11110",
    "0x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854",
    "B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1",
)
PASSWORD = "".join(PASSWORD_PARTS)
PASSWORD_SHA256 = "1a57c572caf3cf722e41f5f9cf99ffacff06728a43032dd44c481c77d2ec30d5"

PHASE32_PASSWORD_PARTS = (
    "jacquefresco",
    "giveitjustonesecond",
    "heisenbergsuncertaintyprinciple",
)
PHASE32_PASSWORD = "".join(PHASE32_PASSWORD_PARTS)
PHASE32_PASSWORD_SHA256 = "250f37726d6862939f723edc4f993fde9d33c6004aab4f2203d9ee489d61ce4c"
BEAUFORT_KEY = "thematrixhasyou"
CHECKERBOARD_ROW_DIGITS = "14"
CHECKERBOARD_ALPHABET = "fubcdora/lethingkymvpszjqwx."


@dataclass(frozen=True)
class Phase32Dump:
    html: phase_api.ParsedHTML
    readable_blocks: tuple[str, ...]
    mojibake_block: str | None
    beaufort_ciphertext: str | None
    architect_message: str | None
    digit_riddle: str | None
    checkerboard_message: str | None
    chess_clue: str | None
    openssl_blob: str | None


def path() -> Path:
    """Return the folder path for this phase."""

    return PHASE_DIR


def source_html_path() -> Path:
    return SOURCE_HTML_PATH


def source_html() -> str:
    return SOURCE_HTML_PATH.read_text(encoding="utf-8", errors="replace")


def parsed_source() -> phase_api.ParsedHTML:
    return phase_api.parse_html(source_html())


def blob() -> str:
    return parsed_source().aes_blobs[1].text


def blobs() -> tuple[phase_api.Blob, ...]:
    return (parsed_source().aes_blobs[1],)


def load() -> phase_api.Phase:
    html_text = source_html()
    parsed_html = phase_api.parse_html(html_text)
    return phase_api.Phase(
        name="phase3",
        path=source_html_path(),
        html=html_text,
        parsed=parsed_html,
        blobs=parsed_html.aes_blobs[1:2],
        notes=("phase3 is stored as the second OpenSSL blob inside the phase2 HTML",),
    )


def password_parts() -> tuple[str, ...]:
    return PASSWORD_PARTS


def password() -> str:
    return PASSWORD


def password_sha256() -> str:
    return PASSWORD_SHA256


def decrypt() -> str:
    return security_codec.decrypt_openssl_blob(blob(), PASSWORD_SHA256)


def phase32_blob() -> str:
    match = re.search(r"(U2FsdGVkX1[0-9A-Za-z+/=\s]+)$", decrypt())
    if not match:
        raise ValueError("could not find Phase 3.2 OpenSSL blob")
    return security_codec.compact(match.group(1))


def phase32_password_parts() -> tuple[str, ...]:
    return PHASE32_PASSWORD_PARTS


def phase32_password() -> str:
    return PHASE32_PASSWORD


def phase32_password_sha256() -> str:
    return PHASE32_PASSWORD_SHA256


def architect_word_message_path() -> Path:
    return ARCHITECT_WORD_MESSAGE_PATH


def architect_word_message() -> str:
    """Return the human-formatted architect message, one word per line."""

    return ARCHITECT_WORD_MESSAGE_PATH.read_text(encoding="utf-8").strip()


def architect_words() -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in architect_word_message().splitlines()
        if line.strip()
    )


def architect_message_joined() -> str:
    return "".join(architect_words())


def architect_message_with_spaces() -> str:
    return " ".join(architect_words())


def phase32_text() -> str:
    return security_codec.decrypt_openssl_blob(phase32_blob(), PHASE32_PASSWORD_SHA256)


def phase32_bytes() -> bytes:
    return phase32_text().encode("latin1")


def _extract_between(data: bytes, start_marker: bytes, end_marker: bytes) -> bytes:
    start = data.find(start_marker)
    if start == -1:
        raise ValueError(f"could not find start marker: {start_marker!r}")
    start += len(start_marker)
    end = data.find(end_marker, start)
    if end == -1:
        raise ValueError(f"could not find end marker: {end_marker!r}")
    return data[start:end]


def architect_beaufort_ciphertext() -> str:
    mojibake = _extract_between(
        phase32_bytes(),
        b"four for one.\r\n\r\n",
        b"\r\n\r\n151659",
    )
    return security_codec.decode_ebcdic_mojibake(mojibake.decode("latin1"))


def parse_decrypted_phase32() -> Phase32Dump:
    return parse_phase32_html(phase32_text())


def decrypt_architect_message() -> str:
    return security_codec.beaufort_decrypt(architect_beaufort_ciphertext(), BEAUFORT_KEY)


def architect_word_message_matches_decrypted() -> bool:
    return architect_message_joined() == decrypt_architect_message()


def parse_phase32_html(html_text: str) -> Phase32Dump:
    parsed = phase_api.parse_html(html_text)
    body_text = html_text
    if parsed.textareas:
        body_text = "\n\n".join((body_text, *(textarea.text for textarea in parsed.textareas)))
    blocks = split_blocks(body_text)

    readable_blocks: list[str] = []
    mojibake_block = None
    digit_riddle = None
    openssl_blob = None

    for block in blocks:
        if digit_riddle is None and security_codec.is_digit_riddle(block):
            digit_riddle = security_codec.compact(block)
        elif openssl_blob is None and security_codec.is_openssl_blob(block):
            openssl_blob = security_codec.compact(block)
        elif mojibake_block is None and security_codec.is_mojibake_block(block):
            mojibake_block = block
        elif security_codec.is_readable_block(block):
            readable_blocks.append(block)

    chess_clue = next(
        (
            block
            for block in readable_blocks
            if re.search(r"\b(fubcd|king|queen|thingky|mvps|board)\b", block, re.IGNORECASE)
        ),
        None,
    )

    beaufort_ciphertext = security_codec.decode_ebcdic_mojibake(mojibake_block) if mojibake_block else None
    architect_message = (
        security_codec.beaufort_decrypt(beaufort_ciphertext, BEAUFORT_KEY)
        if beaufort_ciphertext
        else None
    )
    checkerboard_message = (
        security_codec.checkerboard_decrypt(
            digit_riddle,
            CHECKERBOARD_ALPHABET,
            CHECKERBOARD_ROW_DIGITS,
        )
        if digit_riddle
        else None
    )

    return Phase32Dump(
        html=parsed,
        readable_blocks=tuple(readable_blocks),
        mojibake_block=mojibake_block,
        beaufort_ciphertext=beaufort_ciphertext,
        architect_message=architect_message,
        digit_riddle=digit_riddle,
        checkerboard_message=checkerboard_message,
        chess_clue=chess_clue,
        openssl_blob=openssl_blob,
    )


def split_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
