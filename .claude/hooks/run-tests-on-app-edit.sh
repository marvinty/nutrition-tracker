#!/usr/bin/env bash
# PostToolUse: run the test suite after an edit under app/, and speak up only if it broke.
#
# Runs async (see .claude/settings.json) so it never makes an edit wait ~20s. Exit 2 is
# the "wake the model" signal, so a green run is silent and a red one is not.
#
# The two --ignore'd modules need httpx over ASGITransport; httpx is a project dependency
# but is not installed in the local Python 3.9, so including them would turn every run
# into a collection error. They run in the container — see CLAUDE.md.
set -uo pipefail

payload=$(cat)
file=$(printf '%s' "$payload" | jq -r '.tool_response.filePath // .tool_input.file_path // ""' 2>/dev/null) || exit 0

# Only application code. Edits to tests, templates, docs or config are not worth 20s.
case "$file" in
  */app/*.py|app/*.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

output=$(python3 -m pytest -q \
  --ignore=tests/test_rate_limit_page.py \
  --ignore=tests/test_register_form.py 2>&1)

if [ $? -ne 0 ]; then
  printf 'Tests failed after editing %s:\n\n%s\n' "$file" "$(printf '%s' "$output" | tail -30)"
  exit 2
fi

exit 0
