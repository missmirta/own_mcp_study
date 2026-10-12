"""MCP-сервер для конспекту з Notion.

Нотатки читаються з папки з Markdown-експортом Notion. Шлях до неї задає
змінна середовища NOTES_DIR (за замовчуванням папка notes/ поруч із сервером).
"""

import os
from pathlib import Path
from urllib.parse import quote

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import Resource
from pydantic import BaseModel

import notes

NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path(__file__).parent / "notes"))



def note_uri(note_id: str) -> str:
    return "note:///" + quote(note_id, safe="/")


class NotesServer(MCPServer):
    """MCPServer, який додає кожну нотатку в resources/list.

    Декоратор @resource з шаблоном лише вміє читати нотатку за адресою, а клієнти
    (наприклад, меню «+» у Claude Desktop) показують тільки ресурси зі списку.
    Нотатки змінюються разом з експортом, тож список будуємо на кожен запит.
    """

    async def list_resources(self) -> list[Resource]:
        resources = await super().list_resources()
        if NOTES_DIR.is_dir():
            resources += [
                Resource(uri=note_uri(n.id), name=n.id, title=n.title, mime_type="text/markdown")
                for n in notes.load_notes(NOTES_DIR).values()
            ]
        return resources


mcp = NotesServer("notes")


class NoteInfo(BaseModel):
    id: str
    title: str


class SearchHit(BaseModel):
    note_id: str
    line: int
    text: str


def _notes() -> dict[str, notes.Note]:
    # Читаємо папку на кожен виклик: свіжий експорт підхоплюється без перезапуску.
    if not NOTES_DIR.is_dir():
        raise ToolError(f"Папку з нотатками не знайдено: {NOTES_DIR}. Вкажи її в NOTES_DIR.")
    return notes.load_notes(NOTES_DIR)


@mcp.tool()
def ping(message: str = "ping") -> str:
    """Перевірка зв'язку: повертає повідомлення назад з позначкою сервера."""
    return f"notes-mcp отримав: {message}"


@mcp.tool()
def list_notes() -> list[NoteInfo]:
    """Список усіх нотаток конспекту: id (для read_note) і заголовок."""
    return [NoteInfo(id=n.id, title=n.title) for n in _notes().values()]


@mcp.tool()
def read_note(note_id: str) -> str:
    """Повний текст нотатки в Markdown. note_id береться з list_notes або search_notes."""
    all_notes = _notes()
    if note_id not in all_notes:
        raise ToolError(f"Нотатки «{note_id}» немає. Доступні: {', '.join(all_notes)}")
    return all_notes[note_id].read()


@mcp.tool()
def search_notes(query: str, limit: int = 20) -> list[SearchHit]:
    """Шукає текст у всіх нотатках (без урахування регістру) і повертає рядки зі збігами."""
    return [SearchHit(note_id=m.note_id, line=m.line, text=m.text) for m in notes.search(_notes(), query, limit)]


@mcp.resource("note:///{+note_id}", mime_type="text/markdown")
def note(note_id: str) -> str:
    """Нотатка з конспекту як ресурс: її можна прикріпити до розмови цілком."""
    all_notes = notes.load_notes(NOTES_DIR) if NOTES_DIR.is_dir() else {}
    if note_id not in all_notes:
        raise ResourceError(f"Нотатки «{note_id}» немає")
    return all_notes[note_id].read()


@mcp.prompt(title="Квіз за темою")
def quiz(topic: str, questions: int = 5) -> str:
    """Квіз для повторення: бере нотатки, де згадується тема, і просить скласти питання."""
    all_notes = _notes()
    found = {m.note_id for m in notes.search(all_notes, topic, limit=1000)}
    if not found:
        return f"У моєму конспекті нічого немає про «{topic}». Скажи мені про це і запропонуй схожі теми зі списку: {', '.join(all_notes)}."
    material = "\n\n".join(f"--- {note_id} ---\n{all_notes[note_id].read()}" for note_id in sorted(found))
    return (
        f"Склади квіз з {questions} питань на тему «{topic}», спираючись лише на мій конспект нижче. "
        "Став питання по одному, чекай моєї відповіді, кажи, чи правильно, і коротко пояснюй з конспекту. "
        "Наприкінці підсумуй, що варто повторити.\n\n"
        f"{material}"
    )


def main() -> None:
    # stdio: клієнт (Claude Desktop, Inspector) запускає сервер як процес
    # і спілкується з ним через stdin/stdout.
    mcp.run()


if __name__ == "__main__":
    main()
