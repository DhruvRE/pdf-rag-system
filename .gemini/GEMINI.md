# ~/.gemini/GEMINI.md — Global Rules

## Response style
- Be concise and direct. No filler, no restating the request back to me.
- When making changes, prefer small targeted diffs over rewriting whole files.
- If a task is ambiguous, make the most reasonable assumption and state it
  in one line — don't stop to ask unless it's genuinely blocking.

## Code style
- Follow the existing conventions in the file/repo over generic defaults.
- No magic numbers/strings — use named constants.
- Every function gets a docstring/comment only if it's non-obvious;
  don't comment the obvious.
- Never hardcode secrets, API keys, or credentials — use env vars.
- Prefer explicit error handling over silent failure.

## Workflow
- Before editing, check for a project-level AGENTS.md / .agent/rules/
  and follow those over anything here if they conflict.
- If the project has a shared context/state file (e.g. .agent/context.*),
  read it before starting work and update it after — don't re-derive
  state by re-scanning the whole repo.
- Don't run destructive commands (rm -rf, force-push, drop table, etc.)
  without flagging it first.

## Git
- Write commit messages as: short imperative summary line, blank line,
  then bullet points for the "why" if non-trivial.
- Don't commit generated/build artifacts unless the repo already does.

## Communication
- When you hit an error you can't resolve, show me the exact error and
  what you tried — don't just say "it didn't work."