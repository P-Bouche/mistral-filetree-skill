#!/usr/bin/env python3
"""filetree_selfonly.py — self-only mode: keep every filetree artifact out of git.

Corporate repos often reject tool artifacts in the official tree. Self-only mode
hides the manifest, hash sidecar, config, state file, and CLAUDE.local.md via
.git/info/exclude — git's per-clone, never-committed ignore channel — leaving the
tracked .gitignore and the team's CLAUDE.md / AGENTS.md untouched.

Design:
- `enable` is idempotent: it appends only missing exclude lines and unions them
  into the state file, so repeated runs repair rather than duplicate or forget.
- `enable` refuses when an artifact is already git-tracked: info/exclude has no
  effect on tracked files, so proceeding would silently hide nothing.
- `uninstall` reverses exactly the recorded lines (a Memento in
  .filetree.local.json), preserving the user's own lines, comments and order.
- Separate module and CLI entry (precedent: hooks/commit_guard.py): filetree.py
  sits at the 700-line ceiling and self-only is a standalone lifecycle concern.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from filetree import _atomic_write_text, require_git
from filetree_config import CONFIG_PATH, hash_path_for, load_config

STATE_PATH = Path('.filetree.local.json')

# Heading comment written above our block in info/exclude; recorded in state and
# removed with the block, so users can tell where the lines came from meanwhile.
EXCLUDE_COMMENT = '# filetree self-only artifacts (managed by /filetree:init --self-only)'

# Self-only wiring target. Claude Code auto-loads CLAUDE.local.md; upstream marks
# it deprecated in favor of `@~/...` imports but it remains functional, and it is
# the only auto-loaded project location that never touches the tracked CLAUDE.md.
LOCAL_WIRE_FILE = 'CLAUDE.local.md'


@dataclass
class State:
    """Memento for uninstall — everything enable changed besides the config flag.

    exclude_lines: lines this tool appended to info/exclude (removed verbatim).
    created_config: enable created .filetree.json itself; uninstall then deletes
    the file instead of leaving a husk that only ever held self_only.
    """
    exclude_lines: list[str] = field(default_factory=list)
    created_config: bool = False


def load_state() -> State:
    """Read .filetree.local.json; an absent file means nothing recorded yet.

    Strict like load_config: a malformed state file fails loudly instead of being
    treated as empty — silently forgetting recorded lines would break uninstall.
    """
    if not STATE_PATH.exists():
        return State()
    try:
        raw = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        sys.exit(f"Error: {STATE_PATH} is not valid JSON: {e}")
    if not isinstance(raw, dict):
        sys.exit(f"Error: {STATE_PATH} must be a JSON object, got {type(raw).__name__}")
    lines = raw.get('exclude_lines', [])
    if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
        sys.exit(f"Error: {STATE_PATH} `exclude_lines` must be a list of strings")
    created = raw.get('created_config', False)
    if not isinstance(created, bool):
        sys.exit(f"Error: {STATE_PATH} `created_config` must be a boolean")
    return State(exclude_lines=lines, created_config=created)


def save_state(state: State) -> None:
    """Persist state atomically (tmp + replace), like every other write here."""
    payload = {'exclude_lines': state.exclude_lines, 'created_config': state.created_config}
    _atomic_write_text(STATE_PATH, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def artifact_paths(config) -> list[str]:
    """Every path self-only must hide, in the order they land in info/exclude.

    Deliberately NOT here: CLAUDE.md / AGENTS.md — they are team files; self-only
    neither edits nor hides them (excluding a tracked path is a no-op anyway).
    """
    return [
        config.manifest_path,
        hash_path_for(config.manifest_path),
        CONFIG_PATH.as_posix(),
        STATE_PATH.as_posix(),
        LOCAL_WIRE_FILE,
    ]


def _exclude_file() -> Path:
    """info/exclude located by git itself.

    Never hardcode .git/info/exclude: in a linked worktree or submodule `.git` is
    a FILE, and info/ lives in the shared common dir. `--git-path` resolves both
    (so in a worktree the exclusions apply clone-wide, matching git semantics).
    """
    out = subprocess.check_output(
        ['git', 'rev-parse', '--git-path', 'info/exclude'], encoding='utf-8',
    ).strip()
    return Path(out)


def _tracked(paths: list[str]) -> list[str]:
    """Subset of paths git already tracks (info/exclude has no effect on those)."""
    tracked = set(subprocess.check_output(
        ['git', '-c', 'core.quotePath=false', 'ls-files', '-z'], encoding='utf-8',
    ).split('\0'))
    return [p for p in paths if p in tracked]


def cmd_enable() -> dict:
    """Hide filetree artifacts from git and flip config to self_only: true."""
    require_git()
    config = load_config()
    paths = artifact_paths(config)

    tracked = _tracked(paths)
    if tracked:
        sys.exit(
            "Error: cannot enable self-only mode — these paths are already tracked "
            f"by git, so .git/info/exclude cannot hide them: {', '.join(tracked)}.\n"
            f"       If they are yours to untrack: git rm --cached {' '.join(tracked)}"
        )

    exclude_file = _exclude_file()
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    original = exclude_file.read_text(encoding='utf-8') if exclude_file.exists() else ''
    existing = set(original.splitlines())
    to_add = [line for line in [EXCLUDE_COMMENT] + paths if line not in existing]
    if to_add:
        # Append-only: every pre-existing byte survives; just ensure we start on
        # a fresh line when the file lacks a trailing newline.
        text = original if not original or original.endswith('\n') else original + '\n'
        _atomic_write_text(exclude_file, text + '\n'.join(to_add) + '\n')

    # Decide BEFORE the write below creates the file.
    created_config = not CONFIG_PATH.exists()
    raw = {} if created_config else json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    raw['self_only'] = True
    _atomic_write_text(CONFIG_PATH, json.dumps(raw, ensure_ascii=False, indent=2) + '\n')

    # Union, never overwrite: on a second enable all lines already exist, and
    # overwriting with that empty delta would make uninstall forget every line.
    state = load_state()
    state.exclude_lines += [line for line in to_add if line not in state.exclude_lines]
    state.created_config = state.created_config or created_config
    save_state(state)

    return {
        'self_only': True,
        'exclude_file': exclude_file.as_posix(),
        'excluded_paths': paths,
        'exclude_lines_added': to_add,
    }


def cmd_uninstall() -> dict:
    """Reverse enable — recorded exclude lines, config flag, state file. Nothing else."""
    require_git()
    config = load_config()
    state = load_state()
    # Proceed if EITHER side shows self-only residue: flag set, or lines recorded
    # (a crash between enable's writes can leave one without the other).
    if not config.self_only and not state.exclude_lines:
        return {'self_only': False, 'changed': False}

    exclude_file = _exclude_file()
    removed = 0
    if exclude_file.exists() and state.exclude_lines:
        lines = exclude_file.read_text(encoding='utf-8').splitlines()
        targets = set(state.exclude_lines)
        remaining = [line for line in lines if line not in targets]
        removed = len(lines) - len(remaining)
        # Everything not ours survives verbatim — order, blanks, comments.
        _atomic_write_text(exclude_file, ('\n'.join(remaining) + '\n') if remaining else '')

    if state.created_config:
        # Enable created the config purely to hold self_only; remove the husk.
        CONFIG_PATH.unlink(missing_ok=True)
    elif CONFIG_PATH.exists():
        raw = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        raw.pop('self_only', None)
        _atomic_write_text(CONFIG_PATH, json.dumps(raw, ensure_ascii=False, indent=2) + '\n')

    STATE_PATH.unlink(missing_ok=True)

    # Artifacts still on disk are now VISIBLE to git; report them so the user
    # decides what to delete — uninstall never destroys generated work.
    leftovers = [p for p in artifact_paths(config) if Path(p).exists()]
    return {
        'self_only': False,
        'changed': True,
        'exclude_lines_removed': removed,
        'leftover_paths': leftovers,
    }


def main():
    parser = argparse.ArgumentParser(description='filetree self-only mode lifecycle')
    parser.add_argument('command', choices=['enable', 'uninstall'])
    args = parser.parse_args()
    result = cmd_enable() if args.command == 'enable' else cmd_uninstall()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':  # pragma: no cover - CLI entry; tests call main() directly.
    main()
