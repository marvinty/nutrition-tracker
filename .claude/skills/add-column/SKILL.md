---
name: add-column
description: Add a column to an existing table with a hand-written, idempotent SQLite migration in init_db.py
disable-model-invocation: true
---

# Add a column to an existing table

There is no Alembic in this project. `init_db()` runs `Base.metadata.create_all` plus a
list of hand-written migration functions on every boot. **`create_all` creates missing
tables, never missing columns** — so a column added only to the model appears on a fresh
database and is silently absent on the live one, which then fails at the first query
touching it.

Use this when adding a column (or an index, or a data backfill) to a table that already
exists in production. A brand-new *table* needs no migration: `create_all` handles it,
and the only requirement is the import in step 3.

## 1. Change the model

Models live in `app/models/`. `Base.__tablename__` is the lowercased class name —
`UserTokenTotal` → `usertokentotal`, `AiRequestLog` → `airequestlog`.

Two SQLite constraints decide what the column may look like:

- **`NOT NULL` needs a default** if the table already has rows. Either give it a
  `server_default`, or make it nullable and say why in a comment — as `User.email` does.
- **`UNIQUE` is not addable** via `ALTER TABLE`. Declare it on the model for fresh
  databases and add a separate unique index in the migration (step 2).

Use `server_default=` rather than `default=`: `create_all` writes it into the `CREATE
TABLE` DDL, so a fresh database and a migrated one end up with the same schema. The
literal here and the `DEFAULT` in the `ALTER TABLE` must match exactly, or the two
paths diverge.

## 2. Write the migration function in `app/db/init_db.py`

Follow the existing ones — `_add_user_tier_column` is the minimal case,
`_add_user_email_columns` the one with an index and a backfill.

```python
async def _add_<table>_<column>_column(conn) -> None:
    """One line on what this adds, then *why the backfill is what it is*.

    Say what happens to rows that already exist. That is the part a reader cannot
    reconstruct from the code.
    """
    columns = await conn.execute(text('PRAGMA table_info("<table>")'))
    if any(row[1] == "<column>" for row in columns):
        return
    await conn.execute(text('ALTER TABLE "<table>" ADD COLUMN <column> <TYPE>'))
```

Non-negotiables:

- **Guard on `PRAGMA table_info` first and return early.** This runs on every boot. It
  must be a no-op on a fresh database and on the 500th restart.
- **Quote the table name.** `"user"` is a SQL keyword; unquoted it is a syntax error.
- **One statement per `conn.execute`.** Adding two columns means two `ALTER`s.
- **`UNIQUE` → `CREATE UNIQUE INDEX IF NOT EXISTS ix_<table>_<column> ON "<table>" (<column>)`**
  after the `ALTER`. A unique index still permits many NULLs, which is usually what a
  column added to existing rows needs.
- **Backfill in its own `UPDATE`.** SQLite cannot add and populate in one statement.

For a pure data backfill with no schema change, guard on the data instead — see
`_backfill_token_totals`, which returns early if the target table has any row, so it
seeds once and never overwrites a live counter.

## 3. Register it

- Add the call to `init_db()`, at the end of the list — order is deploy order.
- A **new model file** also needs `from app.models.<mod> import <Class>  # noqa: F401 — must import to register with Base.metadata`
  at the top of `init_db.py`. Without it `create_all` never sees the table.

## 4. Think about the rows that already exist

This is where the real bug lives, and it is not visible on a fresh database.

The email migration is the cautionary tale: verification is enforced by comparing
`created_at` against a grace period, so every pre-existing account would have been past
its deadline the instant the code shipped — locked out of an app they were using a
minute earlier. The backfill marks them verified to grandfather them in.

Ask: with the default (or NULL) this migration gives them, what does the *application*
then do to those rows? If the answer is "something it would not do to a new row", the
backfill is the fix, not the column.

## 5. Test it

Add to `tests/test_init_db.py`, which imports the migration function directly and runs
it against an in-memory database. Cover both:

- the effect on rows that predate the column, and
- **that a second call is a no-op** — `test_backfill_is_a_noop_when_counter_already_populated`
  is the model for this. That test is what stops a restart from double-applying.

Test files set the dummy env vars before importing any `app` module:

```python
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
```

## 6. Verify against a database that has rows

```bash
python3 -m pytest tests/test_init_db.py -q
```

A green in-memory test only proves the fresh path. The migration exists for the other
one, so also run it against a database that predates the column:

```bash
docker compose up -d
docker compose logs --tail=30 api
```

`init_db()` runs at boot on the mounted `/data/macromic.db`, which has real rows. A
clean start plus a spot check of the affected page is the actual proof. Restarting a
second time is worth doing too — that is the idempotency check on live data.
