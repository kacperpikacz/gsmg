#!/usr/bin/env python3
"""List Telegram chats/channels or export messages from one accessible user.

This uses Telegram's client API through Telethon. It does not bypass access
controls: the signed-in Telegram account must already be able to read the group.

Setup:
    python3 -m pip install telethon
    export TELEGRAM_API_ID="123456"
    export TELEGRAM_API_HASH="your_api_hash"

Examples:
    python3 scripts/export_telegram_user_messages.py list-groups

    python3 scripts/export_telegram_user_messages.py export \
        --group my_group_or_channel \
        --user SoWut
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List Telegram chats/channels or export readable messages from one user."
    )
    parser.add_argument(
        "--session",
        default="telegram_export",
        help="Telethon session name/path. Default: telegram_export.",
    )
    parser.add_argument(
        "--api-id",
        default=os.environ.get("TELEGRAM_API_ID"),
        help="Telegram API ID. Defaults to TELEGRAM_API_ID.",
    )
    parser.add_argument(
        "--api-hash",
        default=os.environ.get("TELEGRAM_API_HASH"),
        help="Telegram API hash. Defaults to TELEGRAM_API_HASH.",
    )

    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser(
        "list-groups",
        help="List accessible Telegram groups and channels.",
    )
    list_parser.add_argument(
        "--include-channels",
        action="store_true",
        help="Also include broadcast channels. Default lists groups/supergroups only.",
    )
    list_parser.add_argument(
        "--format",
        choices=("table", "jsonl", "csv"),
        default="table",
        help="Output format. Default: table.",
    )
    list_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file. Default prints to stdout.",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Export messages by one user from one group/channel.",
    )
    export_parser.add_argument(
        "--group",
        required=True,
        help="Telegram group/channel username, t.me link, invite link, or numeric chat id.",
    )
    export_parser.add_argument(
        "--user",
        required=True,
        help="Target username without @.",
    )
    export_parser.add_argument(
        "--output",
        default="sowut_messages.json",
        type=Path,
        help="Output path. Default: sowut_messages.json.",
    )
    export_parser.add_argument(
        "--format",
        choices=("json", "jsonl", "csv", "txt"),
        default="json",
        help="Output format. Default: json.",
    )
    export_parser.add_argument(
        "--limit",
        default=0,
        type=int,
        help="Maximum messages to export. Use 0 for all history. Default: 0.",
    )
    export_parser.add_argument(
        "--oldest-first",
        action="store_true",
        help="Write messages oldest to newest. Default is newest to oldest.",
    )
    export_parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include media/service messages that have no text body.",
    )
    export_parser.add_argument(
        "--progress-every",
        default=500,
        type=int,
        help="Print progress every N scanned messages. Use 0 to disable. Default: 500.",
    )
    export_parser.add_argument(
        "--match-mode",
        choices=("auto", "server", "signature", "scan"),
        default="auto",
        help=(
            "How to match the target user. auto uses server filtering for groups "
            "and signature scanning for broadcast channels. Default: auto."
        ),
    )

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        raise SystemExit(2)
    return args


def clean_username(username: str) -> str:
    return username.strip().strip("\"'").lstrip("@")


def normalized_name(value: str | None) -> str:
    return (value or "").strip().strip("\"'").lstrip("@").casefold()


def clean_chat_ref(chat_ref: str) -> str:
    return str(chat_ref).strip().strip("\"'")


def message_to_record(message: Any, username: str) -> dict[str, Any]:
    media_type = type(message.media).__name__ if message.media else None
    return {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "target_username": username,
        "sender_id": message.sender_id,
        "text": message.message or "",
        "reply_to_msg_id": getattr(message.reply_to, "reply_to_msg_id", None),
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
        "grouped_id": str(message.grouped_id) if message.grouped_id else None,
        "media_type": media_type,
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "date",
        "target_username",
        "sender_id",
        "text",
        "reply_to_msg_id",
        "views",
        "forwards",
        "grouped_id",
        "media_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_txt(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as out:
        for record in records:
            out.write(f"[{record['date']}] #{record['id']} @{record['target_username']}\n")
            out.write(record["text"])
            out.write("\n\n")


def write_records(path: Path, records: list[dict[str, Any]], output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        write_json(path, records)
    elif output_format == "jsonl":
        write_jsonl(path, records)
    elif output_format == "csv":
        write_csv(path, records)
    elif output_format == "txt":
        write_txt(path, records)
    else:
        raise ValueError(f"unsupported output format: {output_format}")


def progress_line(scanned: int, matched: int, message: Any, started_at: float, done: bool = False) -> str:
    elapsed = max(time.monotonic() - started_at, 0.001)
    rate = scanned / elapsed
    date = message.date.isoformat() if message and message.date else "n/a"
    prefix = "Done" if done else "Progress"
    return f"{prefix}: scanned={scanned} matched={matched} rate={rate:.1f}/s last_date={date}"


def maybe_print_progress(
    scanned: int,
    matched: int,
    message: Any,
    started_at: float,
    every: int,
) -> None:
    if every <= 0 or scanned % every != 0:
        return
    print(progress_line(scanned, matched, message, started_at), file=sys.stderr, flush=True)


def require_telegram_client(args: argparse.Namespace):
    try:
        from telethon import TelegramClient
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: telethon. Install it with: python3 -m pip install telethon"
        ) from exc

    if not args.api_id or not args.api_hash:
        raise SystemExit(
            "Missing Telegram credentials. Set TELEGRAM_API_ID and TELEGRAM_API_HASH, "
            "or pass --api-id and --api-hash."
        )

    return TelegramClient(args.session, int(args.api_id), args.api_hash)


def dialog_to_record(dialog: Any) -> dict[str, Any]:
    entity = dialog.entity
    username = getattr(entity, "username", None)
    return {
        "id": dialog.id,
        "name": dialog.name,
        "username": username,
        "type": type(entity).__name__,
        "is_group": dialog.is_group,
        "is_channel": dialog.is_channel,
        "megagroup": bool(getattr(entity, "megagroup", False)),
        "broadcast": bool(getattr(entity, "broadcast", False)),
        "link": f"https://t.me/{username}" if username else None,
    }


async def resolve_chat(client: Any, chat_ref: str) -> Any:
    value = clean_chat_ref(chat_ref)

    async for dialog in client.iter_dialogs():
        record = dialog_to_record(dialog)
        if value in {
            str(record["id"]),
            str(getattr(dialog.entity, "id", "")),
            record["username"] or "",
            f"@{record['username']}" if record["username"] else "",
            record["link"] or "",
        }:
            return dialog.entity

    try:
        return await client.get_entity(int(value))
    except ValueError:
        return await client.get_entity(value)


async def message_matches_user(
    message: Any,
    target_user: Any,
    username: str,
    sender_cache: dict[int, str],
) -> bool:
    if normalized_name(getattr(message, "post_author", None)) == normalized_name(username):
        return True

    if message.sender_id and target_user and message.sender_id == getattr(target_user, "id", None):
        return True

    if not message.sender_id:
        return False

    if message.sender_id in sender_cache:
        return sender_cache[message.sender_id] == normalized_name(username)

    try:
        sender = await message.get_sender()
    except Exception:
        sender_cache[message.sender_id] = ""
        return False

    sender_username = normalized_name(getattr(sender, "username", None))
    sender_cache[message.sender_id] = sender_username
    if sender_username == normalized_name(username):
        return True

    return False


def is_broadcast_channel(chat: Any) -> bool:
    return bool(getattr(chat, "broadcast", False)) and not bool(getattr(chat, "megagroup", False))


def effective_match_mode(requested_mode: str, chat: Any) -> str:
    if requested_mode != "auto":
        return requested_mode
    return "signature" if is_broadcast_channel(chat) else "server"


def write_group_table(records: list[dict[str, Any]]) -> str:
    rows = [
        (
            str(record["id"]),
            record["name"] or "",
            f"@{record['username']}" if record["username"] else "",
            record["type"],
        )
        for record in records
    ]
    headers = ("id", "name", "username", "type")
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]
    lines = [
        "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in rows)
    return "\n".join(lines)


def write_group_records(
    records: list[dict[str, Any]],
    output_format: str,
    output: Path | None,
) -> None:
    if output_format == "table":
        text = write_group_table(records) + "\n"
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return

    if output is None:
        if output_format == "jsonl":
            for record in records:
                print(json.dumps(record, ensure_ascii=False))
        elif output_format == "csv":
            writer = csv.DictWriter(os.sys.stdout, fieldnames=list(records[0]) if records else [])
            if records:
                writer.writeheader()
                writer.writerows(records)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "jsonl":
        write_jsonl(output, records)
    elif output_format == "csv":
        with output.open("w", encoding="utf-8", newline="") as out:
            fieldnames = list(records[0]) if records else [
                "id",
                "name",
                "username",
                "type",
                "is_group",
                "is_channel",
                "megagroup",
                "broadcast",
                "link",
            ]
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


async def list_groups(args: argparse.Namespace) -> int:
    records: list[dict[str, Any]] = []

    async with require_telegram_client(args) as client:
        async for dialog in client.iter_dialogs():
            record = dialog_to_record(dialog)
            is_broadcast = record["is_channel"] and record["broadcast"] and not record["megagroup"]
            if record["is_group"] or record["megagroup"] or (args.include_channels and is_broadcast):
                records.append(record)

    write_group_records(records, args.format, args.output)
    return len(records)


async def export_messages(args: argparse.Namespace) -> int:
    username = clean_username(args.user)
    limit = None if args.limit == 0 else args.limit
    records: list[dict[str, Any]] = []
    sender_cache: dict[int, str] = {}
    scanned = 0
    started_at = time.monotonic()
    last_message = None

    async with require_telegram_client(args) as client:
        chat = await resolve_chat(client, args.group)
        try:
            user = await client.get_entity(username)
        except ValueError:
            user = None
        match_mode = effective_match_mode(args.match_mode, chat)
        iter_kwargs: dict[str, Any] = {"limit": limit}
        if match_mode == "server":
            if user is None:
                raise SystemExit(f"Could not resolve target user @{username} for server-side filtering.")
            iter_kwargs["from_user"] = user

        print(
            f"Exporting @{username} from {clean_chat_ref(args.group)} to {args.output} "
            f"({args.format}, match_mode={match_mode})...",
            file=sys.stderr,
            flush=True,
        )

        async for message in client.iter_messages(chat, **iter_kwargs):
            scanned += 1
            last_message = message
            maybe_print_progress(
                scanned,
                len(records),
                message,
                started_at,
                args.progress_every,
            )
            if match_mode == "signature":
                if normalized_name(getattr(message, "post_author", None)) != normalized_name(username):
                    continue
            elif match_mode == "scan":
                if not await message_matches_user(message, user, username, sender_cache):
                    continue
            if not args.include_empty and not message.message:
                continue
            records.append(message_to_record(message, username))

    if args.oldest_first:
        records.reverse()

    write_records(args.output, records, args.format)
    print(
        progress_line(scanned, len(records), last_message, started_at, done=True),
        file=sys.stderr,
        flush=True,
    )
    return len(records)


def main() -> None:
    args = parse_args()
    if args.command == "list-groups":
        count = asyncio.run(list_groups(args))
        if args.output:
            print(f"Listed {count} chats to {args.output}")
    elif args.command == "export":
        count = asyncio.run(export_messages(args))
        print(f"Exported {count} messages to {args.output}")
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
