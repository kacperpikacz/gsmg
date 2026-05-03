"""Phase 2 information/API helpers.

The local source page contains two OpenSSL blobs, but this module exposes
Phase 2 only. Phase 3 reads the second blob from this same source file.
"""

from __future__ import annotations

from pathlib import Path
import sys


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import phase_api
import security_codec


HTML_PATH = PHASE_DIR / "phase.html"
URL = "https://gsmg.io/choiceisanillusioncreatedbetweenthosewithpowerandthosewithoutaveryspecialdessertiwroteitmyself"

PHASE2_PASSWORD = "causality"
PHASE2_PASSWORD_SHA256 = "eb3efb5151e6255994711fe8f2264427ceeebf88109e1d7fad5b0a8b6d07e5bf"


def path() -> Path:
    return HTML_PATH


def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8", errors="replace")


def parsed() -> phase_api.ParsedHTML:
    return phase_api.parse_html(html())


def source_blobs() -> tuple[phase_api.Blob, ...]:
    return parsed().aes_blobs


def blobs() -> tuple[phase_api.Blob, ...]:
    return source_blobs()[:1]


def load() -> phase_api.Phase:
    html_text = html()
    parsed_html = phase_api.parse_html(html_text)
    return phase_api.Phase(
        name="phase2",
        path=path(),
        html=html_text,
        parsed=parsed_html,
        blobs=parsed_html.aes_blobs[:1],
        notes=("phase2 source also contains the encrypted phase3 blob",),
    )


def phase2_blob() -> str:
    return blobs()[0].text


def decrypt() -> str:
    return security_codec.decrypt_openssl_blob(phase2_blob(), PHASE2_PASSWORD_SHA256)


def decrypt_phase2() -> str:
    return decrypt()


def password() -> str:
    return PHASE2_PASSWORD


def password_sha256() -> str:
    return PHASE2_PASSWORD_SHA256
