#!/usr/bin/env python3
"""Command-line reports for the local GSMG puzzle solve.

The phase facts and decryption/parsing logic live in ``phase_api.py`` and in
each phase's ``phase.py``. This script is intentionally a thin CLI around that
API plus a few analysis/report helpers.
"""

from __future__ import annotations

import argparse
from functools import cache
import re
import textwrap
from pathlib import Path

import bitcoin_utils
import phase_api
from puzzle_image import (
    PUZZLE_PNG_PATH,
    generate_custom_puzzle_png,
    reconstruct_puzzle_image_report,
)


@cache
def phase3_api():
    return phase_api.phase_api("phase3")


def load_phase32_dump(input_path: Path | None = None):
    api = phase3_api()
    if input_path:
        if not input_path.exists():
            raise FileNotFoundError(f"Phase 3.2 input does not exist: {input_path}")
        html_text = input_path.read_bytes().decode("latin1")
        return api.parse_phase32_html(html_text)
    return api.parse_decrypted_phase32()


def load_architect_word_message(explicit_path: Path | None = None) -> tuple[str, Path]:
    path = explicit_path or phase3_api().architect_word_message_path()
    if not path.exists():
        raise FileNotFoundError(f"could not find architect word message: {path}")
    return path.read_text(encoding="utf-8").strip(), path


def normalized_ascii_letters(text: str) -> str:
    return "".join(char for char in text.lower() if "a" <= char <= "z")


def validate_architect_word_message(
    word_message: str,
    decrypted_message: str,
    path: Path,
) -> None:
    normalized_word_message = normalized_ascii_letters(word_message)
    normalized_decrypted_message = normalized_ascii_letters(decrypted_message)

    if len(normalized_word_message) != len(normalized_decrypted_message):
        raise ValueError(
            f"{path} has {len(normalized_word_message)} letters, but the decrypted "
            f"architect message has {len(normalized_decrypted_message)} letters"
        )

    if normalized_word_message != normalized_decrypted_message:
        raise ValueError(f"{path} does not match the decrypted architect message")


def grouped_words_hint() -> str:
    return '"why" am I here? Wake up, you "Neo".'


def require_bip39_words(explicit_path: Path | None, title: str) -> list[str] | None:
    wordlist = bitcoin_utils.find_default_bip39_wordlist(explicit_path)
    if wordlist:
        return bitcoin_utils.load_bip39_words(wordlist)
    print_block(title, f"Skipped: could not find {bitcoin_utils.DEFAULT_BIP39_WORDLIST}.")
    return None


def print_block(title: str, value: str, width: int = 96) -> None:
    print(f"\n== {title} ==")
    print(textwrap.fill(value, width=width))


def print_multiline_block(title: str, value: str) -> None:
    print(f"\n== {title} ==")
    print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    report = subparsers.add_parser("report", help="print the Phase 3.2 solve report")
    report.add_argument(
        "input",
        nargs="?",
        default=None,
        type=Path,
        help="optional already-decrypted Phase 3.2 text/html; defaults to phase_api decryption",
    )
    report.add_argument("--raw", action="store_true", help="also print the raw Beaufort ciphertext")
    report.add_argument("--bip39-wordlist", default=None, type=Path, help="path to bip39-english.txt")
    report.add_argument(
        "--architect-word-message",
        default=None,
        type=Path,
        help="path to architect_word_message.txt",
    )
    report.add_argument("--no-bip39", action="store_true", help="skip BIP39 word counting")
    report.add_argument(
        "--bip39-mnemonic-scan",
        action="store_true",
        help="scan the architect message for checksum-valid contiguous BIP39 mnemonics",
    )
    report.add_argument(
        "--prime-bip39",
        action="store_true",
        help="show BIP39 word tokens that occur at prime 1-based positions in the architect message",
    )

    puzzle_image = subparsers.add_parser("puzzle-image", help="generate or reconstruct a puzzle PNG")
    puzzle_image.add_argument(
        "text",
        nargs="?",
        default="",
        help="text to hide in a custom image; omit to reconstruct the original image",
    )
    puzzle_image.add_argument(
        "--output",
        default=PUZZLE_PNG_PATH,
        type=Path,
        help=f"PNG output path; default: {PUZZLE_PNG_PATH}",
    )

    wallets = subparsers.add_parser("wallets", help="print HALF and better-half Bitcoin addresses")
    wallets.add_argument("--bip39-wordlist", default=None, type=Path, help="path to bip39-english.txt")

    priv_dec = subparsers.add_parser(
        "priv-dec-to-mnemonic",
        help="convert a 256-bit private key decimal to a reversible 24-word BIP39 mnemonic",
    )
    priv_dec.add_argument("private_key", type=int, help="private key as a decimal integer")
    priv_dec.add_argument("--bip39-wordlist", default=None, type=Path, help="path to bip39-english.txt")

    priv_hex = subparsers.add_parser(
        "priv-hex-to-address",
        help="derive a compressed Bitcoin address from a secp256k1 private key hex",
    )
    priv_hex.add_argument("private_key", help="private key as hexadecimal")

    validate_mnemonic = subparsers.add_parser(
        "validate-mnemonic",
        help="validate a BIP39 mnemonic and print recovered entropy/private-key decimal",
    )
    validate_mnemonic.add_argument("mnemonic", help="mnemonic phrase to validate")
    validate_mnemonic.add_argument("--bip39-wordlist", default=None, type=Path, help="path to bip39-english.txt")

    return parser


def normalize_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def print_phase32_report(args: argparse.Namespace) -> None:
    dump = load_phase32_dump(args.input)
    if not dump.architect_message:
        raise ValueError("phase_api could not extract the architect message")
    if not dump.checkerboard_message:
        raise ValueError("phase_api could not extract the numeric checkerboard riddle")
    if not dump.openssl_blob:
        raise ValueError("phase_api could not extract the final OpenSSL/AES blob")

    architect_word_message, architect_word_message_path = load_architect_word_message(args.architect_word_message)
    validate_architect_word_message(architect_word_message, dump.architect_message, architect_word_message_path)

    print_block("Filled Matrix hints", grouped_words_hint())
    if args.raw and dump.beaufort_ciphertext:
        print_block(f'EBCDIC decoded Beaufort ciphertext ({phase3_api().BEAUFORT_KEY})', dump.beaufort_ciphertext)
    print_block(f'Beaufort decrypted with key "{phase3_api().BEAUFORT_KEY}"', dump.architect_message)

    if not args.no_bip39:
        wordlist = bitcoin_utils.find_default_bip39_wordlist(args.bip39_wordlist)
        if wordlist:
            bip39_words = bitcoin_utils.load_bip39_words(wordlist)
            print_block(
                f"BIP39 word tokens in original architect message ({wordlist})",
                bitcoin_utils.format_bip39_counts(
                    bitcoin_utils.count_bip39_word_tokens(architect_word_message, bip39_words),
                    "word-token",
                ),
            )
            if args.prime_bip39:
                print_multiline_block(
                    "Prime-position BIP39 word tokens",
                    bitcoin_utils.format_prime_bip39_token_analysis(architect_word_message, bip39_words),
                )
                print_multiline_block(
                    "Prime-position BIP39 SHA-256 AES attempt",
                    bitcoin_utils.format_prime_bip39_sha256_aes_attempt(
                        architect_word_message,
                        bip39_words,
                        dump.openssl_blob,
                    ),
                )
            if args.bip39_mnemonic_scan:
                mnemonics = bitcoin_utils.find_contiguous_bip39_mnemonics(dump.architect_message, bip39_words)
                print_block("BIP39 mnemonic scan", bitcoin_utils.format_bip39_mnemonics(mnemonics))
        else:
            print_block(
                "BIP39 words in architect message",
                f"Skipped: could not find {bitcoin_utils.DEFAULT_BIP39_WORDLIST}.",
            )

    print_block("Checkerboard decrypted numeric riddle", dump.checkerboard_message)
    print_block("Final OpenSSL/AES blob, password still unknown", dump.openssl_blob)


def print_wallets(args: argparse.Namespace) -> None:
    bip39_words = bitcoin_utils.find_default_bip39_wordlist(args.bip39_wordlist)
    print_multiline_block(
        "Initial address creation",
        bitcoin_utils.initial_wallet_lines(
            bitcoin_utils.load_bip39_words(bip39_words) if bip39_words else None,
            True,
        ),
    )


def print_private_key_mnemonic(args: argparse.Namespace) -> None:
    bip39_words = require_bip39_words(args.bip39_wordlist, "Private key BIP39 mnemonic")
    if bip39_words:
        print_multiline_block(
            "Private key BIP39 mnemonic",
            bitcoin_utils.private_key_to_bip39_report(args.private_key, bip39_words),
        )


def print_private_key_address(args: argparse.Namespace) -> None:
    try:
        address_report = bitcoin_utils.private_key_hex_to_address_report(args.private_key)
    except ValueError as exc:
        print_block("Private key hex address", f"Failed: {exc}")
    else:
        print_multiline_block("Private key hex address", address_report)


def print_mnemonic_validation(args: argparse.Namespace) -> None:
    bip39_words = require_bip39_words(args.bip39_wordlist, "BIP39 mnemonic validation")
    if bip39_words:
        print_multiline_block(
            "BIP39 mnemonic validation",
            bitcoin_utils.validate_bip39_mnemonic_report(args.mnemonic, bip39_words),
        )


def generate_puzzle_image(args: argparse.Namespace) -> None:
    if args.text:
        report = generate_custom_puzzle_png(args.output, args.text)
        title = "Custom GSMG-style puzzle image"
    else:
        report = reconstruct_puzzle_image_report(args.output)
        title = "GSMG puzzle image reconstruction"
    print_multiline_block(title, report)


def dispatch(args: argparse.Namespace) -> None:
    if args.command == "report":
        print_phase32_report(args)
    elif args.command == "puzzle-image":
        generate_puzzle_image(args)
    elif args.command == "wallets":
        print_wallets(args)
    elif args.command == "priv-dec-to-mnemonic":
        print_private_key_mnemonic(args)
    elif args.command == "priv-hex-to-address":
        print_private_key_address(args)
    elif args.command == "validate-mnemonic":
        print_mnemonic_validation(args)
    else:
        raise SystemExit(f"unknown command: {args.command}")


def main() -> None:
    dispatch(normalize_args())


if __name__ == "__main__":
    main()
