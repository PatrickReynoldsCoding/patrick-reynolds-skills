---
name: review-code-diagram
description: Draw a code flow as an Excalidraw sequence diagram where every box and arrow links to the exact code line and opens it in IntelliJ (idea://). Saves to $CODE_DIAGRAM_ROOT/<repo>/<flow>.excalidraw (default ~/diagrams) so the user can open, move, fix and add nodes, and Claude can read and update it later. Use on /review-code-diagram, when the user says yes to a diagram after a flow explanation, or when asked to draw, diagram or update a diagram of a code flow.
argument-hint: "[flow to draw | path to an existing .excalidraw to update]"
---

# Code diagram

**Goal:** The user sees a code flow as a sequence diagram. They click any box or arrow, and IntelliJ opens at that line. They can move, fix and add nodes themselves. Claude can read and update the same file.

## Where files go
- `$CODE_DIAGRAM_ROOT/<repo>/<flow-name>.excalidraw` (default root `~/diagrams`; kebab-case flow name). Make the folder if it is missing.
- If the flow crosses repos, use the repo where the flow starts.

## How the user opens a diagram: always give the one-click link
- A local server (`<skill dir>/server/server.py`, port 7878; `<skill dir>` is the folder holding this SKILL.md) runs inside `~/Applications/Code Diagram Server.app` (built by `<skill dir>/server/build-app.sh`, which records the path of `server.py` at build time, so rebuild it if the skill moves; the app exists so only it, not all of Python, gets macOS access to the diagrams folder). Start the app at login if you want it always up (for example, add it to Login Items); the app restarts the server if it stops.
- "macOS blocked access" error: the app lost its Full Disk Access (e.g. after a rebuild). The user must re-add it in System Settings → Privacy & Security → Full Disk Access.
- **Every time you mention a diagram, give the link** `http://diagrams.localhost:7878/?file=<repo>/<flow>.excalidraw` (path relative to the diagrams folder, URL-encode spaces). List of all diagrams: `http://diagrams.localhost:7878/`.
- The page auto-saves every edit to the file. It also picks up your edits to the file within 2 seconds, so you don't need to ask the user to reload.
- It also opens code in IntelliJ from an http link: `http://diagrams.localhost:7878/open<absolute path>:<line>` opens `idea://open?file=…&line=…` itself and shows an "Opened in IntelliJ" page (only for files under `~/repos`). Use it where `idea://` links break, e.g. VS Code's markdown preview, which percent-encodes the `idea://` query.
- Check it is up: `curl -s -o /dev/null -w '%{http_code}' http://diagrams.localhost:7878/` → `200`. If not: `open -g -a 'Code Diagram Server'`. To restart after a code change: `pkill -f review-code-diagram/server/server.py` (use the path the app was built with) (the app starts it again in 5 s); log in `~/Library/Logs/code-diagram.log`.
- Fallback: open the file at excalidraw.com in Chrome (Open, then Save). idea:// links work there too.

## Make a new diagram
1. **Find the flow in the code.** Read the real code. Get the exact file and line for every participant and every call. Never guess a line number. Use the local checkout path (`/Users/<you>/...`, never `~`).
2. **Write a spec** (JSON) in the scratchpad:
   ```json
   {"title": "<repo>: <flow name>",
    "participants": [{"id": "api", "label": "SearchController", "file": "/Users/<you>/repos/.../SearchController.scala", "line": 40}],
    "messages": [{"from": "api", "to": "agent", "label": "search(query)", "file": "/abs/path/File.scala", "line": 88},
                 {"from": "agent", "to": "api", "label": "SearchResult", "return": true, "file": "...", "line": 120}]}
   ```
   - **Participants:** a class, object, service or external system, in left-to-right call order. Link to its definition line.
   - **Messages:** one per step, in run order. Link to the **call site** line (where the call happens), not the definition. Use `"return": true` for a reply (dashed arrow). `from` = `to` draws a self-call loop.
   - Keep labels short: method name and the main argument. 5–15 messages is a good size. Split big flows into more diagrams.
   - External systems (a database, a message queue, an LLM, an MCP server) have no `file`. Link them to the client code that calls them.
3. **Run:** `python3 <skill dir>/scripts/seq2excalidraw.py <spec.json> "${CODE_DIAGRAM_ROOT:-$HOME/diagrams}/<repo>/<flow>.excalidraw"`
4. **Tell the user** (in the shared writing style, `${CLAUDE_PLUGIN_ROOT}/writing-styles/plain.md`; the plugin root is 2 folders above this skill's folder) the one-click `http://diagrams.localhost:7878/?file=...` link and the full file path, and give the flow as a short numbered list with the same step numbers and IntelliJ links, so text and diagram match.

## Update an existing diagram
- **Always read the file first.** The user may have moved, added, deleted or relabelled shapes. Their changes win.
- **Never re-run the script on a file the user may have edited.** It overwrites their changes. Edit the JSON in place:
  - Change a `link`, `text`/`originalText`, or position (`x`, `y`).
  - Add a step: copy an existing arrow and its text element, give new unique `id`s, set `containerId`/`boundElements` to point at each other, and move the steps below it down by 70.
  - Keep `type`, `version`, `elements`, `appState`, `files` at the top level.
- Shapes the user added by hand may have no `link`. Ask if they want links added.

## Link only to a checkout that IntelliJ has imported
`idea://` opens the file in the IntelliJ project that owns it. If no open project owns it, IntelliJ opens it in whatever window is in front, as a loose file: no code navigation, and Find Usages says "No usages found". So:
- Link to a checkout that has a `.idea` folder (an imported sbt project), e.g. `~/repos/<repo>`. Check with `test -d <checkout>/.idea`.
- Do not link to throwaway worktrees unless they have `.idea`.
- If the code you need is only in a non-imported checkout, tell the user before you draw, and ask if they want to import it in IntelliJ.

## Link format
`idea://open?file=<URL-encoded absolute path>&line=<n>`. Put it on the box, the arrow **and** the arrow's text element, so a click anywhere works.
