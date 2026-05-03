"""Phase 0 information and API helpers."""

from __future__ import annotations

from pathlib import Path
import sys


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import puzzle_image
import phase_api
import security_codec


IMAGE_PATH = PHASE_DIR / "puzzle.png"
HINT = "follow the white rabbit"
NEXT_URL = "https://gsmg.io/theseedisplanted"
HIDDEN_URL = NEXT_URL.removeprefix("https://")
GRID_TEXT = """00110b0010110y
11b1001110b011
1101110b001001
0110b000011101
0b1000110y0110
100110y010y011
100b1100010y00
b11000000010y0
00011b0111110b
11b111y0110001
1101000y011011
11110010b01100
0b0111010y0110
01b0110110b011"""


def path() -> Path:
    return IMAGE_PATH


def load() -> phase_api.Phase:
    return phase_api.Phase(
        name="phase0",
        path=path(),
        html=None,
        parsed=None,
        blobs=(),
        notes=(decode_url(),),
    )


def hidden_url() -> str:
    return HIDDEN_URL


def grid(include_invisible_marker: bool = True) -> list[list[int]]:
    return puzzle_image.puzzle_grid_from_message(
        HIDDEN_URL,
        include_invisible_marker=include_invisible_marker,
    )


def binary() -> str:
    return "".join(
        puzzle_image.color_to_bit(value)
        for value in puzzle_image.spiral_ccw_from_topleft(grid())
    )


def decode() -> str:
    return security_codec.decode_ascii_prefix_from_bits(binary())


def generate(output: str | Path = IMAGE_PATH) -> Path:
    output_path = Path(output)
    puzzle_image.save_matrix_png(output_path, grid())
    return output_path


def report(output: str | Path = IMAGE_PATH) -> str:
    return puzzle_image.reconstruct_puzzle_image_report(Path(output))


def decode_url(grid_text: str = GRID_TEXT) -> str:
    return security_codec.decode_spiral_grid_text(grid_text)
