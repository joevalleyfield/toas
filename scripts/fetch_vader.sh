#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST_DIR="$ROOT_DIR/tests/vendor/vader.vim"
TMP_DIR="$ROOT_DIR/tests/vendor/.vader.vim.tmp"
REPO_URL=${VADER_REPO_URL:-https://github.com/junegunn/vader.vim.git}
REF=${VADER_REF:-master}

mkdir -p "$ROOT_DIR/tests/vendor"
rm -rf "$TMP_DIR"

git clone --depth 1 --branch "$REF" "$REPO_URL" "$TMP_DIR"
rm -rf "$DEST_DIR"
mv "$TMP_DIR" "$DEST_DIR"

printf 'Installed vader.vim to %s\n' "$DEST_DIR"
