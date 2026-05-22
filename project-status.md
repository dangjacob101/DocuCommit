# DocuCommit — Project Status

Last updated: 2026-05-22

---

## Completed

### Dynamic Data Display — 50 pts

The frontend fetches and renders live data from the backend on every page. `DocumentDashboard` lists documents, `Editor` loads branch content, `CommitHistorySidebar` shows commit history, `BranchPicker` populates from the API, and `DiffViewer` renders a visual line-by-line comparison.

---

### Upload Data from Client to Back-End — 50 pts

Multiple POST/PUT routes are wired end-to-end:
- `POST /api/documents` — create document
- `POST /api/documents/:id/branches` — create branch
- `POST /api/branches/:id/commits` — commit a revision
- `POST /api/branches/:id/merge` — merge a branch
- `PUT /api/documents/:id` — update document

All have corresponding frontend API functions in `api.js` and UI triggers in components.

---

### Git Version Control — 100 pts

Active remote tracking, feature branches (`feature/custom-diff-engine`), consistent commit history, and a `.gitignore` are all in place.

---

### Code Readability — 100 pts

- Identifiers are descriptive throughout (`reconstruct_branch_content`, `make_diff`, `compute_visual_diff`, `slugify`)
- Backend routes are split by resource; `utils.py` and `diff_engine.py` are separated by concern
- Frontend is broken into focused, single-purpose components
- Error handling is consistent on both client and server

---

## In Progress

### Visually Pleasing & Easy to Navigate — 50 pts

`styles.css` has a working design system (CSS variables, layout classes, component styles). The app has routing, modals, a diff viewer, branch picker, and commit sidebar. Still room for polish.

---

### Three Distinct Features — 150 pts

Features implemented so far:
1. **Custom diff engine** (`diff_engine.py`) — Myers diff algorithm written from scratch
2. **Visual branch diff viewer** — word-level diff with `?w=1` whitespace toggle
3. **Commit history sidebar** — `CommitHistorySidebar.jsx` shows per-branch history
4. **Rich text editor** — `RichEditor.jsx` (TipTap-based WYSIWYG)
5. **Merge with conflict detection** — `merge.py` detects divergence since branch point

We likely satisfy the "three distinct features" requirement already. The goal is to make sure each one is clearly demonstrable during the final presentation.

---

### README File — 50 pts

Currently covers project description, user stories, and milestones. Still missing:
- Local setup instructions (`pip install`, `flask run`, `npm run dev`)
- Environment variable documentation (`.env.example` exists in `Frank/` but is not referenced)
- Architecture diagrams

---

### 2+ Automated End-to-End Tests — 100 pts

Current test files are unit/component tests and do not satisfy the E2E requirement:
- `Frank/test_diff_engine.py` — backend unit tests
- `client/src/test/api.test.js` — mocked API unit tests
- `client/src/test/DocumentDashboard.test.jsx` — component tests with mocked API
- `client/src/test/NewDocumentForm.test.jsx` — component tests with mocked API

The course requires Playwright. We need at least 2 tests that boot the real app and drive a browser through a complete user flow. Suggested flows:
- Create a document and verify it appears on the dashboard
- Open a document, create a branch, write content, commit, and view the diff

Reference: https://tobiasduerschmid.github.io/SEBook/tools/playwright-tutorial

---

## Not Started

### Authentication — 50 pts

The `User` model exists in `models.py` with `email` and `hashed_password` columns, but nothing is wired up. Still needed:
- Login and register routes
- JWT or session-based token handling
- Route protection on the backend
- Auth UI on the frontend

---

### Search — 50 pts

No search functionality exists. The simplest path is a title search bar on `DocumentDashboard` backed by a `?q=` filter on `GET /api/documents`.

---

### Architecture Diagrams (2+) in README — 100 pts

The README has no diagrams. We need at least two different diagram types, consistent with the codebase. Options:
- ERD (`User`, `Document`, `Branch`, `Commit`)
- System architecture (React → Flask API → SQLite)
- Sequence diagram (create doc → branch → commit → diff → merge)
- Frontend component tree

---

## Summary

| Rubric Item | Points | Status |
|---|---|---|
| Dynamic data display | 50 | Done |
| Upload data to back-end | 50 | Done |
| Git version control | 100 | Done |
| Code readability | 100 | Done |
| Visually pleasing | 50 | In progress |
| Three distinct features | 150 | In progress |
| README (run instructions + diagrams) | 50 | In progress |
| 2+ Playwright E2E tests | 100 | Not started |
| Authentication | 50 | Not started |
| Search | 50 | Not started |
| Architecture diagrams (2+) in README | 100 | Not started |
| **Total** | **850** | |

---

## Action Items

1. Set up Playwright and write at least 2 E2E tests
2. Implement authentication (login/register + protected routes)
3. Add document title search to the dashboard
4. Add architecture diagrams to the README
5. Complete README with local setup instructions
