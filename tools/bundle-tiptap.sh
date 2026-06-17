#!/usr/bin/env bash
# One-shot script to vendor the TipTap ESM bundle.
# Run this when you want to update the vendored tip-edit.js.
# Requires: node >=18, npm, npx (esbuild)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="NossiSite/static/lib/tiptap/tip-edit.js"
DIR=$(mktemp -d)
VERSION_FILE="$REPO_ROOT/tools/.tiptap-versions"
trap 'rm -rf "$DIR"' EXIT

cd "$DIR"
npm init -y > /dev/null

# Pin to specific versions for reproducible builds.
# Update these when you intentionally want newer packages.
TIPTAP_CORE="3.27.0"
TIPTAP_PM="3.27.0"
TIPTAP_STARTER_KIT="3.27.0"
TIPTAP_MARKDOWN="3.27.0"
TIPTAP_TASK_LIST="3.27.0"
TIPTAP_TASK_ITEM="3.27.0"

npm install \
  "@tiptap/core@${TIPTAP_CORE}" \
  "@tiptap/pm@${TIPTAP_PM}" \
  "@tiptap/starter-kit@${TIPTAP_STARTER_KIT}" \
  "@tiptap/markdown@${TIPTAP_MARKDOWN}" \
  "@tiptap/extension-task-list@${TIPTAP_TASK_LIST}" \
  "@tiptap/extension-task-item@${TIPTAP_TASK_ITEM}"

# Record resolved versions for audit
printf "# TipTap vendored bundle versions — %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$VERSION_FILE"
for pkg in core pm starter-kit markdown extension-task-list extension-task-item extension-strike; do
  dir="node_modules/@tiptap/$pkg"
  ver=$(jq -r '.version' "$dir/package.json" 2>/dev/null || echo "unknown")
  echo "@tiptap/$pkg=$ver" >> "$VERSION_FILE"
done

cat > entry.mjs << 'EOF'
export { Editor, Extension } from '@tiptap/core'
export { default as StarterKit } from '@tiptap/starter-kit'
export { Markdown } from '@tiptap/markdown'
export { TaskList } from '@tiptap/extension-task-list'
export { TaskItem } from '@tiptap/extension-task-item'
export { Strike } from '@tiptap/extension-strike'
export { Plugin } from '@tiptap/pm/state'
export { Decoration, DecorationSet } from '@tiptap/pm/view'
EOF

npx esbuild entry.mjs --bundle --format=esm --outfile=tip-edit.js

# Verify the bundle contains all expected exports
for symbol in Editor Extension Markdown StarterKit TaskList TaskItem Strike Plugin Decoration DecorationSet; do
  if ! grep -q "$symbol" tip-edit.js; then
    echo "ERROR: Missing export $symbol in bundle" >&2
    exit 1
  fi
done

cp tip-edit.js "$REPO_ROOT/$OUT"
echo "Wrote $REPO_ROOT/$OUT ($(wc -c < tip-edit.js) bytes)"
echo "Versions recorded in $VERSION_FILE"
