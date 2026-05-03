"""Public orchestrator/API for the local GSMG puzzle phases.

Phase-specific facts live in each phase's own ``phase.py``. This module keeps
the shared dataclasses, HTML parsing, and dispatch functions.

Typical use:

    import phase_api

    phase2 = phase_api.load_phase("phase2")
    print(phase2.blobs[0].text)

    plaintext = phase_api.decrypt_phase2()
    phase3_html = phase_api.decrypt_phase3()
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import sys

import security_codec


DEFAULT_CIPHER = security_codec.DEFAULT_CIPHER
DEFAULT_DIGEST = security_codec.DEFAULT_DIGEST
compact = security_codec.compact
sha256_text = security_codec.sha256_text
decrypt_openssl_blob = security_codec.decrypt_openssl_blob
is_openssl_blob = security_codec.is_openssl_blob
PROJECT_ROOT = Path(__file__).resolve().parent
PHASE_API_FILES = {
    "phase0": PROJECT_ROOT / "primary-path" / "phase0" / "phase.py",
    "phase1": PROJECT_ROOT / "primary-path" / "phase1" / "phase.py",
    "phase2": PROJECT_ROOT / "primary-path" / "phase2" / "phase.py",
    "phase3": PROJECT_ROOT / "primary-path" / "phase3" / "phase.py",
    "secondary": PROJECT_ROOT / "secondary-path" / "phase.py",
}

@dataclass(frozen=True)
class TextArea:
    title: str | None
    text: str


@dataclass(frozen=True)
class Form:
    action: str | None
    method: str | None
    inputs: tuple[str, ...]


@dataclass(frozen=True)
class Blob:
    title: str | None
    text: str
    source: str
    index: int


@dataclass(frozen=True)
class ParsedHTML:
    headings: tuple[str, ...]
    prose: tuple[str, ...]
    images: tuple[str, ...]
    forms: tuple[Form, ...]
    textareas: tuple[TextArea, ...]
    aes_blobs: tuple[Blob, ...]


@dataclass(frozen=True)
class Phase:
    name: str
    path: Path | None
    html: str | None
    parsed: ParsedHTML | None
    blobs: tuple[Blob, ...]
    notes: tuple[str, ...] = ()


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_heading: str | None = None
        self.headings: list[str] = []
        self.prose: list[str] = []
        self.images: list[str] = []
        self.forms: list[Form] = []
        self.textareas: list[TextArea] = []
        self._in_heading = False
        self._heading_parts: list[str] = []
        self._in_textarea = False
        self._textarea_parts: list[str] = []
        self._ignore_depth = 0
        self._form_action: str | None = None
        self._form_method: str | None = None
        self._form_inputs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = dict(attrs)
        if tag in {"script", "style"}:
            self._ignore_depth += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_heading = True
            self._heading_parts = []
        elif tag == "textarea":
            self._in_textarea = True
            self._textarea_parts = []
        elif tag == "img" and attrs_dict.get("src"):
            self.images.append(attrs_dict["src"] or "")
        elif tag == "form":
            self._form_action = attrs_dict.get("action")
            self._form_method = attrs_dict.get("method")
            self._form_inputs = []
        elif tag == "input" and self._form_action is not None:
            name = attrs_dict.get("name")
            if name:
                self._form_inputs.append(name)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self._ignore_depth:
            self._ignore_depth -= 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._in_heading:
            heading = clean_text("".join(self._heading_parts))
            if heading:
                self.current_heading = heading
                self.headings.append(heading)
                self.prose.append(heading)
            self._in_heading = False
        elif tag == "textarea" and self._in_textarea:
            self.textareas.append(TextArea(self.current_heading, clean_text("".join(self._textarea_parts))))
            self._in_textarea = False
        elif tag == "form" and self._form_action is not None:
            self.forms.append(Form(self._form_action, self._form_method, tuple(self._form_inputs)))
            self._form_action = None
            self._form_method = None
            self._form_inputs = []

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        if self._in_textarea:
            self._textarea_parts.append(data)
        elif self._in_heading:
            self._heading_parts.append(data)
        else:
            text = clean_text(data)
            if text:
                self.prose.append(text)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_html(html_text: str) -> ParsedHTML:
    parser = _Parser()
    parser.feed(html_text)
    parser.close()

    aes_blobs = detect_openssl_blobs(parser.textareas, parser.prose)

    return ParsedHTML(
        headings=tuple(parser.headings),
        prose=tuple(parser.prose),
        images=tuple(parser.images),
        forms=tuple(parser.forms),
        textareas=tuple(parser.textareas),
        aes_blobs=aes_blobs,
    )


def detect_openssl_blobs(
    textareas: list[TextArea] | tuple[TextArea, ...],
    prose: list[str] | tuple[str, ...] = (),
) -> tuple[Blob, ...]:
    blobs: list[Blob] = []
    for textarea in textareas:
        text = compact(textarea.text)
        if is_openssl_blob(text):
            blobs.append(Blob(textarea.title, text, "textarea", len(blobs)))

    for block in prose:
        text = compact(block)
        if is_openssl_blob(text):
            blobs.append(Blob(None, text, "prose", len(blobs)))

    return tuple(blobs)


def openssl_blob_at(parsed: ParsedHTML, index: int = 0) -> str:
    return parsed.aes_blobs[index].text


def project_path(*parts: str | Path) -> Path:
    return PROJECT_ROOT.joinpath(*map(Path, parts))


def normalize_phase_name(name: str) -> str:
    normalized = name.lower().replace("_", "-").strip()
    aliases = {
        "0": "phase0",
        "phase-0": "phase0",
        "stage0": "phase0",
        "stage-0": "phase0",
        "1": "phase1",
        "phase-1": "phase1",
        "2": "phase2",
        "phase-2": "phase2",
        "3": "phase3",
        "phase-3": "phase3",
        "salphaseion": "secondary",
        "secondary-path": "secondary",
    }
    key = aliases.get(normalized, normalized)
    if key not in PHASE_API_FILES:
        raise KeyError(f"Unknown phase {name!r}")
    return key


def list_phases() -> tuple[str, ...]:
    return tuple(PHASE_API_FILES)


def phase_api_path(name: str, root: str | Path = PROJECT_ROOT) -> Path:
    key = normalize_phase_name(name)
    path = Path(root) / PHASE_API_FILES[key].relative_to(PROJECT_ROOT)
    if not path.exists():
        raise FileNotFoundError(f"No phase API found for {name!r}")
    return path


def phase_api(name: str, root: str | Path = PROJECT_ROOT):
    key = normalize_phase_name(name)
    path = phase_api_path(key, root)
    module_name = f"gsmg_{key}_phase_api"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load phase API from {path}")
    api = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = api
    spec.loader.exec_module(api)
    return api


def phase_path(name: str, root: str | Path = PROJECT_ROOT) -> Path:
    api = phase_api(name, root)
    if not hasattr(api, "path"):
        raise FileNotFoundError(f"No local path configured for {name!r}")
    path = api.path()
    if not path.exists():
        raise FileNotFoundError(f"No local file found for {name!r}: {path}")
    return path


def load_phase(name: str, root: str | Path = PROJECT_ROOT) -> Phase:
    return phase_api(name, root).load()


def original_textareas(name: str, root: str | Path = PROJECT_ROOT) -> tuple[TextArea, ...]:
    phase = load_phase(name, root)
    return phase.parsed.textareas if phase.parsed else ()


def original_blobs(name: str, root: str | Path = PROJECT_ROOT) -> tuple[Blob, ...]:
    return load_phase(name, root).blobs


def original_blob(name: str, index: int = 0, root: str | Path = PROJECT_ROOT) -> str:
    return original_blobs(name, root)[index].text


def decrypt_phase_blob(
    name: str,
    index: int,
    password: str,
    root: str | Path = PROJECT_ROOT,
    cipher: str = DEFAULT_CIPHER,
    digest: str = DEFAULT_DIGEST,
    pbkdf2: bool = False,
) -> str:
    return decrypt_openssl_blob(
        original_blob(name, index, root),
        password,
        cipher=cipher,
        digest=digest,
        pbkdf2=pbkdf2,
    )


def decrypt_phase2(root: str | Path = PROJECT_ROOT) -> str:
    return phase_api("phase2", root).decrypt()


def decrypt_phase3(root: str | Path = PROJECT_ROOT) -> str:
    return phase_api("phase3", root).decrypt()


def extract_phase3(output: str | Path, root: str | Path = PROJECT_ROOT) -> Path:
    base = Path(root)
    out_path = Path(output)
    if not out_path.is_absolute():
        out_path = base / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(decrypt_phase3(base))
    return out_path
