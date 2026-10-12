"""MCP server for personal Notion notes.

Where the notes come from:
- if NOTION_TOKEN and NOTION_PAGE are set, directly from the Notion API (live notes);
- otherwise from a folder with a Notion Markdown export: NOTES_DIR, notes/ by default.
"""

import os
from pathlib import Path
from urllib.parse import quote

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import Resource
from pydantic import BaseModel

import notes
from notion import NotionSource

NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path(__file__).parent / "notes"))
NOTION = (
    NotionSource(os.environ["NOTION_TOKEN"], os.environ["NOTION_PAGE"])
    if os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_PAGE")
    else None
)


def load_all() -> dict[str, notes.Note]:
    if NOTION is not None:
        return NOTION.load()
    if not NOTES_DIR.is_dir():
        raise FileNotFoundError(f"Notes folder not found: {NOTES_DIR}. Set it in NOTES_DIR.")
    return notes.load_notes(NOTES_DIR)



def note_uri(note_id: str) -> str:
    return "note:///" + quote(note_id, safe="/")


class NotesServer(MCPServer):
    """MCPServer that adds every note to resources/list.

    The @resource decorator with a template can only read a note by its address, while clients
    (e.g. the "+" menu in Claude Desktop) only show resources from the list.
    Notes change along with the source, so the list is built on every request.
    """

    async def list_resources(self) -> list[Resource]:
        resources = await super().list_resources()
        try:
            all_notes = load_all()
        except (FileNotFoundError, PermissionError):
            return resources
        return resources + [
            Resource(uri=note_uri(n.id), name=n.id, title=n.title, mime_type="text/markdown")
            for n in all_notes.values()
        ]


mcp = NotesServer("notes")


class NoteInfo(BaseModel):
    id: str
    title: str


class SearchHit(BaseModel):
    note_id: str
    line: int
    text: str


def _notes() -> dict[str, notes.Note]:
    # Read on every call: a fresh export is picked up without a restart,
    # and NotionSource caches API responses for a minute on its own.
    try:
        return load_all()
    except (FileNotFoundError, PermissionError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def ping(message: str = "ping") -> str:
    """Connectivity check: returns the message back with the server's tag."""
    return f"notes-mcp received: {message}"


@mcp.tool()
def list_notes() -> list[NoteInfo]:
    """List of all notes: id (for read_note) and title."""
    return [NoteInfo(id=n.id, title=n.title) for n in _notes().values()]


@mcp.tool()
def read_note(note_id: str) -> str:
    """Full text of a note in Markdown. note_id comes from list_notes or search_notes."""
    all_notes = _notes()
    if note_id not in all_notes:
        raise ToolError(f"Note '{note_id}' does not exist. Available: {', '.join(all_notes)}")
    return all_notes[note_id].text


@mcp.tool()
def search_notes(query: str, limit: int = 20) -> list[SearchHit]:
    """Searches all notes for text (case-insensitive) and returns the matching lines."""
    return [SearchHit(note_id=m.note_id, line=m.line, text=m.text) for m in notes.search(_notes(), query, limit)]


@mcp.resource("note:///{+note_id}", mime_type="text/markdown")
def note(note_id: str) -> str:
    """A note as a resource: it can be attached to a conversation in full."""
    try:
        all_notes = load_all()
    except (FileNotFoundError, PermissionError) as exc:
        raise ResourceError(str(exc)) from exc
    if note_id not in all_notes:
        raise ResourceError(f"Note '{note_id}' does not exist")
    return all_notes[note_id].text


@mcp.prompt(title="Quiz on a topic")
def quiz(topic: str, questions: int = 5) -> str:
    """Revision quiz: takes the notes that mention the topic and asks for questions to be made."""
    all_notes = _notes()
    found = {m.note_id for m in notes.search(all_notes, topic, limit=1000)}
    if not found:
        return f"My notes contain nothing about '{topic}'. Tell me so and suggest similar topics from this list: {', '.join(all_notes)}."
    material = "\n\n".join(f"--- {note_id} ---\n{all_notes[note_id].text}" for note_id in sorted(found))
    return (
        f"Make a quiz of {questions} questions on the topic '{topic}', relying only on my notes below. "
        "Ask the questions one at a time, wait for my answer, say whether it is right, and briefly explain using the notes. "
        "At the end, sum up what is worth reviewing.\n\n"
        f"{material}"
    )


def main() -> None:
    # stdio: the client (Claude Desktop, Inspector) launches the server as a process
    # and talks to it over stdin/stdout.
    mcp.run()


if __name__ == "__main__":
    main()
