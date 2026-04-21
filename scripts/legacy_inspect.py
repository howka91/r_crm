#!/usr/bin/env python3
"""Inspect the legacy r_crm Postgres database and dump its schema to a markdown report.

Why this exists
---------------
Before we write the real data migration in Phase 9, we need to know what's actually
in the old database: what tables exist, what columns they have, how many rows, and
how FK relationships map. The architecture doc describes the *intended* model, but
the actual legacy DB has drifted over years of hot-patches — we can only plan a
reliable migration once we've seen what's really there.

Usage
-----
Fill the LEGACY_POSTGRES_* vars in .env and run from the repo root:

    python scripts/legacy_inspect.py              # writes docs/legacy_schema.md
    python scripts/legacy_inspect.py --sample 3   # also include 3 sample rows per table

Requires only `psycopg[binary]` (already in backend/requirements/base.txt).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import psycopg
    from psycopg import sql
except ImportError:
    sys.exit("psycopg not installed. Run: pip install 'psycopg[binary]'")


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "legacy_schema.md"


@dataclass
class Column:
    name: str
    data_type: str
    is_nullable: bool
    default: str | None


@dataclass
class ForeignKey:
    column: str
    ref_table: str
    ref_column: str


@dataclass
class Table:
    schema: str
    name: str
    row_count: int
    columns: list[Column] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}" if self.schema != "public" else self.name


def load_env() -> dict[str, str]:
    """Read LEGACY_POSTGRES_* from a repo-root .env (minimal parser)."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip("'\"")
    return out


def connect() -> psycopg.Connection:
    env = {**load_env(), **os.environ}

    host = env.get("LEGACY_POSTGRES_HOST")
    if not host:
        sys.exit(
            "LEGACY_POSTGRES_HOST is not set. Fill legacy DB credentials in .env "
            "(see .env.example → LEGACY_POSTGRES_*)"
        )

    return psycopg.connect(
        host=host,
        port=int(env.get("LEGACY_POSTGRES_PORT", "5432")),
        dbname=env["LEGACY_POSTGRES_DB"],
        user=env["LEGACY_POSTGRES_USER"],
        password=env.get("LEGACY_POSTGRES_PASSWORD", ""),
        connect_timeout=10,
    )


def fetch_tables(conn: psycopg.Connection) -> list[Table]:
    """List user tables with row counts (approximate via pg_class.reltuples)."""
    query = """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            c.reltuples::bigint AS approx_rows
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND c.relname NOT LIKE 'pg_%'
        ORDER BY n.nspname, c.relname;
    """
    tables: list[Table] = []
    with conn.cursor() as cur:
        cur.execute(query)
        for schema_name, table_name, approx in cur.fetchall():
            tables.append(Table(schema=schema_name, name=table_name, row_count=approx))
    return tables


def fetch_exact_row_count(conn: psycopg.Connection, table: Table) -> int:
    """Precise COUNT(*) — slower, used only for small tables."""
    q = sql.SQL("SELECT count(*) FROM {}.{}").format(
        sql.Identifier(table.schema), sql.Identifier(table.name)
    )
    with conn.cursor() as cur:
        cur.execute(q)
        return cur.fetchone()[0]


def fetch_columns(conn: psycopg.Connection, table: Table) -> list[Column]:
    query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(query, (table.schema, table.name))
        return [
            Column(name=r[0], data_type=r[1], is_nullable=(r[2] == "YES"), default=r[3])
            for r in cur.fetchall()
        ]


def fetch_primary_key(conn: psycopg.Connection, table: Table) -> list[str]:
    query = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = %s
          AND tc.table_name = %s
        ORDER BY kcu.ordinal_position;
    """
    with conn.cursor() as cur:
        cur.execute(query, (table.schema, table.name))
        return [r[0] for r in cur.fetchall()]


def fetch_foreign_keys(conn: psycopg.Connection, table: Table) -> list[ForeignKey]:
    query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = %s
          AND tc.table_name = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (table.schema, table.name))
        return [
            ForeignKey(column=r[0], ref_table=r[1], ref_column=r[2])
            for r in cur.fetchall()
        ]


def sample_rows(conn: psycopg.Connection, table: Table, limit: int) -> list[tuple]:
    q = sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
        sql.Identifier(table.schema), sql.Identifier(table.name)
    )
    with conn.cursor() as cur:
        cur.execute(q, (limit,))
        return cur.fetchall()


def render(tables: list[Table], sample: int, samples_map: dict[str, list[tuple]]) -> str:
    lines: list[str] = []
    lines.append("# Legacy schema report\n")
    lines.append(
        "Auto-generated by `scripts/legacy_inspect.py`. Used to plan the "
        "Phase 9 data migration. Do not edit by hand.\n"
    )

    # Summary
    total_tables = len(tables)
    total_rows = sum(t.row_count for t in tables)
    lines.append(f"**Total tables**: {total_tables}  ")
    lines.append(f"**Total rows (approx)**: {total_rows:,}\n")

    # Table of contents
    lines.append("## Tables\n")
    lines.append("| Table | Approx rows | Columns | FKs |")
    lines.append("|-------|------------:|--------:|----:|")
    for t in tables:
        lines.append(
            f"| [`{t.full_name}`](#{t.full_name.replace('.', '-')}) | "
            f"{t.row_count:,} | {len(t.columns)} | {len(t.foreign_keys)} |"
        )
    lines.append("")

    # Per-table details
    for t in tables:
        lines.append(f"## {t.full_name}\n")
        lines.append(f"Approx rows: **{t.row_count:,}**  ")
        if t.primary_key:
            lines.append(f"Primary key: `{', '.join(t.primary_key)}`\n")
        else:
            lines.append("*No primary key.*\n")

        lines.append("| Column | Type | Nullable | Default |")
        lines.append("|--------|------|---------:|---------|")
        for c in t.columns:
            default = f"`{c.default}`" if c.default else ""
            lines.append(
                f"| `{c.name}` | `{c.data_type}` | "
                f"{'yes' if c.is_nullable else 'no'} | {default} |"
            )
        lines.append("")

        if t.foreign_keys:
            lines.append("**Foreign keys:**\n")
            for fk in t.foreign_keys:
                lines.append(f"- `{fk.column}` → `{fk.ref_table}.{fk.ref_column}`")
            lines.append("")

        if sample > 0 and samples_map.get(t.full_name):
            lines.append(f"**Sample rows (first {sample}):**\n")
            lines.append("```")
            for row in samples_map[t.full_name]:
                lines.append(repr(row))
            lines.append("```\n")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Include N sample rows per table (default: 0)",
    )
    parser.add_argument(
        "--exact-count",
        action="store_true",
        help="Use SELECT count(*) for precise row counts (slow on big tables)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"Output file (default: {OUTPUT.relative_to(REPO_ROOT)})",
    )
    args = parser.parse_args()

    print(f"Connecting to legacy DB…")
    conn = connect()
    print("Connected. Enumerating tables…")

    tables = fetch_tables(conn)
    print(f"Found {len(tables)} tables. Fetching columns + FKs…")

    samples_map: dict[str, list[tuple]] = {}
    for t in tables:
        t.columns = fetch_columns(conn, t)
        t.primary_key = fetch_primary_key(conn, t)
        t.foreign_keys = fetch_foreign_keys(conn, t)
        if args.exact_count and t.row_count < 1_000_000:
            t.row_count = fetch_exact_row_count(conn, t)
        if args.sample > 0:
            try:
                samples_map[t.full_name] = sample_rows(conn, t, args.sample)
            except Exception as e:
                samples_map[t.full_name] = [(f"<error: {e}>",)]

    conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(tables, args.sample, samples_map), encoding="utf-8")
    print(f"Wrote {args.output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
