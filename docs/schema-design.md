# Schema Design Decisions

## Why a Star Schema?

A star schema was chosen over a snowflake schema for several reasons:

- **Query simplicity.** Most analytics queries ask "how did player X perform in game Y?" or "what are team Z's stats over a date range?" A star schema answers these with straightforward joins between one fact table and a few dimensions — no multi-level dimension chains.
- **Read performance.** The primary workload is analytical reads (dashboards, rolling averages, player comparisons), not transactional writes. Star schemas minimize the number of joins needed for these queries.
- **Dimension tables are small.** There are ~32 teams, ~800 active players, and ~1,400 games per season. Denormalizing team info (division, conference) into `dim_team` instead of breaking it into `dim_division` → `dim_conference` wastes negligible storage and avoids unnecessary joins.
- **Snowflake normalization adds no value here.** A snowflake schema normalizes dimensions into sub-dimensions. Our dimensions are already flat — a team has a division and conference, a player has a position and handedness. There's nothing to further normalize.

## Fact Table Design

### Grain

Both fact tables are at the **player-game** grain: one row per player per game. This is the most granular level available from the NHL API boxscore endpoints and supports all planned analyses (per-game stats, rolling averages, season aggregations).

A coarser grain (player-season) was rejected because it loses game-level detail needed for rolling averages, hot/cold streak detection, and game-specific queries.

A finer grain (player-game-period or play-by-play) was considered out of scope for the initial build. The schema can be extended later with play-by-play fact tables if needed.

### `fact_game_skater_stats`

Stores per-game counting stats for skaters (forwards and defensemen). Key design choices:

- **TOI stored in seconds** (`toi_seconds`) rather than "MM:SS" strings. Integer arithmetic is simpler and faster than parsing time strings. The Python model provides a `toi_minutes` property for display.
- **Points stored explicitly** alongside goals and assists. This is technically redundant (points = goals + assists) but avoids recomputing it on every query, which is the most common stat accessed.
- **Faceoff percentage is nullable** because defensemen and wingers rarely take faceoffs. A NULL means "not applicable" rather than zero.
- **Composite primary key** on `(player_id, game_id)` enforces that a player can only have one stat line per game, providing natural idempotency for pipeline reruns.

### `fact_game_goalie_stats`

Stores per-game stats for goalies. Key design choices:

- **Decision is nullable** because only the starting or winning/losing goalie receives a decision (W/L/O). Relief goalies who enter mid-game may not get one.
- **Save percentage stored** (`save_pct`) alongside saves and shots_against. Like points, this is technically derivable but queried frequently enough to justify pre-computation.
- **Situation-specific saves** (power_play, shorthanded, even_strength) stored separately. These are available directly from the NHL API boxscore and are important for evaluating goalie quality in different game contexts.

## Dimension Table Design

### `dim_season`

- **`season_id` is a text key** (e.g., "20252026") matching the NHL API's own season identifier format. This avoids a surrogate key mapping step during ETL.
- **`season_type`** distinguishes regular season from playoffs. A single season ID can have multiple rows if needed, though the current implementation defaults to "regular."

### `dim_team`

- **`team_abbrev` is the natural key** (e.g., "COL", "TOR") rather than a surrogate integer. Team abbreviations are stable, human-readable, and match the NHL API response format directly. This simplifies ETL and makes fact table rows readable without a join.
- **Division and conference are denormalized** into this table. With 32 rows, a separate `dim_division` table would add a join for zero practical benefit.

### `dim_player`

- **`player_id` comes from the NHL API** rather than using a surrogate key. The API's player IDs are stable integers, so there's no need for an additional mapping layer.
- **`team_abbrev` is a foreign key** to `dim_team`, representing the player's current team. This is a slowly changing dimension — when a player is traded, their row is updated. Historical team affiliation is captured in the fact tables (each stat row has its own `team_abbrev`).
- **`updated_at` timestamp** tracks when the player record was last refreshed, supporting incremental updates.

### `dim_game`

- **`game_id` comes from the NHL API.** Same rationale as player IDs.
- **`game_state`** tracks the game lifecycle (FUT → LIVE → OFF → FINAL). This allows the pipeline to identify which games need re-extraction (incomplete games) versus which are finalized.
- **Both `home_team` and `away_team`** reference `dim_team`. This supports queries filtered by either home or away perspective without needing to union two tables.

## Indexing Strategy

Indexes are chosen based on expected query patterns:

| Index | Supports |
|-------|----------|
| `idx_skater_stats_game` | "All skater stats for game X" |
| `idx_skater_stats_player` | "All games for player X" (rolling averages, career stats) |
| `idx_skater_stats_team` | "All stats for team X's players" |
| `idx_goalie_stats_game` | "All goalie stats for game X" |
| `idx_goalie_stats_player` | "All games for goalie X" |
| `idx_game_date` | "All games on date X" (daily pipeline runs) |
| `idx_game_season` | "All games in season X" (season-level reports) |

The composite primary keys on fact tables also serve as implicit indexes on `(player_id, game_id)`.

## Pipeline Metadata

The `pipeline_runs` table is not part of the star schema itself but supports operational monitoring:

- **Tracks each ETL run** with start/end timestamps, row counts, and status.
- **Enables debugging** when data looks wrong — check if the pipeline ran successfully for a given date.
- **Supports incremental loading** — query the last successful run date to determine what new data to extract.
