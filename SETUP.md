# DocuCommit — Local Development Setup

This guide walks every teammate through getting DocuCommit running locally,
from a fresh clone to a working app in the browser. If you hit something not
covered here, add it — this file is the source of truth.

## 0. Prerequisites

| Tool   | Min version | Check                   |
| ------ | ----------- | ----------------------- |
| Git    | 2.30+       | `git --version`         |
| Python | 3.11+       | `python3 --version`     |
| Node   | 18+         | `node --version`        |
| npm    | 9+          | `npm --version`         |

> macOS: install via [Homebrew](https://brew.sh):
> `brew install git python node`
>
> Windows: use [Git for Windows](https://git-scm.com/download/win),
> [python.org](https://www.python.org/downloads/) (check "Add to PATH"),
> and [nodejs.org](https://nodejs.org/).

## 1. Clone

```bash
git clone git@github.com:dangjacob101/DocuCommit.git
cd DocuCommit
```

(If SSH gives `Permission denied (publickey)`, either add your SSH key at
<https://github.com/settings/keys> or clone over HTTPS with a Personal Access
Token: `git clone https://github.com/dangjacob101/DocuCommit.git`.)

## 2. Backend (Frank / Flask)

```bash
cd Frank
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python app.py
```

You should see:

```
* Running on http://127.0.0.1:5000
```

Smoke-test in a second terminal:

```bash
curl http://127.0.0.1:5000/api/documents
# -> []
```

**If you get `403 Forbidden` with `Server: AirTunes/...`, you're on macOS and
AirPlay Receiver is squatting port 5000.** See the troubleshooting section
below.

## 3. Frontend (client / React + Vite)

In a new terminal (leave the backend running):

```bash
cd client
npm install
npm run dev
```

Open <http://localhost:5173>. You should see the DocuCommit dashboard.

## 4. Verify everything is wired up

1. Click **New Document**, give it a title and some text, save.
2. Refresh the page — the document should persist.
3. Open the document, click **New Branch**, name it, make an edit, commit it.
4. Click **Compare to Main** — you should see a red/green diff.

If all four work, your environment is good to go.

## 5. Run the test suites

### Backend

```bash
cd Frank
source .venv/bin/activate
python test_diff_engine.py
```

### Frontend

```bash
cd client
npm run test:run
```

## Troubleshooting

### macOS: backend boots but every API call returns 403 (`Server: AirTunes/...`)

macOS 12+ uses port 5000 for AirPlay Receiver, which intercepts every request
before Flask sees it. Two fixes:

**Option A — turn off AirPlay Receiver (one-time):**
*System Settings → General → AirDrop & Handoff → AirPlay Receiver: off.*

**Option B — run the backend on a different port (no system changes):**

```bash
# in Frank/.env
PORT=5001
```

```bash
# in client/.env.local  (create this file)
VITE_API_TARGET=http://localhost:5001
```

Restart both the backend and the Vite dev server.

### `ImportError: No module named 'flask'` or similar

You forgot to activate the venv. Run `source .venv/bin/activate` (Mac/Linux)
or `.venv\Scripts\activate` (Windows) before `python app.py`.

### Vite dev server runs but API calls return 500 / network errors

The backend isn't running, or it's running on a different port than what
`VITE_API_TARGET` points to. Check both terminals.

### "documents.db is locked"

Some editor (e.g. a DB viewer) has the SQLite file open. Close it. Or just
delete `Frank/documents.db` to start fresh — `app.py` re-creates it on boot.

### Resetting the database

```bash
rm Frank/documents.db
# next `python app.py` will recreate it empty
```

## Branch / PR workflow (read before pushing!)

- **Never push directly to `main`.** Protected by branch rules.
- Create a feature branch off `main`:
  `git checkout -b yourname/short-description`
- Commit, push, open a PR on GitHub.
- At least one approval is required before merge.
- Use **Squash and merge** to keep `main` history clean.

## Project layout (at a glance)

```
DocuCommit/
├── Frank/                  # Python / Flask backend
│   ├── app.py              # entrypoint
│   ├── models.py           # SQLAlchemy: User, Document, Branch, Commit
│   ├── diff_engine.py      # Myers diff implementation
│   ├── routes/             # REST endpoints (documents, branches, merge)
│   └── test_diff_engine.py
├── client/                 # React + Vite frontend
│   └── src/
│       ├── components/     # Editor, DiffViewer, BranchPicker, …
│       └── api.js          # all calls to the backend
└── SETUP.md                # ← this file
```
