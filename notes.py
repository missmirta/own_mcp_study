"""Reading notes from a Notion Markdown export.

Notion appends a 32-character id to every file and folder name
("Machine Learning 3b2736c1ab2c8060b525fd7bc7052f74.md"). We strip it,
so a note id looks like a path with human-readable names: "Machine Learning/PyTorch".
"""

import re
from dataclasses import dataclass
from pathlib import Path

NOTION_ID = re.compile(r" [0-9a-f]{32}$")


@dataclass
class Note:
    id: str
    title: str
    text: str


def _clean(name: str) -> str:
    return NOTION_ID.sub("", name)


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_notes(notes_dir: Path) -> dict[str, Note]:
    """Finds all .md files in the folder (including nested ones) and returns them by id."""
    notes: dict[str, Note] = {}
    for path in notes_dir.rglob("*.md"):
        rel = path.relative_to(notes_dir).with_suffix("")
        note_id = "/".join(_clean(part) for part in rel.parts)
        text = path.read_text(encoding="utf-8")
        notes[note_id] = Note(note_id, _title(text, rel.name), text)
    return dict(sorted(notes.items()))


@dataclass
class Match:
    note_id: str
    line: int
    text: str


def search(notes: dict[str, Note], query: str, limit: int) -> list[Match]:
    """Case-insensitive search; returns the lines where the query occurs."""
    needle = query.casefold()
    matches: list[Match] = []
    for note in notes.values():
        for number, line in enumerate(note.text.splitlines(), start=1):
            if needle in line.casefold():
                matches.append(Match(note.id, number, line.strip()))
                if len(matches) >= limit:
                    return matches
    return matches
