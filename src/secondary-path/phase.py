"""Secondary path information and API helpers."""

from __future__ import annotations

from pathlib import Path
import sys


PHASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PHASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import phase_api
import security_codec


HTML_PATH = PHASE_DIR / "phase.html"
DECENTRALAND_COORDS = (-41, -17)
CONTENT_ID = "QmeRy5MjmEZ2W6J3DwhQfht5HKBKXBFpoGzSkzmjeGKiDK"
AUDIO_URL = "https://peer.decentraland.org/content/contents/QmeRy5MjmEZ2W6J3DwhQfht5HKBKXBFpoGzSkzmjeGKiDK"
HASH_INPUT = "GSMGIO5BTCPUZZLECHALLENGE1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe"
SALPHASEION_HASH = security_codec.sha256_text(HASH_INPUT)
SALPHASEION_URL = "https://gsmg.io/89727c598b9cd1cf8873f27cb7057f050645ddb6a7a157a110239ac0152f6a32"


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
        name="secondary",
        path=path(),
        html=html_text,
        parsed=parsed_html,
        blobs=parsed_html.aes_blobs,
    )


def textareas() -> tuple[phase_api.TextArea, ...]:
    return parsed().textareas


def blobs() -> tuple[phase_api.Blob, ...]:
    return parsed().aes_blobs


def salphaseion_text() -> str:
    return textareas()[0].text


def cosmic_duality_blob() -> str:
    return blobs()[0].text


def salphaseion_url() -> str:
    return SALPHASEION_URL
