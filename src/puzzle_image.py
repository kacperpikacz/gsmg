#!/usr/bin/env python3
"""Puzzle image generation helpers for the GSMG phase 0 grid."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import struct
import zlib

import security_codec


W = 0
B = 1
U = 2
Y = 3
X = 4

CUSTOM_PUZZLE_BACKGROUND_ART = [
    ".....X.X........",
    "....X.X.X.......",
    "....X.X.X.......",
    "....X.X.X.......",
    "...X....X.......",
    "..X......XXX....",
    "..X..X......X.XX",
    "..X..X.......X.X",
    "..X..........XXX",
    "...XX.....XX...X",
    ".....X.........X",
    "....X..XXX.....X",
    "....XXX...XXXXXX",
]

ORIGINAL_SHUTTERSTOCK_RABBIT_ART = [
    ".....X.X........",
    "....X.X.X.......",
    "....X.X.X.......",
    "....X.X.X.......",
    "...X....X.......",
    "..X......XXX....",
    "..X..X......X...",
    "..X..X.......XXX",
    "..X..........X.X",
    "...XX.........XX",
    ".....X....XX...X",
    "....X..XXX.....X",
    "....XXX...XXXXXX",
]

CUSTOM_PUZZLE_BACKGROUND_SIZE = 6
ASCII_ART_CELL_SIZE_PX = 15
ASCII_ART_ANCHOR_ROW = 7
ASCII_ART_ANCHOR_COL = 7
CUSTOM_PUZZLE_GRID_ROWS = 14
CUSTOM_PUZZLE_GRID_COLS = 14
INVISIBLE_MARKER_ROW = 8
INVISIBLE_MARKER_COL = 5
PUZZLE_PNG_PATH = "gsmg_puzzle.png"
TARGET_ADDRESS = "1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe"
HIDDEN_URL_STEP_1 = "gsmg.io/theseedisplanted"
CELL_SIZE_PX = 75
RED_LINE_HEIGHT_PX = 15
WHITE_LINE_HEIGHT_PX = 3

COLOR_RGB = {
    W: (255, 255, 255),
    B: (0, 0, 0),
    U: (63, 72, 204),
    Y: (255, 242, 0),
    X: (254, 254, 254),
}


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    limit = int(value**0.5)
    return all(value % divisor for divisor in range(3, limit + 1, 2))


def color_to_bit(value: int) -> str:
    return "1" if value in (B, U) else "0"


def blue_yellow_row_bits(matrix: list[list[int]]) -> str:
    bits = []
    for row in matrix:
        for value in row:
            if value == U:
                bits.append("0")
            elif value == Y:
                bits.append("1")
    return "".join(bits)


def blue_yellow_row_value(matrix: list[list[int]]) -> tuple[str, int]:
    bits = blue_yellow_row_bits(matrix)
    return bits, int(bits, 2)


def color_value(value: int) -> int:
    return {
        W: 0,
        B: 1,
        U: 2,
        Y: 3,
        X: 4,
    }[value]


def matrix_sumlist(matrix: list[list[int]]) -> tuple[list[int], list[int]]:
    row_sums = [sum(color_value(value) for value in row) for row in matrix]
    col_sums = [
        sum(color_value(matrix[row][col]) for row in range(len(matrix)))
        for col in range(len(matrix[0]))
    ]
    return row_sums, col_sums


def prime_index_cells(matrix: list[list[int]]) -> list[tuple[int, int, int, int]]:
    out = []
    for r, row in enumerate(matrix, 1):
        for c, value in enumerate(row, 1):
            index = (r - 1) * len(row) + c
            if is_prime(index):
                out.append((index, r, c, value))
    return out


def prime_row_col_cells(matrix: list[list[int]]) -> list[tuple[int, int, int]]:
    out = []
    for r, row in enumerate(matrix, 1):
        for c, value in enumerate(row, 1):
            if is_prime(r) and is_prime(c):
                out.append((r, c, value))
    return out


def selected_matrix_bits(matrix: list[list[int]], rows: list[int], cols: list[int]) -> str:
    return "".join(color_to_bit(matrix[r - 1][c - 1]) for r in rows for c in cols)


def color_marker_sums(matrix: list[list[int]], marker: int) -> dict[str, object]:
    coords = []
    for r, row in enumerate(matrix, 1):
        for c, value in enumerate(row, 1):
            if value == marker:
                coords.append((r, c, (r - 1) * len(row) + c))

    return {
        "count": len(coords),
        "row_sum": sum(r for r, _c, _index in coords),
        "col_sum": sum(c for _r, c, _index in coords),
        "index_sum": sum(index for _r, _c, index in coords),
        "row_col_product_sum": sum(r * c for r, c, _index in coords),
        "coords": coords,
    }


def spiral_ccw_from_topleft(matrix: list[list[int]]) -> list[int]:
    return [matrix[row][col] for row, col in spiral_ccw_coordinates_from_topleft(len(matrix), len(matrix[0]))]


def spiral_ccw_coordinates_from_topleft(row_count: int, col_count: int) -> list[tuple[int, int]]:
    top = 0
    bottom = row_count - 1
    left = 0
    right = col_count - 1
    out = []

    while left <= right and top <= bottom:
        for i in range(top, bottom + 1):
            out.append((i, left))
        left += 1
        if left > right:
            break

        for j in range(left, right + 1):
            out.append((bottom, j))
        bottom -= 1
        if top > bottom:
            break

        for i in range(bottom, top - 1, -1):
            out.append((i, right))
        right -= 1
        if left > right:
            break

        for j in range(right, left - 1, -1):
            out.append((top, j))
        top += 1

    return out


def spiral_zero_square_grid(text: str, zero_char: str = "0") -> list[list[str]]:
    if len(zero_char) != 1:
        raise ValueError("zero character must be exactly one character")
    if not text:
        raise ValueError("text must not be empty")

    size = math.ceil(math.sqrt(len(text)))
    capacity = size * size
    chars = list(text) + [zero_char] * (capacity - len(text))
    grid = [[zero_char for _ in range(size)] for _ in range(size)]

    for char, (row, col) in zip(chars, spiral_ccw_coordinates_from_topleft(size, size)):
        grid[row][col] = char

    return grid


def format_spiral_zero_square_grid(text: str, zero_char: str = "0") -> str:
    grid = spiral_zero_square_grid(text, zero_char)
    size = len(grid)
    zeroed = size * size - len(text)
    coordinates = spiral_ccw_coordinates_from_topleft(size, size)
    zero_cells = [(row + 1, col + 1) for row, col in coordinates[len(text):]]

    lines = [
        f"Input length: {len(text)}",
        f"Grid size: {size}x{size}",
        f"Zeroed trailing cells: {zeroed}",
        f"Zeroed cells, 1-based: {zero_cells}",
        "",
        "Grid:",
    ]
    lines.extend("".join(row) for row in grid)
    lines.extend(
        [
            "",
            "Rows with lengths:",
            *[f"{index:02d} {len(''.join(row)):02d} {''.join(row)}" for index,
              row in enumerate(grid, 1)],
        ]
    )
    return "\n".join(lines)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def save_matrix_png(
    path: Path,
    matrix: list[list[int]],
    append_ascii_art: bool = False,
    overlay_center_art: bool = False,
) -> None:
    grid_height_px = len(matrix) * CELL_SIZE_PX
    width = len(matrix[0]) * CELL_SIZE_PX
    ascii_art_height = len(CUSTOM_PUZZLE_BACKGROUND_ART) * \
        ASCII_ART_CELL_SIZE_PX if append_ascii_art else 0
    height = grid_height_px + ascii_art_height + \
        RED_LINE_HEIGHT_PX + WHITE_LINE_HEIGHT_PX
    rows = []

    overlay_rows = len(CUSTOM_PUZZLE_BACKGROUND_ART)
    overlay_cols = max(len(line) for line in CUSTOM_PUZZLE_BACKGROUND_ART)
    overlay_width_px = overlay_cols * ASCII_ART_CELL_SIZE_PX
    overlay_height_px = overlay_rows * ASCII_ART_CELL_SIZE_PX
    overlay_x0 = (ASCII_ART_ANCHOR_COL - 1) * CELL_SIZE_PX
    overlay_y0 = (ASCII_ART_ANCHOR_ROW - 1) * CELL_SIZE_PX

    for global_y in range(grid_height_px):
        matrix_row = global_y // CELL_SIZE_PX
        pixel_parts = []
        for global_x in range(width):
            matrix_col = global_x // CELL_SIZE_PX
            rgb = COLOR_RGB[matrix[matrix_row][matrix_col]]

            if (
                overlay_center_art
                and overlay_x0 <= global_x < overlay_x0 + overlay_width_px
                and overlay_y0 <= global_y < overlay_y0 + overlay_height_px
            ):
                art_row = (global_y - overlay_y0) // ASCII_ART_CELL_SIZE_PX
                art_col = (global_x - overlay_x0) // ASCII_ART_CELL_SIZE_PX
                char = CUSTOM_PUZZLE_BACKGROUND_ART[art_row][art_col]
                if char == "X":
                    rgb = (0, 0, 0)
                elif char != ".":
                    raise ValueError(
                        f"unsupported ASCII art character: {char!r}")

            pixel_parts.append(bytes(rgb))

        rows.append(b"\x00" + b"".join(pixel_parts))

    if append_ascii_art:
        art_width = max(
            len(line) for line in CUSTOM_PUZZLE_BACKGROUND_ART) * ASCII_ART_CELL_SIZE_PX
        left_padding = (width - art_width) // 2
        right_padding = width - art_width - left_padding
        for line in CUSTOM_PUZZLE_BACKGROUND_ART:
            art_pixels = []
            for char in line:
                if char == "X":
                    art_pixels.append(bytes((0, 0, 0)) *
                                      ASCII_ART_CELL_SIZE_PX)
                elif char == ".":
                    art_pixels.append(bytes((255, 255, 255))
                                      * ASCII_ART_CELL_SIZE_PX)
                else:
                    raise ValueError(
                        f"unsupported ASCII art character: {char!r}")
            pixels = (
                bytes((255, 255, 255)) * left_padding
                + b"".join(art_pixels)
                + bytes((255, 255, 255)) * right_padding
            )
            scanline = b"\x00" + pixels
            for _ in range(ASCII_ART_CELL_SIZE_PX):
                rows.append(scanline)

    red_scanline = b"\x00" + bytes((237, 28, 36)) * width
    white_scanline = b"\x00" + bytes((255, 255, 255)) * width
    for _ in range(RED_LINE_HEIGHT_PX):
        rows.append(red_scanline)
    for _ in range(WHITE_LINE_HEIGHT_PX):
        rows.append(white_scanline)

    raw = b"".join(rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB",
                    width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def save_puzzle_png(path: Path) -> None:
    save_matrix_png(path, PUZZLE_GRID)


message_bits_for_puzzle = security_codec.message_bits_for_puzzle


def custom_puzzle_background_matrix(row_count: int, col_count: int) -> list[list[int]]:
    matrix = [[W for _ in range(col_count)] for _ in range(row_count)]
    lines = scaled_custom_background_art()
    target_size = CUSTOM_PUZZLE_BACKGROUND_SIZE
    if target_size > row_count or target_size > col_count:
        raise ValueError(
            f"background art {target_size}x{target_size} does not fit in {row_count}x{col_count}"
        )

    row_offset = (row_count - target_size) // 2
    col_offset = (col_count - target_size) // 2
    for target_row, line in enumerate(lines):
        for target_col, char in enumerate(line):
            if char == "X":
                matrix[row_offset + target_row][col_offset + target_col] = B
            elif char == ".":
                matrix[row_offset + target_row][col_offset + target_col] = W
            else:
                raise ValueError(
                    f"unsupported background art character: {char!r}")

    return matrix


def scaled_custom_background_art() -> list[str]:
    art_height = len(CUSTOM_PUZZLE_BACKGROUND_ART)
    art_width = max(len(line) for line in CUSTOM_PUZZLE_BACKGROUND_ART)
    target_size = CUSTOM_PUZZLE_BACKGROUND_SIZE
    lines = []

    for target_row in range(target_size):
        source_row_start = target_row * art_height // target_size
        source_row_end = (target_row + 1) * art_height // target_size
        line = []
        for target_col in range(target_size):
            source_col_start = target_col * art_width // target_size
            source_col_end = (target_col + 1) * art_width // target_size
            chars = [
                CUSTOM_PUZZLE_BACKGROUND_ART[row][col]
                for row in range(source_row_start, source_row_end)
                for col in range(source_col_start, source_col_end)
            ]
            x_count = chars.count("X")
            line.append("X" if x_count * 2 >= len(chars) else ".")
        lines.append("".join(line))

    return lines


def custom_puzzle_background_report(row_count: int, col_count: int) -> list[str]:
    art_rows = len(CUSTOM_PUZZLE_BACKGROUND_ART)
    art_cols = max(len(line) for line in CUSTOM_PUZZLE_BACKGROUND_ART)
    art_width_px = art_cols * ASCII_ART_CELL_SIZE_PX
    art_height_px = art_rows * ASCII_ART_CELL_SIZE_PX
    art_x0 = (ASCII_ART_ANCHOR_COL - 1) * CELL_SIZE_PX
    art_y0 = (ASCII_ART_ANCHOR_ROW - 1) * CELL_SIZE_PX

    return [
        f"Center overlay art grid: {art_rows}x{art_cols}",
        f"Center overlay cell size: {ASCII_ART_CELL_SIZE_PX}x{ASCII_ART_CELL_SIZE_PX}px",
        "Center overlay spacing: 0px",
        f"Center overlay size: {art_width_px}x{art_height_px}px",
        f"Center overlay anchor cell: row {ASCII_ART_ANCHOR_ROW}, col {ASCII_ART_ANCHOR_COL}",
        f"Center overlay top-left pixel: x {art_x0}, y {art_y0}",
        "Center overlay art:",
        *CUSTOM_PUZZLE_BACKGROUND_ART,
    ]


def custom_puzzle_matrix_from_message(message: str) -> tuple[list[list[int]], str]:
    row_count = CUSTOM_PUZZLE_GRID_ROWS
    col_count = CUSTOM_PUZZLE_GRID_COLS
    bit_capacity = row_count * col_count
    bits = message_bits_for_puzzle(message)
    if len(bits) > bit_capacity:
        max_bytes = bit_capacity // 8
        raise ValueError(
            f"message is too long for {row_count}x{col_count}: "
            f"{len(bits)} bits needed, {bit_capacity} bits available. "
            f"Max full UTF-8 bytes here: {max_bytes}."
        )

    payload_bit_count = len(bits)
    padded_bits = bits + "0" * (bit_capacity - payload_bit_count)
    matrix = [[W for _ in range(col_count)] for _ in range(row_count)]
    for index, (bit, (row, col)) in enumerate(
        zip(padded_bits, spiral_ccw_coordinates_from_topleft(row_count, col_count)),
        start=1,
    ):
        is_message_byte_boundary = index <= payload_bit_count and index % 8 == 0
        if is_message_byte_boundary:
            matrix[row][col] = U if bit == "1" else Y
        else:
            matrix[row][col] = B if bit == "1" else W

    return matrix, padded_bits


def puzzle_grid_from_message(
    message: str = HIDDEN_URL_STEP_1,
    include_invisible_marker: bool = True,
) -> list[list[int]]:
    matrix, _bits = custom_puzzle_matrix_from_message(message)
    if include_invisible_marker:
        matrix[INVISIBLE_MARKER_ROW - 1][INVISIBLE_MARKER_COL - 1] = X
    return matrix


PUZZLE_GRID = puzzle_grid_from_message()


def generate_custom_puzzle_png(path: Path, message: str) -> str:
    row_count = CUSTOM_PUZZLE_GRID_ROWS
    col_count = CUSTOM_PUZZLE_GRID_COLS
    matrix, bits = custom_puzzle_matrix_from_message(message)
    save_matrix_png(path, matrix, overlay_center_art=True)
    decoded = security_codec.decode_ascii_prefix_from_bits(
        "".join(color_to_bit(value) for value in spiral_ccw_from_topleft(matrix)))

    if decoded != message:
        raise ValueError(
            f"custom hidden text changed: expected {message!r}, got {decoded!r}")

    return "\n".join(
        [
            f"PNG: {path}",
            f"Grid: {row_count}x{col_count}",
            f"Capacity bits: {row_count * col_count}",
            f"Payload bits: {len(message_bits_for_puzzle(message))}",
            f"Padding bits: {len(bits) - len(message_bits_for_puzzle(message))}",
            f"Hidden text: {decoded}",
            f"Original grid cell size: {CELL_SIZE_PX}x{CELL_SIZE_PX}px",
            *custom_puzzle_background_report(row_count, col_count),
            "BINARY:",
            bits,
        ]
    )


decode_ascii_prefix_from_bits = security_codec.decode_ascii_prefix_from_bits


def reconstruct_puzzle_image_report(path: Path) -> str:
    save_puzzle_png(path)

    full_stream = spiral_ccw_from_topleft(PUZZLE_GRID)
    binary = "".join(color_to_bit(value) for value in full_stream)
    decoded = decode_ascii_prefix_from_bits(binary)
    if decoded != HIDDEN_URL_STEP_1:
        raise ValueError(
            f"hidden URL changed: expected {HIDDEN_URL_STEP_1!r}, got {decoded!r}")

    blue_yellow_bits, blue_yellow_value = blue_yellow_row_value(PUZZLE_GRID)
    blue_yellow_complement = blue_yellow_value ^ (
        (1 << len(blue_yellow_bits)) - 1)
    row_sums, col_sums = matrix_sumlist(PUZZLE_GRID)
    prime_number_rows = [n for n in range(
        1, len(PUZZLE_GRID) + 1) if is_prime(n)]
    prime_number_cols = [n for n in range(
        1, len(PUZZLE_GRID[0]) + 1) if is_prime(n)]
    prime_sum_rows = [i + 1 for i,
                      value in enumerate(row_sums) if is_prime(value)]
    prime_sum_cols = [i + 1 for i,
                      value in enumerate(col_sums) if is_prime(value)]
    prime_cells = prime_index_cells(PUZZLE_GRID)
    prime_bits = "".join(color_to_bit(value)
                         for index, r, c, value in prime_cells)
    prime_blue_yellow = [
        (index, r, c, "Y" if value == Y else "U")
        for index, r, c, value in prime_cells
        if value in (U, Y)
    ]
    prime_row_col = prime_row_col_cells(PUZZLE_GRID)
    prime_row_col_bits = "".join(color_to_bit(value)
                                 for r, c, value in prime_row_col)
    prime_rownum_colsum_bits = selected_matrix_bits(
        PUZZLE_GRID, prime_number_rows, prime_sum_cols)
    prime_rowsum_colnum_bits = selected_matrix_bits(
        PUZZLE_GRID, prime_sum_rows, prime_number_cols)
    prime_rowsum_colsum_bits = selected_matrix_bits(
        PUZZLE_GRID, prime_sum_rows, prime_sum_cols)
    blue_sums = color_marker_sums(PUZZLE_GRID, U)
    yellow_sums = color_marker_sums(PUZZLE_GRID, Y)

    return "\n".join(
        [
            "GSMG puzzle reconstruction context:",
            f"Target address: {TARGET_ADDRESS}",
            f"Hidden URL: {decoded}",
            f"PNG: {path}",
            "",
            f"TOTAL BITS: {len(binary)}",
            "BINARY:",
            binary,
            "",
            "BLUE/YELLOW ROW BITS:",
            blue_yellow_bits,
            "BLUE/YELLOW ROW HEX:",
            f"0x{blue_yellow_value:0{len(blue_yellow_bits) // 4}X}",
            "BLUE/YELLOW COMPLEMENT HEX:",
            f"0x{blue_yellow_complement:0{len(blue_yellow_bits) // 4}X}",
            "",
            "MATRIX SUMLIST ROWS:",
            str(row_sums),
            "MATRIX SUMLIST COLUMNS:",
            str(col_sums),
            "MATRIX SUMLIST ROW PRIME MASK:",
            "".join("1" if is_prime(value) else "0" for value in row_sums),
            "MATRIX SUMLIST COLUMN PRIME MASK:",
            "".join("1" if is_prime(value) else "0" for value in col_sums),
            "MATRIX SUMLIST PRIME ROWS:",
            str(prime_sum_rows),
            "MATRIX SUMLIST PRIME COLUMNS:",
            str(prime_sum_cols),
            "PRIME CELL URL BITS HEX:",
            f"0x{int(prime_bits, 2):X}",
            "PRIME CELL BLUE/YELLOW MARKERS:",
            str(prime_blue_yellow),
            "PRIME ROW/COLUMN INTERSECTION BITS:",
            prime_row_col_bits,
            "PRIME ROW/COLUMN INTERSECTION HEX:",
            f"0x{int(prime_row_col_bits, 2):X}",
            "PRIME ROW NUMBER / PRIME SUM COLUMN HEX:",
            f"0x{int(prime_rownum_colsum_bits, 2):X}",
            "PRIME SUM ROW / PRIME COLUMN NUMBER HEX:",
            f"0x{int(prime_rowsum_colnum_bits, 2):X}",
            "PRIME SUM ROW / PRIME SUM COLUMN HEX:",
            f"0x{int(prime_rowsum_colsum_bits, 2):X}",
            "BLUE MATRIX SUMS:",
            str({key: value for key, value in blue_sums.items() if key != "coords"}),
            "YELLOW MATRIX SUMS:",
            str({key: value for key, value in yellow_sums.items() if key != "coords"}),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate GSMG-style puzzle images.")
    parser.add_argument(
        "message",
        nargs="?",
        default=HIDDEN_URL_STEP_1,
        help=f"text to hide in the puzzle grid; default: {HIDDEN_URL_STEP_1}",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(PUZZLE_PNG_PATH),
        help=f"PNG output path; default: {PUZZLE_PNG_PATH}",
    )
    parser.add_argument(
        "--original",
        action="store_true",
        help="reconstruct the original phase 0 image and print analysis",
    )
    args = parser.parse_args()

    if args.original:
        print(reconstruct_puzzle_image_report(args.output))
    else:
        print(generate_custom_puzzle_png(args.output, args.message))


if __name__ == "__main__":
    main()
