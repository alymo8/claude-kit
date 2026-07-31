---
name: supabase-cli
description: Use when working with a Supabase project from the command line — local dev stack (start/stop), schema migrations, db push/pull/diff/reset, seeding, linking to a remote project, generating types, or Edge Functions. Reference for exact `supabase` CLI command syntax and the migration workflow.
---

# Supabase CLI

Reference for driving a Supabase project with the `supabase` CLI. Covers install, the
local development stack, and the migration-based schema workflow (local → remote).

## Install / update (Windows, this machine)

Installed via **Scoop** at `C:\Users\alymo\scoop\shims\supabase.exe` (on PATH).

```bash
supabase --version            # verify
scoop update supabase         # upgrade to latest
```

Fresh install elsewhere: `scoop bucket add supabase https://github.com/supabase/scoop-bucket.git && scoop install supabase`.
Global `npm install -g supabase` is **not supported** by Supabase — use Scoop, Homebrew, or a
project dev-dependency (`npm i -D supabase` then `npx supabase ...`).

The local stack (`supabase start`) requires **Docker Desktop running**.

## Core principle: migrations are the source of truth

Every schema change goes through a **migration file** in `supabase/migrations/`. Never edit the
remote database directly (SQL editor / Table Editor) once you're using migrations — it bypasses
migration history and makes `db push` fail with sync errors. Local Dashboard changes are fine
because you capture them with `db diff`.

## Quick reference

| Command | What it does |
|---|---|
| `supabase login` | Auth the CLI with a personal access token |
| `supabase init` | Create `supabase/` config in the current project |
| `supabase start` | Start the local stack (Postgres, Studio, etc.) via Docker |
| `supabase stop` | Stop the local stack (`--no-backup` to discard data) |
| `supabase status` | Show local stack URLs, keys, and ports |
| `supabase link` | Link this project to a remote Supabase project (interactive picker) |
| `supabase migration new <name>` | Create an empty timestamped migration file |
| `supabase migration up` | Apply pending migrations to the **local** db |
| `supabase migration list` | Show applied/pending status across local and remote |
| `supabase migration repair --status applied\|reverted <ts>` | Fix the tracking table only (no SQL run) |
| `supabase db reset` | Drop local db, re-run all migrations, then run `seed.sql` |
| `supabase db diff -f <name>` | Diff local schema changes into a new migration file |
| `supabase db pull` | Pull remote schema into a new migration file |
| `supabase db push` | Apply local migrations to the **remote** db |
| `supabase db push --include-seed` | Push migrations and seed the remote db |
| `supabase gen types typescript --local > types.ts` | Generate TS types from the local schema |
| `supabase functions new/serve/deploy <name>` | Edge Functions lifecycle |
| `supabase secrets set/list/unset` | Manage remote project secrets |

Run `supabase <command> --help` for full flag lists — don't guess flags.

## Migration workflow (write SQL yourself)

```bash
supabase migration new create_employees_table   # 1. create file in supabase/migrations/
#    -> edit supabase/migrations/<timestamp>_create_employees_table.sql, add DDL
supabase migration up                            # 2. apply to local db
```

Later change:

```bash
supabase migration new add_department_column
#    -> edit the new file: alter table public.employees add department text;
supabase migration up
```

## Diffing workflow (build in the Dashboard, capture as SQL)

Use only for changes made to the **local** Dashboard/db:

```bash
supabase db diff -f create_cities_table   # writes the diff into a new migration file
supabase db reset                         # verify it applies cleanly from scratch
```

## Seeding

Put repeatable seed data in `supabase/seed.sql`. It runs automatically on every `supabase db reset`.

## Deploy to remote

```bash
supabase login
supabase link                 # pick the remote project
supabase db push              # apply local migrations to remote
supabase db push --include-seed   # optional: also seed remote
```

## Team workflow

Golden rule: **never change the remote database directly.** All schema changes go through
migration files committed to git.

```bash
# each dev, on their branch
supabase migration new your_change_description
supabase db reset                       # test it applies
git add supabase/migrations && git commit -m "add migration: your_change_description"

# after pulling a teammate's merged migration
git pull
supabase db reset

# only ONE person runs this at a time (migrations apply in timestamp order)
supabase db push
```

## Diagnosing sync errors

`db push` failing and suggesting `migration repair`? Local files and the remote
`supabase_migrations.schema_migrations` tracking table have diverged.

1. `supabase migration list` — see where local vs remote differ.
2. Made changes on the remote directly? `supabase db pull` to capture remote state into a new
   migration file, commit it, then resume the normal workflow.
3. Tracking table wrong (schema already matches but history is off)?
   `supabase migration repair --status applied <ts>` (mark as applied without re-running), or
   `--status reverted <ts>` (mark as not-applied). Repair edits the tracking table only — it
   never runs or reverts SQL.

## Common mistakes

- **`migration up` vs `db push`** — `up` applies to the *local* db; `db push` applies to the
  *remote*. Don't confuse them.
- **`db reset` wipes local data** — it drops and rebuilds from migrations + `seed.sql`. Expected
  locally; never point it at anything but local.
- **Editing remote directly** — the #1 cause of sync errors. Always go through migration files.
- **`supabase start` hangs / errors** — Docker Desktop isn't running.
- **`migration repair` won't fix schema** — it only corrects the history table, not the actual
  schema. Use `db pull` to reconcile actual schema drift.

## Tools

- `tools/new-migration.sh` — create a migration and open it for editing in one step (bash).
