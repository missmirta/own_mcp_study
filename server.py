"""MCP-сервер для конспекту з Notion.

Крок 1: лише скелет з одним інструментом, щоб перевірити, що клієнт бачить сервер.
"""

from mcp.server import MCPServer

mcp = MCPServer("notes")


@mcp.tool()
def ping(message: str = "ping") -> str:
    """Перевірка зв'язку: повертає повідомлення назад з позначкою сервера."""
    return f"notes-mcp отримав: {message}"


def main() -> None:
    # stdio: клієнт (Claude Desktop, Inspector) запускає сервер як процес
    # і спілкується з ним через stdin/stdout.
    mcp.run()


if __name__ == "__main__":
    main()
