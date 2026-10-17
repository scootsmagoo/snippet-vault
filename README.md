# SnippetVault

**Developer Code Snippet Manager** — Local-first, zero-dependency code snippet storage with a clean dark-themed web UI and REST API.

> 🚀 Micro-SaaS MVP: Built by the Nightly Builder as part of Murphy's passive income portfolio.
> Free tier: local-only. Premium (planned): cloud sync, team sharing, IDE integrations.

## Quick Start

```bash
# Start the server
python3 server.py

# Open in browser
open http://127.0.0.1:3040
```

Custom port: `python3 server.py --port 8080`

## Features

- **REST API** — Full CRUD for snippets with search, tags, export/import
- **Dark-themed Web UI** — Sidebar navigation, tag filtering, code editor
- **Zero dependencies** — Python 3 stdlib only, no `pip install` needed
- **JSON storage** — All data in a simple `snippets.json` file
- **Export/Import** — Backup and restore your snippet library
- **Keyboard shortcuts** — `Ctrl+S` save, `Ctrl+N` new snippet
- **Syntax highlighting** — Language selector with 16 languages (highlighting via monospace; full Prism.js integration planned)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/snippets` | List all snippets (supports `?tag=`, `?lang=`) |
| GET | `/api/snippets/<id>` | Get one snippet |
| POST | `/api/snippets` | Create a snippet |
| PUT | `/api/snippets/<id>` | Update a snippet |
| DELETE | `/api/snippets/<id>` | Delete a snippet |
| GET | `/api/snippets/search?q=` | Search snippets |
| GET | `/api/tags` | List all tags |
| GET | `/api/stats` | Snippet counts by language |
| GET | `/api/export` | Export all as JSON |
| POST | `/api/import` | Import from JSON |
| GET | `/api/health` | Health check |

## Data Format

```json
{
  "id": "a1b2c3d4e5f6",
  "title": "React useEffect cleanup",
  "code": "useEffect(() => {\n  const sub = subscribe();\n  return () => sub.unsubscribe();\n}, []);",
  "language": "typescript",
  "tags": ["react", "hooks"],
  "description": "Cleanup pattern for useEffect",
  "created": "2026-10-17T06:00:00Z",
  "updated": "2026-10-17T06:00:00Z"
}
```

## Roadmap

- [ ] Syntax highlighting (Prism.js)
- [ ] Dark/light theme toggle
- [ ] Snippet favorites / pinning
- [ ] Cloud sync (premium)
- [ ] IDE plugin (VS Code)
- [ ] Team sharing (premium)
- [ ] Markdown notes per snippet

## License

MIT