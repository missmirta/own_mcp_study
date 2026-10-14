# DocSearchByMcp

A custom MCP server for personal Notion notes. Built step by step to learn the Model Context Protocol.

The notes it serves: [Machine Learning on Notion](https://app.notion.com/p/Machine-Learning-3b2736c1ab2c8060b525fd7bc7052f74).

## Plan

1. **Server skeleton** with a single `ping` tool, checked in MCP Inspector and Claude Desktop. ✅
2. **Notes as data**: a Markdown export from Notion and the tools `list_notes`, `read_note`, `search_notes`. ✅
3. **The rest of the protocol**: a resource for every note and a "make a quiz on a topic" prompt. ✅
4. **Live Notion**: reading through the Notion API instead of an export. ← currently here

## Running

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/missmirta/own_mcp_study
cd own_mcp_study
uv sync
uv run pytest        # tests
```

### Notes

The server reads a Markdown export from Notion:

1. In Notion, open the notes page → **⋯ → Export**.
2. Choose the **Markdown & CSV** format and enable **Include subpages** (otherwise only the top page is exported, without subpages).
3. Unzip into a `notes/` folder in the repository (it is in .gitignore, so your notes won't end up in git) or into any other folder and point `NOTES_DIR` at it.

Tools:

- `list_notes` — list of notes with ids. Notion hashes are stripped from the names, so ids look like `Machine Learning/PyTorch`.
- `read_note(note_id)` — full text of a note.
- `search_notes(query, limit=20)` — matching lines, case-insensitive.

Resources and prompt:

- Every note is a resource `note:///<id>`. In Claude Desktop they appear in the **+ → notes** menu, and a note can be attached to a conversation in full.
- The prompt `quiz(topic, questions=5)` finds the notes that mention the topic and asks Claude to run a quiz, one question at a time. In Claude Desktop it is also in the **+ → notes** menu.

The three MCP parts and who triggers them: the model decides to call **tools**, the user or the app attaches **resources**, and the user picks **prompts** as ready-made scenarios.

### Live Notion (no export)

The server can read the notes straight from Notion, so there is nothing to export:

1. Open [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**, type Internal, capability **Read content**. Copy the token (`ntn_…` or `secret_…`).
2. Open the root page of your notes → **⋯ → Connections** → add your integration. Subpages inherit access.
3. Copy the link to that page (**Share → Copy link**).
4. Add to `env` in the Claude Desktop config:

```json
"env": {
  "NOTION_TOKEN": "ntn_...",
  "NOTION_PAGE": "https://www.notion.so/Machine-Learning-3b2736c1ab2c8060b525fd7bc7052f74"
}
```

When both variables are set, `NOTES_DIR` is ignored. The server walks the root page and all subpages (both `child_page` and page links), converts the blocks to Markdown and caches the result for a minute, because the Notion API is slow and rate-limited. The token goes nowhere except the headers of requests to api.notion.com. Images and embedded databases are skipped for now.

To update an exported folder, just replace the files: the server re-reads it on every call.

### Checking in MCP Inspector

Inspector shows which tools a client sees and lets you call them by hand (requires Node.js):

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

In the window that opens, click **Connect**, then **Tools → List Tools → ping → Run Tool**.

### Connecting to Claude Desktop

Open **Settings → Developer → Edit Config** and add the server to `claude_desktop_config.json`
(replace the paths with your own; on Windows use `\\`):

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": ["run", "--directory", "/FULL/PATH/to/own_mcp_study", "server.py"],
      "env": { "NOTES_DIR": "/FULL/PATH/to/export" }
    }
  }
}
```

`env` can be removed if the export is in `notes/`.

Restart Claude Desktop and ask, for example: "what do my notes say about Tensor Cores?"
If `uv` is not found, put its full path in `command` (`which uv`).
