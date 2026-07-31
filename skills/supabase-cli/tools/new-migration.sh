#!/usr/bin/env bash
# Create a new Supabase migration and print its path so you can open it.
# Usage: ./new-migration.sh <snake_case_name>
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <snake_case_name>" >&2
  exit 1
fi

name="$1"

# Create the migration file via the CLI (writes to supabase/migrations/<ts>_<name>.sql).
supabase migration new "$name"

# Find and report the newest migration file matching the name.
newest="$(ls -1t supabase/migrations/*_"$name".sql 2>/dev/null | head -n1 || true)"
if [[ -n "$newest" ]]; then
  echo "Created: $newest"
  echo "Edit it, then run: supabase migration up   (local)   or   supabase db push   (remote)"
else
  echo "Migration created under supabase/migrations/ — check the CLI output above." >&2
fi
