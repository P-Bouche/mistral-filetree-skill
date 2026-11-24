---
description: Uninstall filetree from this repo — un-wires CLAUDE.md/AGENTS.md, removes generated artifacts (confirmed per item), tears down self-only mode if enabled.
allowed-tools: Read, Edit, Write, Bash(python3:*), AskUserQuestion
---

Remove filetree from the current repository. Nothing is deleted without explicit confirmation, and nothing is committed — the user reviews `git status` and commits.

## Steps

1. **Resolve state.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/filetree/scripts/filetree.py" wire-target
   ```
   Keep this snapshot: `manifest_path`, `manifest_exists`, `self_only`, and per wire file `{exists, real_path, wired, matches}`. All later steps read from it — never re-parse `.filetree.json` yourself.

2. **Self-only teardown — only when the snapshot shows `self_only: true`.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/filetree/scripts/filetree_selfonly.py" uninstall
   ```
   It removes exactly the `.git/info/exclude` lines it added (the user's own lines, comments and order survive byte-for-byte), clears `self_only` from `.filetree.json` (deleting that file only if enable created it), and deletes `.filetree.local.json`. It never deletes generated files — its `leftover_paths` feed step 4's deletion list.

3. **Un-wire.** For each wire file in the snapshot with `wired: true` (normal mode: `CLAUDE.md` / `AGENTS.md`; self-only: `CLAUDE.local.md`):

   a. Read `real_path` (never the symlink name) and locate the wire section: the `## <manifest_path>` heading through the line before the next same-or-higher-level `#` heading, or end of file.
   b. Confirm via `AskUserQuestion` with the exact span shown (question body or `preview`). On decline, skip — do not retry.
   c. `Edit` the section out of `real_path`. Leave any manifest mentions OUTSIDE the section untouched (`matches` may list user-authored references — not yours to remove).
   d. Self-only special case: if after removal `CLAUDE.local.md` would be empty (init created it to hold only the section), propose deleting the whole file in step 4 instead of editing it here.

4. **Delete generated artifacts — explicit list, one confirmation.** Candidates: the manifest, its hash sidecar (`<manifest>.hash.json` next to it), `.filetree.json`, plus step 2's `leftover_paths` if it ran. List only files that exist. Ask once via `AskUserQuestion` (multiSelect — the user picks which to delete); then delete each confirmed file:
   ```bash
   python3 -c "import os; os.remove('FILETREE.md')"
   ```
   Warn in the question that git-tracked files will show up as deletions to review and commit.

5. **Report.** Per wire file: un-wired / declined / not wired. Files deleted vs kept. If anything was git-tracked, remind the user to review `git status` and commit the removal themselves. Mention `/filetree:init` to reinstall later.

## Do not

- Commit.
- Delete anything outside the confirmed list; never remove directories.
- Touch manifest mentions outside the wire section.
- Call any LLM summaries or load the filetree SKILL.md — no shared rules apply here.
- Skip step 2 when `self_only: true` — deleting artifacts while their exclude lines linger leaves the user's exclude file dirty.
