# Snowflake vs PostgreSQL: Architectural Differences

This document compares the two database platforms used in this project, focusing on the architectural differences that affect how the same star schema behaves in each.

## Storage and Compute

**PostgreSQL** couples storage and compute on a single server. The database engine, query planner, and data files all share the same machine's CPU, memory, and disk. Scaling up means upgrading the server; scaling out requires read replicas or partitioning.

**Snowflake** separates storage and compute entirely. Data is stored in a centralized cloud object store (S3, GCS, or Azure Blob), while compute runs on independent **virtual warehouses** — clusters of nodes that spin up on demand and shut down when idle. This means:
- You can scale compute without touching storage (and vice versa).
- Multiple warehouses can query the same data simultaneously without contention.
- You pay for storage and compute independently. A warehouse that's suspended costs nothing.

For this project the difference is academic (our dataset is small), but it's the key architectural distinction that makes Snowflake attractive for large-scale analytics.

## Indexing vs Micro-Partitioning

**PostgreSQL** uses B-tree indexes to speed up queries. Our schema defines 7 explicit indexes on columns like `game_date`, `player_id`, and `team_abbrev`. These must be manually created, consume disk space, and add overhead to writes.

**Snowflake** has no user-created indexes. Instead it uses:
- **Micro-partitioning**: Data is automatically divided into immutable, compressed storage units (50–500 MB each) based on insertion order.
- **Partition pruning**: The query engine maintains min/max metadata for each micro-partition. When a query filters on a column, Snowflake skips partitions that can't contain matching rows — no index needed.
- **Clustering keys** (optional): For very large tables, you can define clustering keys to reorganize data for better pruning. Our dataset doesn't need this.

The practical impact: the 7 indexes in `schema.sql` have no equivalent in `snowflake_schema.sql`. Snowflake handles it automatically.

## Data Types

| PostgreSQL | Snowflake | Notes |
|-----------|-----------|-------|
| `TEXT` | `VARCHAR` | Functionally identical in Snowflake, but VARCHAR is conventional |
| `REAL` | `FLOAT` | Both are IEEE 754 floating point |
| `SERIAL` | `INTEGER AUTOINCREMENT` | Snowflake's equivalent of auto-incrementing integers |
| `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP()` | Snowflake requires parentheses on the function call |

## Referential Integrity

**PostgreSQL** enforces foreign key constraints. If you try to insert a `dim_player` row with a `team_abbrev` that doesn't exist in `dim_team`, the insert fails. This protects data integrity at the database level.

**Snowflake** supports foreign key syntax but **does not enforce it**. Foreign keys exist as metadata only — the query optimizer can use them as hints for join elimination, but nothing prevents orphaned references. Data integrity must be enforced in the ETL pipeline or through validation queries.

Both schemas declare the same foreign keys, but they serve different purposes: enforcement in PostgreSQL, documentation and optimization hints in Snowflake.

## Idempotent Inserts

**PostgreSQL** uses `INSERT ... ON CONFLICT DO NOTHING` for idempotent seed data (see `seed.sql`).

**Snowflake** doesn't support `ON CONFLICT`. Instead we use `MERGE` statements (see `snowflake_seed.sql`), which match source rows against the target table and only insert when no match is found. Same result, different syntax.

## Warehouses and Cost

Snowflake's compute model uses virtual warehouses sized from XS to 6XL. Key concepts:
- **Warehouse = compute cluster.** Queries run on a warehouse, not on the database itself.
- **Auto-suspend**: Warehouses suspend after a configurable idle period (default 10 minutes). Suspended warehouses cost nothing.
- **Auto-resume**: A query sent to a suspended warehouse automatically resumes it.
- **Credit-based billing**: You pay per-second for active warehouse time. An X-Small warehouse costs 1 credit/hour.

For this project, the default `COMPUTE_WH` (X-Small) on a free trial is more than sufficient.

## Stages

Snowflake introduces the concept of **stages** — intermediate storage locations for loading data. Data flows: source → stage → table (via `COPY INTO`).

- **Internal stages**: Managed by Snowflake. You upload files to a stage, then load them into tables.
- **External stages**: Point to your own S3/GCS/Azure bucket.

This is relevant for bulk loading. Our current pipeline uses `DataFrame.to_sql()` via SQLAlchemy for PostgreSQL. A Snowflake integration would use the Snowflake Python connector's `write_pandas()` or stage-based `COPY INTO` for better performance at scale.

## Semi-Structured Data

Snowflake natively supports `VARIANT`, `OBJECT`, and `ARRAY` types for storing JSON, Avro, and Parquet data directly in tables. PostgreSQL has `JSONB` but Snowflake's semi-structured support is more deeply integrated with the query engine — you can query nested JSON with dot notation and automatic type casting.

This could be useful in the future for storing raw NHL API responses alongside the structured star schema, but isn't used in the current design.

## Running the Snowflake Schema

```sql
-- In Snowflake worksheet or SnowSQL:
-- 1. Run the schema
!source sql/snowflake_schema.sql
-- Or paste the contents of sql/snowflake_schema.sql

-- 2. Run the seed data
!source sql/snowflake_seed.sql
-- Or paste the contents of sql/snowflake_seed.sql

-- 3. Verify
SELECT COUNT(*) FROM dim_team;      -- Should return 32
SELECT COUNT(*) FROM dim_season;    -- Should return 1
```

Or using SnowSQL CLI:
```bash
snowsql -a RAXFPCE-GQB21566 -u bobloblaw -f sql/snowflake_schema.sql
snowsql -a RAXFPCE-GQB21566 -u bobloblaw -f sql/snowflake_seed.sql
```
