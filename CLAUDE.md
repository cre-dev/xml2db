# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install with dev dependencies
pip install -e .[tests,docs] duckdb_engine pytz

# Run all tests including DB integration tests (uses in-memory DuckDB)
TZ="Europe/Paris" DB_STRING="duckdb:///:memory:" python -m pytest

# Run only non-database tests (no DB_STRING needed)
pytest -m "not dbtest"

# Run a single test file or test by name
pytest tests/test_conversions.py
pytest -k "test_iterative_recursive_parsing"

# Run against a real database instead
DB_STRING="postgresql+psycopg2://user:pass@localhost/testdb" pytest

# Serve documentation locally
mkdocs serve
```

## Architecture

`xml2db` maps an XSD schema to a relational database schema and loads XML files into it. The top-level flow is:

1. **`DataModel`** (`model.py`) reads an XSD file using `xmlschema` + `lxml`, traverses the schema tree, and builds a set of `DataModelTable` objects — one per XSD `complexType`. It then creates SQLAlchemy tables from those objects.
2. **`DataModel.parse_xml()`** returns a **`Document`** (`document.py`), which holds the parsed flat data ready for insertion.
3. **`XMLConverter`** (`xml_converter.py`) does the actual XML traversal, producing a nested "document tree" dict. Two strategies exist: iterative (`iterparse=True`) and recursive — tests assert they produce identical output.
4. **`Document.insert_into_target_tables()`** inserts the flat data into the database. **`Document.to_xml()`** converts it back.

### Table hierarchy (`table/`)

Each XSD `complexType` becomes one of two concrete table classes:

- **`DataModelTableReused`** — deduplicates identical subtrees via a SHA-256 hash column (`xml2db_record_hash`). This is the default. Relationships between a reused child and multiple parents require an intermediate join table (`DataModelRelationN` + `DataModelTransformedTable`).
- **`DataModelTableDuplicated`** — stores rows without deduplication; parent FK lives directly in the child row. Set `"reuse": False` in `model_config` to use this per table.

Relations are stored as `DataModelRelation1` (0..1 / 1..1) or `DataModelRelationN` (0..n / 1..n) in `DataModelTable.fields`.

### Dialect system (`dialect/`)

`DatabaseDialect` (base class) abstracts DB-specific behaviour: identifier length limits (truncated with MD5 suffix when too long), XSD→SQLAlchemy type mapping, and DDL generation. Each subclass (`postgresql.py`, `mysql.py`, `mssql.py`, `duckdb.py`) overrides only what differs. `get_dialect()` in `dialect/__init__.py` selects the right class from the SQLAlchemy engine dialect name.

### Snapshot tests for model outputs

`tests/test_models_output.py` compares generated ERDs, source/target trees, and SQL DDL against committed `.md`, `.txt`, and `.sql` files under `tests/sample_models/`. When a change intentionally modifies the data model or DDL output, regenerate these snapshots by running:

```bash
cd tests/sample_models && python models.py
```

then commit the updated snapshot files alongside the code change.

## Writing style

- After any code change, check whether docstrings, inline docs, or `docs/` pages need updating and update them as part of the same task.
- Write docstrings and documentation concisely and directly. No em-dashes or en-dashes; use commas, colons, or plain sentences instead.

### Key configuration options (`model_config`)

| Option | Effect |
|---|---|
| `tables.<name>.reuse` | `False` → `DataModelTableDuplicated` |
| `tables.<name>.choice_transform` | `False` → keep XSD `choice` fields separate instead of type+value columns |
| `tables.<name>.fields.<field>.transform` | `False` / `"elevate_wo_prefix"` etc. → override field-level simplification |
| `row_numbers` | Add ordering column tracking original XML element position |
| `metadata_columns` | Extra SQLAlchemy columns appended to the root table |
| `record_hash_column_name` / `record_hash_constructor` / `record_hash_size` | Customise the deduplication hash column |
| `as_columnstore` | MS SQL Server columnstore index on a table |
