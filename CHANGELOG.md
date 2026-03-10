# Changelog

**Recent releases for MCP Memory Service (v10.25.0 and later)**

All notable changes to the MCP Memory Service project will be documented in this file.

**Versions v10.24.0 and earlier** – See [docs/archive/CHANGELOG-HISTORIC.md](./docs/archive/CHANGELOG-HISTORIC.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [10.26.3] - 2026-03-10

### Fixed

- **Dashboard: metadata object values now rendered as JSON** (`app.js`, #582): Metadata values that are objects (or arrays of objects) were previously rendered as `[object Object]`. They are now serialised with `JSON.stringify` and HTML-escaped via `escapeHtml`, fixing both the display issue and a potential XSS vector introduced by the naive object-to-string coercion.
- **Dashboard: long memory content collapsed by default in detail modal; quality tab fetches full object** (`app.js`, `style.css`, #583): Memory content longer than 500 characters is now collapsed with a "Show more / Show less" toggle in the detail modal. When opening a memory from the quality tab, the full memory object is fetched via `GET /api/memories/{hash}` before the modal opens, preventing incomplete data display.
- **Quality scorer: empty query during `store_memory` no longer yields 0.0 score** (`ai_evaluator.py`, #584): The Groq scorer previously used a relevance-based prompt even when the query was empty (as is the case for `store_memory` calls). An empty query produced a semantically meaningless prompt and a near-zero score. The scorer now detects an empty query and switches to an absolute quality prompt that evaluates content quality independently of any query.
- **Quality scorer: Groq 429 rate limit triggers model fallback chain** (`ai_evaluator.py`, #585): The Groq quality scorer now attempts a sequence of models (`llama-3.1-8b-instant`, `llama3-8b-8192`, `gemma2-9b-it`) in order when a `429 Too Many Requests` response is received, instead of failing hard. This prevents quality scoring from failing silently under rate pressure and improves resilience for high-throughput deployments.

## [10.26.2] - 2026-03-08

### Fixed

- **[#576] OAuth token exchange fails with 500 for public PKCE clients** (`authorization.py`): claude.ai and other MCP clients that use OAuth 2.1 public-client flow (PKCE without `client_secret`) received a `500 Internal Server Error` during token exchange because the endpoint unconditionally called `authenticate_client()`, which requires a secret. The endpoint now detects public PKCE clients — requests that supply a `code_verifier` but no `client_secret` — and skips secret authentication, using the PKCE verifier as the sole identity proof instead, in accordance with OAuth 2.1 §2.1. Confidential clients (with `client_secret`) are unaffected. Closes #576.
- **Missing `/.well-known/oauth-protected-resource` endpoint** (`discovery.py`): The endpoint required by RFC 9728 and the MCP OAuth spec was returning 404, breaking OAuth discovery for compliant clients. Added `OAuthProtectedResourceMetadata` Pydantic model and the corresponding route, which advertises the resource identifier and authorization server URLs with `token_endpoint_auth_methods_supported: ["none"]`.
- **Opaque OAuth error logging**: Added `exc_info=True` to exception handlers in the token and authorization endpoints so that full tracebacks are recorded in logs instead of generic error messages, making future debugging significantly easier.

### Added

- **Automated CHANGELOG housekeeping workflow** (`.github/workflows/changelog-housekeeping.yml`): Monthly GitHub Actions workflow (runs on the 1st of each month, also triggerable via `workflow_dispatch`) that automatically archives CHANGELOG entries older than the 8 most recent versions into `docs/archive/CHANGELOG-HISTORIC.md`. Keeps the main CHANGELOG lean for faster reads while preserving full history. Validates that no version entries are lost during archival.
- **Changelog housekeeping script** (`scripts/maintenance/changelog_housekeeping.py`): Python script backing the workflow. Keeps the 8 most recent versions in `CHANGELOG.md`, moves older entries to the historic archive, and trims the README "Previous Releases" section to a maximum of 7 entries. Supports `--dry-run` for safe preview before applying changes.

## [10.26.1] - 2026-03-08

### Fixed

- **[#570] Hybrid backend misidentified as sqlite-vec in MCP health checks** (`memory_health` tool): `HealthCheckFactory` relied solely on the storage object's class name to select the health-check strategy. When the hybrid backend's storage is accessed through a delegation or wrapper layer the class name is not `HybridMemoryStorage`, so the factory fell back to the sqlite-vec strategy and reported `"sqlite-vec"` instead of `"hybrid"`, hiding Cloudflare sync status from users. The factory now performs structural detection — if the storage object exposes both a `primary` attribute and either a `secondary` or `sync_service` attribute it is classified as hybrid regardless of class name. The existing SQLite and Cloudflare strategy paths are unchanged. Adds three focused unit tests for strategy selection (sqlite class-name path, wrapped/delegated hybrid structural path, unknown fallback). Fixes #570.

## [10.26.0] - 2026-03-07

### Added

- **Credentials tab in Settings modal** (`GET /api/config/credentials`, `POST /api/config/credentials/test`, `POST /api/config/credentials`): Manage Cloudflare API token, Account ID, D1 Database ID, and Vectorize Index directly from the dashboard. Credentials shown with partial-reveal (masked) display and an eye-toggle for full reveal.
- **Connection test gate (test-gate pattern)**: Credentials must pass a live connection test before they can be saved, preventing accidental misconfiguration.
- **Sync Owner selector** (`MCP_HYBRID_SYNC_OWNER`: `http` / `both` / `mcp`): New setting to control which server handles Cloudflare sync in hybrid mode. Default is `http` (recommended) — HTTP server owns all sync; MCP server (Claude Desktop) uses SQLite-Vec only, removing the need for a Cloudflare token in the MCP config.
- **Settings tabs restructured**: The Backup tab is split into three focused tabs — Quality, Backup, and Server — bringing the total to 7 tabs for clearer organisation.

### Security

- **SSRF protection on credentials endpoint**: `account_id` validated against `[a-f0-9]{32}` regex before use in Cloudflare API calls, blocking Server-Side Request Forgery via crafted account IDs.
- **Newline injection prevention**: Credential values sanitised to reject embedded newlines, preventing HTTP header injection.
- **`sync_owner` allowlist**: Only `http`, `both`, and `mcp` are accepted; unknown values are rejected with a 422 error.

### Documentation

- `CLAUDE.md` and `README.md` updated: `MCP_HYBRID_SYNC_OWNER=http` documented as the recommended configuration for hybrid mode, along with the rationale (HTTP server as sole sync owner, MCP server token-free).

### CI

- Claude Code Review GitHub Actions workflow disabled due to OAuth token expiry issues (will be migrated to API key auth).

### Tests

- No new tests added in this release (1,420 total).

## [10.25.3] - 2026-03-07

### Fixed

- **[#561] Strict stdio MCP clients (e.g. Codex CLI) timing out during startup handshake**: Non-LM-Studio stdio clients performing eager initialization could exceed the client's fixed handshake budget (Codex uses ~10 s). The eager-init timeout is now capped at 5.0 s for these clients, ensuring the MCP handshake completes within budget. Co-authored-by SergioChan.
- **Syntax errors in eager-init timeout cap (follow-up to PR #569)**: Resolved a duplicate function call, an orphaned closing parenthesis, and a duplicate `return` statement introduced in the initial fix. Named constants replace magic numbers, a dead-code guard was corrected, and warning messages were clarified.
- **Hybrid sync premature termination**: The cloud-to-local sync aborted early when `synced_count` was 0 at the `HYBRID_MIN_CHECK_COUNT` (1,000) threshold, even though thousands of memories remained unchecked. The early-exit condition now only triggers after all `secondary_count` memories have been inspected, ensuring a complete Cloudflare-to-local sync.
- **Dashboard version badge always blank**: `loadVersion()` called `/health` which returns only `{"status":"healthy"}` since the v10.21.0 GHSA-73hc security hardening. Changed to `/health/detailed` which includes the `version` field.

### Chores

- `.gitignore` updated to exclude TLS certificate files (`*.pem`, `certs/` directory) to prevent accidental credential commits.

## [10.25.2] - 2026-03-07

### Fixed

- **Health check in `update_and_restart.sh` always reported "unknown" version**: The `/api/health` endpoint was stripped of its `version` field in v10.21.0 (security hardening GHSA-73hc-m4hx-79pj). The update script still tried to read `data.get('version')`, causing it to always fall back to "unknown" and wait the full 15-second timeout before giving up. The check now reads the `status` field (`"healthy"`) to confirm the server is up, and reports the already-known pip-installed version instead.

## [10.25.1] - 2026-03-06

### Security

- **[GHSA-g9rg-8vq5-mpwm] Wildcard CORS default enables cross-origin memory theft**: `MCP_CORS_ORIGINS` defaulted to `'*'`, allowing any website to read API responses cross-origin when combined with anonymous access. Default changed to `'http://localhost:8000,http://127.0.0.1:8000'`. `allow_credentials` is now automatically set to `False` when wildcard origins are configured (the two cannot be combined securely). A startup warning is logged if wildcard is explicitly set via environment variable.
- **[GHSA-x9r8-q2qj-cgvw] TLS certificate verification disabled in peer discovery**: Already fixed in v10.25.0 (config already contained `PEER_VERIFY_SSL=True` default). Advisory formally closed.

### Fixed

- **Soft-delete leak in `search_by_tag_chronological()`**: Missing `AND deleted_at IS NULL` filter caused soft-deleted memories to appear in chronological tag search results. All soft-delete filters are now consistently applied across all query paths.

## [10.25.0] - 2026-03-06

### Added

- **Embedding model migration script** (`scripts/maintenance/migrate_embeddings.py`): Standalone script for migrating embeddings between models, including across different dimensions (e.g., 384-dim `all-MiniLM-L6-v2` to 768-dim `nomic-embed-text`). Works with any OpenAI-compatible API (Ollama, vLLM, OpenAI, TEI). Features: `--dry-run`, auto-detect dimension, timestamped backup, service detection (macOS launchd, Linux systemd), cross-platform DB path detection, `--keep-graph` option, batched embedding with progress, post-migration integrity verification. Closes #552.

### Fixed

- **[#557] Soft-delete leaks in recall, time-range, and statistics methods**: `recall()` (both semantic and time-based paths), `get_memories_by_time_range()`, `get_largest_memories()`, and `get_memory_timestamps()` (both branches) were missing `deleted_at IS NULL` filters, causing soft-deleted memories to appear in results.
- **[#557] Incorrect cosine distance score formula in recall()**: Used `1.0 - distance` but cosine distance ranges [0, 2], producing negative scores for dissimilar pairs. Corrected to `max(0.0, 1.0 - (distance / 2.0))` to map to [0, 1].
- **[#557] Tag parsing in get_largest_memories()**: Used `json.loads()` to parse tags, but tags are stored as comma-separated strings. Changed to `split(",")` to match all other methods.
- **[#558] Substring tag matching bug**: `get_all_memories(tags=["test"])`, `count_all_memories(tags=["test"])`, and `retrieve()` used `LIKE '%test%'`, incorrectly matching `"testing"`, `"my-test-tag"`, etc. All now use the canonical GLOB exact-match pattern: `(',' || REPLACE(tags, ' ', '') || ',') GLOB '*,tag,*'`. Added `_escape_glob()` helper to prevent GLOB wildcard injection (`*`, `?`, `[`) from user-supplied tag values. `search_by_tag_chronological()` LIMIT/OFFSET now parameterized instead of f-string interpolated.
- **[#559] O(n²) memory in association sampling**: `_sample_memory_pairs()` materialized all `combinations(memories, 2)` into a list (50M pairs for 10k memories) just to pick 100. Now uses random index pair generation, O(max_pairs) in the sparse case.
- **[#559] Broken duplicate detection in consolidation**: `_get_existing_associations()` loaded all memories and filtered by `memory_type=="association"`, but new associations are stored with `memory_type="observation"` and tag `"association"`. The filter never matched, so duplicate associations were never prevented. Now uses `search_by_tag(["association"])`.
- **[#560] Soft-delete gaps in write and statistics methods**: `get_memory_connections()`, `get_access_patterns()`, `update_memory_metadata()`, and `update_memories_batch()` could return or modify tombstoned memories. All now include `deleted_at IS NULL` filters. `delete()` error handler now explicitly rolls back the transaction with `sqlite3.OperationalError` narrowing to prevent dangling embedding DELETEs.

### Performance

- **Batch access metadata persistence** (`retrieve()`): Access metadata now persisted in one `executemany` call per query instead of N individual `UPDATE+COMMIT` round-trips (new `_persist_access_metadata_batch()` method).
- **Hybrid search O(n+m) deduplication** (`retrieve_hybrid()`): Replaced O(n×m) nested-loop deduplication with O(n+m) dict-based merging. BM25-only memories now batch-fetched in one SQL query (capped at 999 to respect `SQLITE_MAX_VARIABLE_NUMBER`) instead of N+1 individual `get_by_hash()` calls.

### Tests

- 23 new regression tests covering all fixed methods
- Total: 1,420 tests

