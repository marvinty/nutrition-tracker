#!/usr/bin/env bash
# PreToolUse guard: refuse any tool call that touches .env or .env.*
#
# .env holds live credentials against the production deployment (RESEND_API_KEY,
# HETZNER_CLOUD_API_TOKEN, ANTHROPIC/OPENAI keys). .gitignore keeps them out of the
# repo but does nothing about the transcript — a single `awk -F= '...' .env` copies a
# secret into conversation history, where it is out of reach of any later cleanup.
#
# .env.example is the documented, secret-free template and stays fully readable.
#
# Covers file_path (Read/Edit/Write), command (Bash) and pattern/path (Grep), since
# each is a different route to the same bytes.
set -uo pipefail

payload=$(cat)
target=$(printf '%s' "$payload" | jq -r '
  [ .tool_input.file_path // ""
  , .tool_input.command   // ""
  , .tool_input.pattern   // ""
  , .tool_input.path      // ""
  ] | join(" ")
' 2>/dev/null) || exit 0

# Remove the allowed name first, so what is left is only ever a real secret file.
stripped=${target//.env.example/}

# Match `.env` and `.env.<anything>` only as a standalone path component: a leading
# char that is not part of a filename (start, space, quote, slash) and a trailing char
# that is not a name character. Keeps `settings.env` or `foo.environment` from tripping it.
if printf '%s' "$stripped" | grep -Eq '(^|[^A-Za-z0-9_.-])\.env([^A-Za-z0-9_-]|$)'; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked by .claude/hooks/block-env-access.sh: .env and .env.* hold live production secrets, and reading them copies the value into the transcript permanently. .env.example is allowed and documents every key. If you need a real value, ask Marvin to check it."}}
JSON
fi

exit 0
