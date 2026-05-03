"""Phase 1 information and API helpers."""

from __future__ import annotations

from pathlib import Path
import sys


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import phase_api


HTML_PATH = PHASE_DIR / "phase.html"
URL = "https://gsmg.io/theseedisplanted"
PASSWORD = "theflowerblossomsthroughwhatseemstobeaconcretesurface"
NEXT_URL = "https://gsmg.io/choiceisanillusioncreatedbetweenthosewithpowerandthosewithoutaveryspecialdessertiwroteitmyself"
SONG = "The Warning - Logic"


def path() -> Path:
    return HTML_PATH


def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8", errors="replace")


def parsed() -> phase_api.ParsedHTML:
    return phase_api.parse_html(html())


def load() -> phase_api.Phase:
    html_text = html()
    parsed_html = phase_api.parse_html(html_text)
    return phase_api.Phase(
        name="phase1",
        path=path(),
        html=html_text,
        parsed=parsed_html,
        blobs=parsed_html.aes_blobs,
    )


def images() -> tuple[str, ...]:
    return parsed().images


def forms() -> tuple[phase_api.Form, ...]:
    return parsed().forms


def password() -> str:
    return PASSWORD


def next_url() -> str:
    return NEXT_URL
