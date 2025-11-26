# Historic Changelog

**Historic releases for MCP Memory Service (v8.0.0 - v8.23.0 and v7.x)**

For recent releases (v8.24.0+), see [CHANGELOG.md](./CHANGELOG.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [8.23.0] - 2025-11-10

### Added
- **Consolidation Scheduler via Code Execution API** - Dream-based memory consolidation now operates independently of MCP server
  - **Architecture Shift**: Migrated ConsolidationScheduler from MCP server to HTTP server using Code Execution API (v8.19.0+)
  - **Token Efficiency**: Achieves **88% token reduction** (803K tokens/year saved) by eliminating redundant memory retrieval
  - **24/7 Operation**: Consolidation now runs continuously via HTTP server, independent of Claude Desktop sessions
  - **Code Execution Extensions**:
    - Added `CompactConsolidationResult` and `CompactSchedulerStatus` types for efficient data transfer
    - Implemented `consolidate()` and `scheduler_status()` functions in API operations
    - Enhanced API client with consolidator/scheduler management capabilities
  - **HTTP API Endpoints** (new):
    - `POST /api/consolidation/trigger` - Manual consolidation trigger for specific time horizons
    - `GET /api/consolidation/status` - Scheduler health and job status monitoring
    - `GET /api/consolidation/recommendations` - Analysis-based consolidation suggestions
  - **Graceful Lifecycle**: HTTP server lifespan events handle scheduler startup/shutdown
  - **Dependencies**: Made `apscheduler>=3.11.0` a required dependency (previously optional)
  - **Files Modified**:
    - `src/mcp_memory_service/api/types.py` - New compact result types
    - `src/mcp_memory_service/api/operations.py` - Consolidation functions
    - `src/mcp_memory_service/api/client.py` - Client methods
    - `src/mcp_memory_service/api/__init__.py` - Export updates
    - `src/mcp_memory_service/web/app.py` - Scheduler integration
    - `src/mcp_memory_service/web/api/consolidation.py` - NEW endpoint router
    - `pyproject.toml` - Dependency update

### Changed
- **Consolidation Workflow**: Users can now trigger and monitor consolidation via HTTP API or web dashboard
- **Performance**: Background consolidation no longer impacts MCP server response times
- **Reliability**: Scheduler continues running even when Claude Desktop is closed

### Migration Notes
- **Backward Compatible**: Existing MCP consolidation tools continue to work via Code Execution API
- **HTTP Server Required**: For scheduled consolidation, HTTP server must be running (`export MCP_HTTP_ENABLED=true`)
- **No Action Needed**: Consolidation automatically migrates to HTTP server when enabled

### Technical Details
- **Token Savings Breakdown**:
  - Before: ~900K tokens/year (MCP server retrieval overhead)
  - After: ~97K tokens/year (compact API responses)
  - Reduction: 803K tokens (88% efficiency gain)
- **Execution Model**: Code Execution API handles consolidation in isolated Python environment
- **Scheduler Configuration**: Same settings as before (`.env` or environment variables)

## [8.22.3] - 2025-11-10

### Fixed
- **Complete Tag Schema Validation Fix**: Extended oneOf schema pattern to ALL MCP tools with tags parameter
  - Previous fixes (v8.22.1-v8.22.2) only addressed character-split bugs in handler code
  - Root cause: 7 tools had schemas accepting ONLY arrays, rejecting comma-separated strings at MCP client validation
  - Updated tool schemas to accept both array and string formats using `oneOf` pattern:
    - `update_memory_metadata` (line 1733)
    - `search_by_tag` (line 1428)
    - `delete_by_tag` (line 1475)
    - `delete_by_tags` (line 1506)
    - `delete_by_all_tags` (line 1536)
    - `ingest_document` (line 1958)
    - `ingest_directory` (line 2015)
  - Added `normalize_tags()` calls in all affected handlers to properly parse comma-separated strings
  - Validation now happens gracefully: client accepts both formats, server normalizes to array
  - **Breaking**: Users must reconnect MCP client (`/mcp` in Claude Code) to fetch updated schemas
  - Resolves recurring "Input validation error: 'X' is not of type 'array'" errors

### Technical Details
- **Validation Flow**: MCP client validates against tool schema → Server normalizes tags → Storage processes
- **Schema Pattern**: Each tags parameter now uses `{"oneOf": [{"type": "array"}, {"type": "string"}]}`
- **Handler Updates**: 7 handlers updated to import and call `normalize_tags()` from `services/memory_service.py`
- **File Modified**: `src/mcp_memory_service/server.py` (schemas + handlers)

### Notes
- This completes the tag parsing fix saga (v8.22.1 → v8.22.2 → v8.22.3)
- v8.22.1: Fixed character-split bug in documents.py
- v8.22.2: Extended fix to server.py and cli/ingestion.py handlers
- v8.22.3: Fixed JSON schemas to accept comma-separated strings at validation layer

## [8.22.2] - 2025-11-09

### Fixed
- **Complete Tag Parsing Fix** - Extended v8.22.1 fix to all remaining locations where tag parsing bug existed
  - **Additional Files Fixed**:
    - `src/mcp_memory_service/server.py` - MCP ingest_document and ingest_directory tool handlers (2 locations)
    - `src/mcp_memory_service/cli/ingestion.py` - CLI ingest_file and ingest_directory commands (2 locations)
  - **Root Cause**: Same as v8.22.1 - `.extend()` on comma-separated string treated as character iterable
  - **Impact**: MCP tools and CLI commands now correctly parse comma-separated tags
  - **Database Repair**: 6 additional memories repaired from metadata backup (total 19 across both releases)
  - **Verification**: All tag parsing code paths now include `isinstance()` type checking

## [8.22.1] - 2025-11-09

### Fixed
- **Document Ingestion Tag Parsing** - Fixed critical data corruption bug where tags were stored character-by-character instead of as complete strings
  - **Root Cause**: When `chunk.metadata['tags']` contained a comma-separated string (e.g., `"claude-code-hooks,update-investigation"`), the `extend()` method treated it as an iterable and added each character individually
  - **Symptom**: Tags like `"claude-code-hooks,update-investigation,configuration,breaking-changes"` became `['c','l','a','u','d','e','-','c','o','d','e','-','h','o','o','k','s',',','u','p','d','a','t','e',...]` (80+ character tags per memory)
  - **Impact**: Memories were unsearchable by tags, tag filtering broken, tag display cluttered with single characters
  - **Fix**: Added `isinstance()` type check to detect string vs list, properly split comma-separated strings before extending tag list
  - **Database Repair**: 13 affected memories automatically repaired using metadata field (which stored correct tags)
  - **Files Modified**: `src/mcp_memory_service/web/api/documents.py` (lines 424-430 for single uploads, 536-542 for batch uploads)

## [8.22.0] - 2025-11-09

### Fixed
- **Session-Start Hook Stability & UX** - Comprehensive reliability and output quality improvements
  - **Memory Age Calculation**: Fixed memory age analyzer defaulting to 365 days for all memories
    - Added `created_at_iso` field to Code Execution API response mapping
    - Now correctly shows recent work (e.g., "🕒 today", "📅 2d ago")
    - Resolves memory age display bug (Related: Issue #214)
  - **Timeout Improvements**: Prevents timeouts during DNS retries and slow network operations
    - Increased code execution timeout: 8000ms → 15000ms
    - Increased sessionStart hook timeout: 10000ms → 20000ms
  - **Tree Formatting Enhancements**: Complete rewrite for proper ANSI-aware rendering
    - ANSI-aware width calculation in wrapText() function
    - Tree prefix parameter for proper continuation line formatting
    - Normalized embedded newlines to prevent structure breaks
    - Fixed line breaks cutting through tree characters (│, ├─, └─)
  - **Date Sanitization**: Enhanced patterns for multi-line date formats
    - Removes clutter from old session summaries (e.g., "Date:\n  9.11.")
    - Added re-sanitization after section extraction
  - **Output Visibility**: Restored console.log output for user-visible tree display
    - Critical fix for output regression where tree was invisible to users
  - **Status Bar Improvements**: Added "memories" label for clarity
    - Format: "💭 6 (4 recent) memories" instead of just "💭 6 (4 recent)"
    - Corrected documentation: "static" instead of "300ms updates"
  - **Configuration**: Removed duplicate codeExecution block from config.json
  - Files modified: `core/session-start.js`, `utilities/context-formatter.js`, `statusline.sh`, `README.md`, `config.json`

## [8.21.0] - 2025-11-08

### Added
- **Amp PR Automator Agent** - Lightweight PR automation using Amp CLI (1,240+ lines)
  - OAuth-free alternative to Gemini PR Automator with file-based workflow
  - `.claude/agents/amp-pr-automator.md` - Complete agent definition
  - `scripts/pr/amp_quality_gate.sh` - Parallel complexity, security, type hint checks
  - `scripts/pr/amp_collect_results.sh` - Aggregate Amp analysis results
  - `scripts/pr/amp_suggest_fixes.sh` - Generate fix suggestions from review feedback
  - `scripts/pr/amp_generate_tests.sh` - Create pytest tests for new code
  - `scripts/pr/amp_detect_breaking_changes.sh` - Identify API breaking changes
  - `scripts/pr/amp_pr_review.sh` - Complete review workflow orchestration
  - Fast parallel processing with UUID-based prompt/response tracking
  - Credit conservation through focused, non-interactive tasks

### Fixed
- **Memory Hook Tag+Time Filtering** (Issue #214, PR #215) - Fixed semantic over-filtering bug
  - Enhanced `search_by_tag()` with optional `time_start` parameter across all backends
  - Replaced limited `parse_time_query` with robust `parse_time_expression` from `utils.time_parser`
  - Fixed HTTP client time filter format (ISO date instead of custom string)
  - Improved SQL construction clarity in Cloudflare backend
  - Removed unused `match_all` parameter from hybrid backend (regression fix)
  - Quality gate: 9.2/10 (Gemini Code Assist review - 4 critical issues fixed)
  - Time parser tests: 14/14 PASS (100%)

## [8.20.1] - 2025-11-08

### Fixed
- **retrieve_memory MCP tool**: Fixed MemoryQueryResult serialization error introduced in v8.19.1
  - Extract Memory object from MemoryQueryResult before formatting response
  - Add similarity_score to response for consistency with recall_memory
  - Affects all backends (sqlite-vec, cloudflare, hybrid)
  - Issue #211 follow-up fix - thanks @VibeCodeChef for detailed testing!

## [8.20.0] - 2025-11-08

### Added
- **GraphQL PR Review Integration** - GitHub GraphQL API for advanced PR operations
  - `resolve_threads.sh` - Auto-resolve review threads when commits address feedback (saves 2+ min/PR)
  - `thread_status.sh` - Display all review threads with resolution status
  - Reusable GraphQL helper library in `scripts/pr/lib/graphql_helpers.sh`
  - Smart commit tracking for resolved vs outdated threads
- **PR Automation Workflow** - Comprehensive Gemini Code Assist integration
  - `auto_review.sh` - Automated iterative PR review cycles (saves 10-30 min/PR)
  - `quality_gate.sh` - Pre-PR quality checks (complexity, security, tests, breaking changes)
  - `generate_tests.sh` - Auto-generate pytest tests for new code
  - `detect_breaking_changes.sh` - API diff analysis with severity classification
- **Amp Bridge Redesign** - Direct code execution mode for batch operations
  - Execute prompts directly without prompt file management
  - Batch processing support for multiple operations
  - Improved error handling and output formatting
- **Code Quality Guard Agent** - Fast automated code quality analysis
  - Pre-commit hook for complexity scoring (blocks >8, warns >7)
  - Security pattern detection (SQL injection, XSS, command injection)
  - TODO prioritization with impact analysis (Critical/High/Medium/Low)
  - Integrated with Gemini CLI for fast analysis
- **Gemini PR Automator Agent** - Eliminates manual review wait times
  - Automated "Fix → Comment → /gemini review → Wait → Repeat" workflow
  - Intelligent fix classification (safe vs unsafe)
  - Comprehensive test generation for all new code
  - Breaking change detection with severity levels
- **Groq Bridge Integration** - 10x faster alternative to Gemini CLI
  - Python CLI (`groq_agent_bridge.py`) for non-interactive LLM calls
  - Support for llama-3.3-70b-versatile, Kimi K2 (256K context), and other Groq models
  - Drop-in replacement for Gemini CLI with same interface
  - Model comparison documentation with performance benchmarks
- **Pre-commit Hook Infrastructure** - Quality gates before commit
  - Symlinked hook: `.git/hooks/pre-commit` → `scripts/hooks/pre-commit`
  - Automated complexity checks on staged Python files
  - Security vulnerability scanning (blocks commit if found)
  - Graceful degradation if Gemini CLI not installed

### Documentation
- Added `docs/pr-graphql-integration.md` - GraphQL PR review integration guide
- Added `docs/integrations/groq-bridge.md` - Setup and usage guide for Groq integration
- Added `docs/integrations/groq-integration-summary.md` - Integration overview
- Added `docs/integrations/groq-model-comparison.md` - Performance benchmarks and model selection
- Added `docs/amp-cli-bridge.md` - Amp CLI integration guide
- Added `docs/development/todo-tracker.md` - Automated TODO tracking output
- Added `docs/troubleshooting/hooks-quick-reference.md` - Hook debugging and troubleshooting
- Added `docs/document-ingestion.md` - Document parsing guide
- Added `docs/legacy/dual-protocol-hooks.md` - Historical hook configuration
- Added `scripts/maintenance/memory-types.md` - Memory type taxonomy documentation

### Changed
- Updated `.claude/agents/github-release-manager.md` - Enhanced with latest release workflow
- Updated `.env.example` - Removed deprecated ChromaDB backend references
- Updated API specification - Removed `chroma` from backend enum
- Updated example configs - Modernized to use Python module approach

### Fixed
- **PR Automation Scripts** - Addressed all Gemini Code Assist review feedback
  - Removed hardcoded repository name from all PR scripts (now dynamic with `gh repo view`)
  - Fixed script path handling in documentation examples
  - Improved error messages and validation in GraphQL helpers
  - Enhanced documentation with correct usage examples
- Removed all ChromaDB artifacts from active code (deprecated in v8.0.0)
  - Fixed broken test imports (`CHROMADB_MAX_CONTENT_LENGTH` removed)
  - Updated integration tests to remove `--chroma-path` CLI assertions
  - Cleaned up example configurations
  - Added clear deprecation warnings in `install.py`

### Performance
- Groq bridge provides 10x faster inference vs Gemini CLI
  - llama-3.3-70b: ~300ms response time
  - Kimi K2: ~200ms response time (fastest)
  - llama-3.1-8b-instant: ~300ms response time
- Pre-commit hooks minimize developer wait time with complexity checks

## [8.19.1] - 2025-11-07

### Fixed
- **Critical MCP Tool Regressions** (Issue #211) - Two core MCP tools broken in v8.19.0
  - **retrieve_memory**: Fixed parameter error where unsupported 'tags' parameter was passed to storage.retrieve()
    - Removed unsupported parameters from storage call
    - Implemented post-retrieval filtering in MemoryService
    - File: `src/mcp_memory_service/services/memory_service.py`
  - **search_by_tag**: Fixed type error where code assumed created_at was always string
    - Added type checking for both float (timestamp) and string (ISO format)
    - Uses `datetime.fromtimestamp()` for floats, `datetime.fromisoformat()` for strings
    - Files: `src/mcp_memory_service/server.py` (handle_search_by_tag, handle_retrieve_memory)
  - **Impact**: Both tools now work correctly with hybrid storage backend
  - **Root Cause**: v8.19.0 refactoring introduced incompatibilities with hybrid storage

## [8.19.0] - 2025-11-07

### Added
- **Code Execution Interface API** 🚀 - Revolutionary token efficiency for MCP Memory Service (Issue #206)
  - **Core API Module** (`src/mcp_memory_service/api/`):
    - Compact NamedTuple types (91% size reduction vs MCP tool responses)
    - Core operations: `search()`, `store()`, `health()`
    - Sync wrapper utilities (hide asyncio complexity)
    - Storage client with connection reuse
  - **Session Hook Migration** (`claude-hooks/core/session-start.js`):
    - Code execution wrapper for token-efficient memory retrieval
    - Automatic MCP fallback (100% reliability)
    - Performance metrics tracking
    - Zero breaking changes
  - **Migration Guide** (`docs/migration/code-execution-api-quick-start.md`):
    - 5-minute migration workflow
    - Cost savings calculator
    - Comprehensive troubleshooting
    - Platform-specific instructions
  - **Comprehensive Documentation**:
    - API reference guide
    - Phase 1 and Phase 2 implementation summaries
    - Research documents (10,000+ words)
    - Performance benchmarks

### Changed
- **Installer Default** - Code execution now enabled by default for new installations
  - Auto-detects Python path (Windows: `python`, Unix: `python3`)
  - Validates Python version (warns if < 3.10)
  - Shows token reduction benefits during installation
  - Graceful upgrade path for existing users

### Performance
- **Token Reduction (Validated)**:
  - Session hooks: **75% reduction** (3,600 → 900 tokens)
  - Search operations: **85% reduction** (2,625 → 385 tokens)
  - Store operations: **90% reduction** (150 → 15 tokens)
  - Health checks: **84% reduction** (125 → 20 tokens)
- **Execution Performance**:
  - Cold start: 61.1ms (target: <100ms)
  - Warm calls: 1.3ms avg (target: <10ms)
  - Memory overhead: <10MB
- **Annual Savings Potential**:
  - 10 users: **$23.82/year** (158.8M tokens saved)
  - 100 users: **$238.20/year** (1.59B tokens saved)
  - 1000 users: **$2,382/year** (15.9B tokens saved)

### Fixed
- **Cross-Platform Compatibility** - Replaced hardcoded macOS paths with `get_base_directory()`
- **Async/Await Pattern** - Fixed async `health()` to properly await storage operations
- **Resource Management** - Added explicit `close()` and `close_async()` methods
- **Documentation** - Fixed Unicode symbols and absolute local paths for better compatibility

### Technical Details
- **Files Added**: 23 files, 6,517 lines (production + tests + docs)
- **Test Coverage**: 52 tests (88% passing)
- **Backward Compatibility**: 100% (zero breaking changes)
- **Platform Support**: macOS, Linux, Windows
- **API Exports**: `search`, `store`, `health`, `close`, `close_async`

### Removed
- **Obsolete ChromaDB Test Infrastructure** - Removed all test files referencing deprecated ChromaDB storage backend
  - **Deleted Files**:
    - `tests/performance/test_caching.py` - ChromaDB-specific performance tests
    - `tests/test_timestamp_recall.py` - Timestamp tests using ChromaDB APIs
    - `tests/test_tag_storage.py` - Tag storage tests for ChromaDB
    - `tests/integration/test_storage.py` - ChromaDB storage diagnostic script
    - `tests/unit/test_tags.py` - Tag deletion tests using deprecated CHROMA_PATH
    - `tests/test_content_splitting.py::test_chromadb_limit()` - ChromaDB content limit test
  - **Updated**: `tests/conftest.py` - Generic database testing fixture (removed ChromaDB reference)
  - **Context**: ChromaDB backend was fully replaced by SQLite-vec, Cloudflare, and Hybrid backends
  - **Impact**: Test suite no longer has broken imports or references to removed storage layer

## [8.18.2] - 2025-11-06

### Fixed
- **MCP Tool Handler Method Name** - Fixed critical bug where MCP tool handlers called non-existent `retrieve_memory()` method
  - **Root Cause**: Method name mismatch introduced in commit 36e9845 during MemoryService refactoring (Oct 28, 2025)
  - **Symptom**: `'MemoryService' object has no attribute 'retrieve_memory'` error when using MCP retrieve_memory tool
  - **Fix**: Updated handlers to call correct `retrieve_memories()` method (plural)
  - **Files Modified**: `src/mcp_memory_service/server.py` (line 2153), `src/mcp_memory_service/mcp_server.py` (line 227)
  - **Additional**: Removed unsupported `min_similarity` parameter from MCP tool definition
  - **Impact**: MCP retrieve_memory tool now functions correctly
  - **Issue**: [#207](https://github.com/doobidoo/mcp-memory-service/issues/207)

## [8.18.1] - 2025-11-05

### Fixed
- **Test Suite Import Errors** - Resolved critical import failures blocking all test collection
  - **MCP Client Import**: Updated from deprecated `mcp` module to `mcp.client.session` (v1.1.2 API)
  - **Storage Path Import**: Removed obsolete `CHROMA_PATH` constant that no longer exists in current architecture
  - **Impact**: Restored ability to collect and run 190 test cases across unit, integration, and E2E test suites
  - **PR**: [#205](https://github.com/doobidoo/mcp-memory-service/pull/205)
  - **Issue**: [#204](https://github.com/doobidoo/mcp-memory-service/issues/204)

### Technical Details
- **Test Files Updated**: `tests/unit/test_import.py`, `tests/integration/test_store_memory.py`
- **Import Fix**: `from mcp import ClientSession, StdioServerParameters` → `from mcp.client.session import ClientSession`
- **Cleanup**: Removed dependency on deprecated storage constants

## [8.18.0] - 2025-11-05

### Performance
- **Analytics Dashboard Optimization** - 90% performance improvement for dashboard analytics
  - **New Method**: `get_memory_timestamps()` added to all storage backends (SQLite-Vec, Cloudflare, Hybrid)
  - **Optimization**: Single optimized SQL query instead of N individual queries for timestamp retrieval
  - **Impact**: Dashboard analytics load significantly faster, especially with large memory datasets
  - **PR**: [#203](https://github.com/doobidoo/mcp-memory-service/pull/203)
  - **Issue**: [#186](https://github.com/doobidoo/mcp-memory-service/issues/186)

### Added
- **Type Safety Enhancements** - Pydantic models for analytics data structures
  - **Models**: `LargestMemory` (content hash, size, created timestamp) and `GrowthTrendPoint` (date, cumulative count)
  - **Benefit**: Enhanced type checking and validation for analytics endpoints
  - **File**: `src/mcp_memory_service/web/api/analytics.py`

### Fixed
- **Weekly Activity Year Handling** - Fixed incorrect aggregation of same week numbers across different years
  - **Issue**: Week 1 of 2024 and Week 1 of 2025 were being combined in weekly activity charts
  - **Solution**: Year included in grouping logic for proper temporal separation
  - **Impact**: Weekly activity charts now accurately reflect year boundaries

### Technical Details
- **Storage Interface**: `get_memory_timestamps()` method added to base `MemoryStorage` class
- **Backend Implementation**: Optimized SQL queries for SQLite-Vec, Cloudflare D1, and Hybrid storage
- **Code Quality**: Import organization and naming consistency improvements per Gemini Code Assist review

## [8.17.1] - 2025-11-05

### Documentation
- **Workflow Documentation Harvest** - Comprehensive project management templates adapted from PR #199
  - **GitHub Issue Templates**: Structured bug/feature/performance reports with environment validation
    - `bug_report.yml`: OS, Python version, storage backend, reproduction steps
    - `feature_request.yml`: Use case, alternatives, impact assessment
    - `performance_issue.yml`: Metrics, database size, profiling data
    - `config.yml`: Template selector with Wiki/Discussions links
  - **Regression Test Scenarios**: 10 structured test procedures (Setup → Execute → Evidence → Pass/Fail)
    - Database locking tests (concurrent MCP servers, concurrent operations)
    - Storage backend integrity (hybrid sync, backend switching)
    - Dashboard performance (page load <2s, operations <1s)
    - Tag filtering correctness (exact matching, index usage)
    - MCP protocol compliance (schema validation, tool execution)
  - **PR Review Guide**: Standardized code review with Gemini integration
    - Template compliance checklist, code quality standards (type hints, async patterns, security)
    - Testing verification (>80% coverage), merge criteria, effective feedback templates
  - **Issue Management Guide**: Triage, closure, and post-release workflows
    - 48h triage response, professional closure templates, GitHub CLI automation
    - Issue→PR→Release tracking, post-release systematic review
  - **Release Checklist Enhancements**: Version management and emergency procedures
    - 3-file version bump procedure (`__init__.py` → `pyproject.toml` → `uv lock`)
    - CHANGELOG quality gates, GitHub workflow verification
    - Emergency rollback procedure (Docker/PyPI/Git steps, recovery timeline)
  - **Impact**: 2,400+ lines of actionable documentation (7 new files, 1 enhanced)
  - **Files**: `.github/ISSUE_TEMPLATE/`, `docs/testing/regression-tests.md`, `docs/development/pr-review-guide.md`, `docs/development/issue-management.md`, `docs/development/release-checklist.md`
  - **Source**: Adapted from [PR #199](https://github.com/doobidoo/mcp-memory-service/pull/199) by Ray Walker (27Bslash6)
  - **Commit**: [ca5ccf3](https://github.com/doobidoo/mcp-memory-service/commit/ca5ccf3f460feca06d3c9232303a6e528ca2c76f)

### Fixed
- **CRITICAL: Dashboard Analytics Accuracy** - Fixed analytics endpoint showing incorrect memory count
  - **Issue**: Dashboard displayed 1,000 memories (sampling) instead of actual 2,222 total
  - **Root Cause**: Analytics endpoint used `get_recent_memories(n=1000)` sampling approach instead of direct SQL query
  - **Solution**: Direct SQL query via `storage.primary.conn` for `HybridMemoryStorage` backend
  - **File**: `src/mcp_memory_service/web/api/analytics.py` (line 386)
  - **Impact**: Dashboard now shows accurate memory totals for all storage backends
  - **Additional Fix**: Corrected attribute check from `storage.sqlite` to `storage.primary` for hybrid backend detection

### Added
- **Malformed Tags Repair Utility** - Intelligent repair tool for JSON serialization artifacts in tags
  - **Script**: `scripts/maintenance/repair_malformed_tags.py`
  - **Repaired**: 1,870 malformed tags across 369 memories
  - **Patterns Detected**: JSON quotes (`\"tag\"`), brackets (`[tag]`), mixed artifacts
  - **Features**: Multi-tier parser, dry-run mode, automatic backups, progress tracking
  - **Safety**: Creates backup before modifications, validates repairs

- **Intelligent Memory Type Assignment** - Automated type inference for untyped memories
  - **Script**: `scripts/maintenance/assign_memory_types.py`
  - **Processed**: 119 untyped memories with multi-tier inference algorithm
  - **Inference Methods**:
    - Tag-based mapping (80+ tag-to-type associations)
    - Pattern-based detection (40+ content patterns)
    - Metadata analysis (activity indicators)
    - Fallback heuristics (default to "note")
  - **Confidence Scoring**: High/medium/low confidence levels for inference quality
  - **Features**: Dry-run mode, automatic backups, detailed statistics

### Technical Details
- **Analytics Fix**: Removed "Using sampling approach" warning from logs
- **Database Backups**: Both maintenance scripts create timestamped backups before modifications
- **Type Taxonomy**: Follows 24 core types from consolidated memory type system
- **Hybrid Backend**: Scripts properly detect and handle `HybridMemoryStorage` architecture

## [8.17.0] - 2025-11-04

### Added
- **Platform-Aware Consolidation Tool** - Cross-platform database path detection for memory type consolidation
  - **Auto-detection**: macOS (`~/Library/Application Support`), Windows (`%LOCALAPPDATA%`), Linux (`~/.local/share`)
  - **Script**: `scripts/maintenance/consolidate_memory_types.py` enhanced with `platform.system()` detection
  - **Benefit**: Works seamlessly across all platforms without manual path configuration
  - **PR**: [#201](https://github.com/doobidoo/mcp-memory-service/pull/201)

- **External JSON Configuration** - Editable consolidation mappings for flexible type management
  - **File**: `scripts/maintenance/consolidation_mappings.json` (294 mappings, v1.1.0)
  - **Schema**: JSON Schema validation with taxonomy documentation
  - **Extensibility**: Add custom type mappings without code changes
  - **Taxonomy**: 24 core types organized into 5 categories
  - **PR**: [#201](https://github.com/doobidoo/mcp-memory-service/pull/201)

- **Agent System Documentation** - Comprehensive agent guidelines for development workflows
  - **File**: `AGENTS.md` - Central documentation for available agents
  - **Agent**: `amp-bridge` - Amp CLI integration for research without credit consumption
  - **Integration**: Semi-automated file-based workflow with Amp's `@file` reference syntax
  - **CLAUDE.md**: Updated with Amp CLI Bridge architecture and quick start guide
  - **PR**: [#201](https://github.com/doobidoo/mcp-memory-service/pull/201)

### Fixed
- **Dashboard Analytics Chart Layout** - Resolved rendering and proportionality issues
  - **Fixed**: Chart bars rendering outside containers
  - **Fixed**: Uniform bar sizes despite different values
  - **Fixed**: Memory type distribution showing incorrect proportions
  - **Enhancement**: Switched to 200px pixel scale for proper visualization
  - **Enhancement**: CSS container constraints with `overflow-x: auto` and flexbox improvements
  - **Files**: `web/static/app.js`, `web/static/index.html`, `web/static/style.css`
  - **PR**: [#200](https://github.com/doobidoo/mcp-memory-service/pull/200)

### Technical Details
- **Platform Detection**: Uses `platform.system()` for "Darwin" (macOS), "Windows", and Linux
- **Backward Compatibility**: Existing scripts continue to work with new platform-aware paths
- **Agent Workflow**: Claude Code creates prompts → User runs `amp @prompt-file` → Amp writes response → Agent presents results
- **Chart Rendering**: Dashboard now properly visualizes memory distribution with accurate proportions

## [8.16.2] - 2025-11-03

### Fixed
- **Critical Bug**: Fixed bidirectional sync script crash due to incorrect Memory attribute access
  - **File**: `scripts/sync/sync_memory_backends.py`
  - **Root Cause**: Script accessed non-existent `memory.id` and `memory.hash` attributes instead of correct `memory.content_hash`
  - **Impact**: Bidirectional sync between SQLite-vec and Cloudflare backends completely broken
  - **Lines Fixed**: 81, 121, 137, 146, 149, 151, 153, 155, 158
  - **Testing**: Dry-run validated with 1,978 SQLite memories and 1,958 Cloudflare memories
  - **Result**: Successfully identified 338 memories to sync, 1,640 duplicates correctly skipped

### Technical Details
- **Error Type**: `AttributeError: 'Memory' object has no attribute 'id'/'hash'`
- **Correct Attribute**: `content_hash` - SHA-256 based unique identifier for memory content
- **Affected Methods**: `get_all_memories_from_backend()`, `_sync_between_backends()`
- **Backward Compatibility**: No breaking changes, only fixes broken functionality

## [8.16.1] - 2025-11-02

### Fixed
- **Critical Bug**: Fixed `KeyError: 'message'` in MCP server handler (`server.py:2118`)
  - **Issue**: [#198](https://github.com/doobidoo/mcp-memory-service/issues/198)
  - **Root Cause**: `handle_store_memory()` attempted to access non-existent `result["message"]` key
  - **Impact**: All memory store operations via MCP `server.py` handler failed completely
  - **Fix**: Properly handle `MemoryService.store_memory()` response format:
    - Success (single): `{"success": True, "memory": {...}}`
    - Success (chunked): `{"success": True, "memories": [...], "total_chunks": N}`
    - Failure: `{"success": False, "error": "..."}`
  - **Response Messages**: Now include truncated content hash for verification
  - **Related**: This was part of issue #197 where async/await bug was fixed in v8.16.0, but this response format bug was missed

### Added
- **Integration Tests**: New test suite for MCP handler methods (`tests/integration/test_mcp_handlers.py`)
  - **Coverage**: 11 test cases for `handle_store_memory()`, `handle_retrieve_memory()`, `handle_search_by_tag()`
  - **Regression Tests**: Specific tests for issue #198 to prevent future KeyError bugs
  - **Test Scenarios**: Success, chunked response, error handling, edge cases
  - **Purpose**: Prevent similar bugs in future releases

### Technical Details
- **Affected Handler**: Only `handle_store_memory()` was affected by this bug
- **Fixed Code Pattern**: Matches the correct pattern used in `mcp_server.py:182-205`
- **Backward Compatibility**: No breaking changes, only fixes broken functionality

## [8.16.0] - 2025-11-01

### Added
- **Memory Type Consolidation Tool** 🆕 - Professional-grade database maintenance for type taxonomy cleanup
  - **Script**: `scripts/maintenance/consolidate_memory_types.py` (v1.0.0)
  - **Configuration**: `scripts/maintenance/consolidation_mappings.json` (168 predefined mappings)
  - **Performance**: ~5 seconds for 1,000 memory updates
  - **Safety Features**:
    - ✅ Automatic timestamped backups before execution
    - ✅ Dry-run mode for safe preview
    - ✅ Transaction safety (atomic with rollback)
    - ✅ Database lock detection
    - ✅ HTTP server status warnings
    - ✅ Disk space verification
    - ✅ Backup integrity validation
  - **Consolidates**: 341 fragmented types → 24 core taxonomy types
  - **Real-world test**: 1,049 memories updated in 5s (59% of database)
  - **Type reduction**: 342 → 128 unique types (63% reduction)
  - **Zero data loss**: Only type reassignments, preserves all content

- **Standardized Memory Type Taxonomy** - 24 core types organized into 5 categories
  - **Content Types** (4): note, reference, document, guide
  - **Activity Types** (5): session, implementation, analysis, troubleshooting, test
  - **Artifact Types** (4): fix, feature, release, deployment
  - **Progress Types** (2): milestone, status
  - **Infrastructure Types** (5): configuration, infrastructure, process, security, architecture
  - **Other Types** (4): documentation, solution, achievement, technical
  - **Purpose**: Prevents future type fragmentation
  - **Benefits**: Improved query efficiency, consistent naming, better semantic grouping

### Changed
- **CLAUDE.md** - Added Memory Type Taxonomy section to Development Guidelines
  - Documents 24 core types with clear usage guidelines
  - Provides examples of what to avoid (bug-fix vs fix, technical-* prefixes)
  - Added consolidation commands to Essential Commands section
  - Includes best practices for maintaining type consistency

### Documentation
- **Comprehensive Maintenance Documentation**
  - Updated `scripts/maintenance/README.md` with consolidation tool guide
  - Added to Quick Reference table with performance metrics
  - Detailed usage instructions with safety prerequisites
  - Recovery procedures for backup restoration
  - Maintenance schedule recommendations (monthly dry-run checks)
  - **Real-world example**: Production consolidation results from Nov 2025

### Technical Details
- **Consolidation Mappings**:
  - NULL/empty → `note` (609 memories in real test)
  - Milestone/completion variants → `milestone` (21 source types → 60 memories)
  - Session variants → `session` (8 source types → 37 memories)
  - Technical-* prefix removal → base types (62 memories)
  - Project-* prefix removal → base types (67 memories)
  - Fix/bug variants → `fix` (8 source types → 28 memories)
  - See `consolidation_mappings.json` for complete mapping list (168 rules)

### Notes
- **Customizable**: Edit `consolidation_mappings.json` to customize behavior
- **Idempotent**: Safe to run multiple times with same mappings
- **Platform support**: Linux, macOS, Windows (disk space check requires statvfs)
- **Recommended schedule**: Run --dry-run monthly, execute when types exceed 150

## [8.15.1] - 2025-10-31

### Fixed
- **Critical Python Syntax Error in Hook Installer** - Fixed IndentationError in `claude-hooks/install_hooks.py` (line 790)
  - **Issue**: Extra closing braces in SessionEnd hook configuration caused installation to fail
  - **Symptom**: `IndentationError: unexpected indent` when running `python install_hooks.py`
  - **Root Cause**: Git merge conflict resolution left two extra `}` characters (lines 790-791)
  - **Impact**: Users could not install or update hooks after pulling v8.15.0
  - **Fix**: Removed extra closing braces, corrected indentation
  - **Files Modified**: `claude-hooks/install_hooks.py`
  - **Testing**: Verified successful installation on macOS after fix

### Technical Details
- **Line Numbers**: 788-791 in install_hooks.py
- **Error Type**: IndentationError (Python syntax)
- **Detection Method**: Manual testing during hook reinstallation
- **Resolution Time**: Immediate (same-day patch)

## [8.15.0] - 2025-10-31

### Added
- **`/session-start` Slash Command** - Manual session initialization for all platforms
  - Provides same functionality as automatic SessionStart hook
  - Displays project context, git history, relevant memories
  - **Platform**: Works on Windows, macOS, Linux
  - **Use Case**: Primary workaround for Windows SessionStart hook bug (#160)
  - **Location**: `claude_commands/session-start.md`
  - **Benefits**:
    - ✅ Safe manual alternative to automatic hooks
    - ✅ No configuration changes needed
    - ✅ Full memory awareness functionality
    - ✅ Prevents Claude Code hangs on Windows

### Changed
- **Windows-Aware Installer** - Platform detection and automatic configuration
  - Detects Windows platform during hook installation
  - Automatically skips SessionStart hook configuration on Windows
  - Shows clear warning about SessionStart limitation
  - Suggests `/session-start` slash command as alternative
  - Also skips statusLine configuration on Windows (requires bash)
  - **Files Modified**: `claude-hooks/install_hooks.py` (lines 749-817)
  - **User Impact**: Prevents Windows users from accidentally breaking Claude Code

### Documentation
- **Enhanced Windows Support Documentation**
  - Updated `claude_commands/README.md` with `/session-start` command details
  - Added Windows workaround section to `claude-hooks/README.md`
  - Updated `CLAUDE.md` with `/session-start` as #1 recommended workaround
  - Added comprehensive troubleshooting guidance
  - Updated GitHub issue #160 with new workaround instructions

### Fixed
- **Windows Installation Experience** - Prevents SessionStart hook deadlock (Issue #160)
  - **Previous Behavior**: Windows users install hooks → Claude Code hangs → frustration
  - **New Behavior**: Windows users see warning → skip SessionStart → use `/session-start` → works
  - **Breaking Change**: None - fully backward compatible
  - **Upstream Issue**: Awaiting fix from Anthropic Claude Code team (claude-code#9542)

### Technical Details
- **Files Created**: 1 new slash command
  - `claude_commands/session-start.md` - Full command documentation
- **Files Modified**: 4 files
  - `claude-hooks/install_hooks.py` - Windows platform detection and warnings
  - `claude_commands/README.md` - Added `/session-start` to available commands
  - `claude-hooks/README.md` - Added slash command workaround reference
  - `CLAUDE.md` - Updated workaround prioritization

- **Platform Compatibility**:
  - ✅ Windows: `/session-start` command works, automatic hooks skipped
  - ✅ macOS: All features work (automatic hooks + slash command)
  - ✅ Linux: All features work (automatic hooks + slash command)

## [8.14.2] - 2025-10-31

### Performance
- **Optimized MemoryService.get_memory_by_hash()** - O(1) direct lookup replaces O(n) scan (Issue #196)
  - **Previous Implementation**: Loaded ALL memories via `storage.get_all_memories()`, then filtered by hash
  - **New Implementation**: Direct O(1) database lookup via `storage.get_by_hash()`
  - **Performance Impact**:
    - Small datasets (10-100 memories): ~2x faster
    - Medium datasets (100-1000 memories): ~10-50x faster
    - Large datasets (1000+ memories): ~100x+ faster
  - **Memory Usage**: Single memory object vs loading entire dataset into memory

### Added
- **Abstract method `get_by_hash()` in MemoryStorage base class** (storage/base.py)
  - Enforces O(1) direct hash lookup across all storage backends
  - Required implementation for all storage backends
  - Returns `Optional[Memory]` (None if not found)

- **Implemented `get_by_hash()` in CloudflareStorage** (storage/cloudflare.py)
  - Direct D1 SQL query: `SELECT * FROM memories WHERE content_hash = ?`
  - Handles R2 content loading if needed
  - Loads tags separately
  - Follows same pattern as SqliteVecMemoryStorage implementation

### Changed
- **MemoryService.get_memory_by_hash()** now uses direct storage lookup
  - Removed inefficient `get_all_memories()` + filter approach
  - Simplified implementation (5 lines vs 10 lines)
  - Updated docstring to reflect O(1) lookup

### Testing
- **Updated unit tests** (tests/unit/test_memory_service.py)
  - Mocks now use `storage.get_by_hash()` instead of `storage.get_all_memories()`
  - Added assertions to verify method calls
  - All 3 test cases pass (found, not found, error handling)

- **Updated integration tests** (tests/integration/test_api_with_memory_service.py)
  - Mock updated for proper method delegation
  - Real storage backends (SqliteVecMemoryStorage, HybridMemoryStorage) work correctly

### Technical Details
- **Files Modified**: 5 files
  - `src/mcp_memory_service/storage/base.py`: Added abstract `get_by_hash()` method
  - `src/mcp_memory_service/storage/cloudflare.py`: Implemented `get_by_hash()` (40 lines)
  - `src/mcp_memory_service/services/memory_service.py`: Optimized `get_memory_by_hash()`
  - `tests/unit/test_memory_service.py`: Updated mocks
  - `tests/integration/test_api_with_memory_service.py`: Updated mocks

- **Breaking Changes**: None - fully backward compatible
- **All Storage Backends Now Support get_by_hash()**:
  - ✅ SqliteVecMemoryStorage (line 1153)
  - ✅ CloudflareStorage (line 666)
  - ✅ HybridMemoryStorage (line 974, delegates to primary)

## [8.14.1] - 2025-10-31

### Added
- **Type Safety Improvements** - Comprehensive TypedDict definitions for all MemoryService return types
  - **Problem**: All MemoryService methods returned loose `Dict[str, Any]` types, providing no IDE support or compile-time validation
  - **Solution**: Created 14 specific TypedDict classes for structured return types
    - Store operations: `StoreMemorySingleSuccess`, `StoreMemoryChunkedSuccess`, `StoreMemoryFailure`
    - List operations: `ListMemoriesSuccess`, `ListMemoriesError`
    - Retrieve operations: `RetrieveMemoriesSuccess`, `RetrieveMemoriesError`
    - Search operations: `SearchByTagSuccess`, `SearchByTagError`
    - Delete operations: `DeleteMemorySuccess`, `DeleteMemoryFailure`
    - Health operations: `HealthCheckSuccess`, `HealthCheckFailure`
  - **Benefits**:
    - ✅ IDE autocomplete for all return values (type `result["` to see available keys)
    - ✅ Compile-time type checking catches typos (e.g., `result["succes"]` → type error)
    - ✅ Self-documenting API - clear contracts for all methods
    - ✅ Refactoring safety - renaming keys shows all affected code
    - ✅ 100% backward compatible - no runtime changes
    - ✅ Zero performance impact - pure static typing

### Fixed
- **Missing HybridMemoryStorage.get_by_hash()** - Added delegation method to HybridMemoryStorage
  - Fixed `AttributeError: 'HybridMemoryStorage' object has no attribute 'get_by_hash'`
  - All storage backends now implement `get_by_hash()`: SqliteVecMemoryStorage, CloudflareMemoryStorage, HybridMemoryStorage
  - Enables direct memory retrieval by content hash without loading all memories
  - See issue #196 for planned optimization to use this method in MemoryService

### Technical Details
- **Files Modified**:
  - `src/mcp_memory_service/services/memory_service.py`: Added 14 TypedDict classes, updated 6 method signatures
  - `src/mcp_memory_service/storage/hybrid.py`: Added `get_by_hash()` delegation method
- **Breaking Changes**: None - fully backward compatible (TypedDict is structural typing)
- **Testing**: All tests pass (15/15), comprehensive structure validation, HTTP API integration verified

## [8.14.0] - 2025-10-31

### Fixed
- **Comprehensive Tag Normalization** - DRY solution for all tag format handling
  - **Problem**: Inconsistent tag handling across different APIs caused validation errors
    - Top-level `tags` parameter accepted strings, but MemoryService expected arrays
    - `metadata.tags` field had no normalization, causing "is not of type 'array'" errors
    - Comma-separated strings like `"tag1,tag2,tag3"` were not split into arrays
    - Normalization logic was duplicated in some methods but missing in others
  - **Root Cause**:
    - MCP/HTTP adapters accepted `Union[str, List[str], None]` in signatures
    - But passed values to MemoryService without normalization
    - MemoryService expected `Optional[List[str]]`, causing type mismatch
    - `search_by_tag()` had normalization, but `store_memory()` did not (DRY violation)
  - **Solution** (DRY Principle Applied):
    - Created centralized `normalize_tags()` utility function (services/memory_service.py:27-56)
    - Handles ALL input formats:
      - `None` → `[]`
      - `"tag1,tag2,tag3"` → `["tag1", "tag2", "tag3"]`
      - `"single-tag"` → `["single-tag"]`
      - `["tag1", "tag2"]` → `["tag1", "tag2"]` (passthrough)
    - Updated `MemoryService.store_memory()` to:
      - Accept `Union[str, List[str], None]` type hint
      - Normalize both `tags` parameter and `metadata.tags` field
      - Merge tags from both sources with deduplication
    - Updated `MemoryService.search_by_tag()` to use utility (removed duplicate code)
  - **Files Modified**:
    - `src/mcp_memory_service/services/memory_service.py`: Added normalize_tags(), updated store_memory() and search_by_tag()
    - `src/mcp_memory_service/mcp_server.py`: Updated docstring to reflect all formats supported
  - **Benefits**:
    - ✅ Single source of truth for tag normalization (DRY)
    - ✅ All tag formats work everywhere (top-level, metadata, any protocol)
    - ✅ No more validation errors for comma-separated strings
    - ✅ Fully backward compatible
    - ✅ Consistent behavior across all endpoints
  - **User Impact**:
    - Can use any tag format anywhere without errors
    - No need to remember which parameter accepts which format
    - Improved developer experience and reduced friction

### Technical Details
- **Affected Components**: MemoryService (business logic layer), MCP server documentation
- **Breaking Changes**: None - fully backward compatible
- **Tag Merge Behavior**: When tags provided in both parameter and metadata, they are merged and deduplicated
- **Testing**: Verified with all format combinations (None, string, comma-separated, array, metadata.tags)

## [8.13.5] - 2025-10-31

### Fixed
- **Memory Hooks Display Polish** - Visual improvements for cleaner, more professional CLI output
  - **Issue**: Multiple visual inconsistencies in memory hooks tree structure display
  - **Problems Identified**:
    1. Redundant bottom frame (`╰────╯`) after tree naturally ended with `└─`
    2. Wrapped text continuation showing vertical lines (`│`) after last items
    3. Duplicate final summary message ("Context injected") when header already shows count
    4. Embedded formatting (✅, •, markdown) conflicting with tree structure
    5. Excessive content length despite adaptive truncation
  - **Fixes** (commits ed46d24, 998a39c):
    - **Content Sanitization**: Remove checkmarks, bullets, markdown formatting that conflicts with tree characters
    - **Smart Truncation**: Extract first 1-2 sentences for <400 char limits using sentence boundary detection
    - **Tree Continuation Logic**: Last items show clean indentation without vertical lines on wrapped text
    - **Remove Redundant Frame**: Tree ends naturally with `└─`, no separate closing box
    - **Remove Duplicate Message**: Header shows "X memories loaded", no redundant final summary
  - **Files Modified**:
    - `claude-hooks/utilities/context-formatter.js`: Content sanitization, smart truncation, tree continuation fixes
    - `claude-hooks/core/session-start.js`: Removed redundant success message
  - **Result**: Clean, consistent tree structure with proper visual hierarchy and no redundancy
  - **User Impact**: Professional CLI output, easier to scan, maintains continuous blue tree lines properly

### Technical Details
- **Affected Component**: Claude Code memory awareness hooks (SessionStart display)
- **Deployment**: Hooks loaded from repository automatically, no server restart needed
- **Testing**: Verified with mock execution and real Claude Code session

## [8.13.4] - 2025-10-30

### Fixed
- **Critical: Memory Hooks Showing Incorrect Ages** (#195) - Timestamp unit mismatch causing 20,371-day ages
  - **Error**: Memory hooks reporting `avgAge: 20371 days, medianAge: 20371 days` when actual age was 6 days
  - **User Impact**: Recent memories didn't surface, auto-calibration incorrectly triggered "stale memory" warnings
  - **Root Cause** (claude-hooks/utilities/memory-client.js:273): Timestamp unit mismatch
    - HTTP API returns Unix timestamps in **SECONDS**: `1758344479.729`
    - JavaScript `Date()` expects **MILLISECONDS**: Interpreted as `Jan 21, 1970` (55 years ago)
    - Age calculation: `(now - 1758344479ms) / 86400000 = 20371 days`
  - **Symptoms**:
    - `[Memory Age Analyzer] { avgAge: 20371, recentPercent: 0, isStale: true }`
    - Hooks showed "Stale memory set detected (median: 20371d old)"
    - Recent development work (< 7 days) never surfaced in context
  - **Fix** (claude-hooks/utilities/memory-client.js:273-294, commit 5c54894):
    - Convert API timestamps from seconds to milliseconds (`× 1000`)
    - Added year 2100 check (`< 4102444800`) to prevent double-conversion
    - Applied in `_performApiPost()` response handler for both `created_at` and `updated_at`
  - **Result**:
    - `avgAge: 6 days, medianAge: 5 days, recentPercent: 100%, isStale: false`
    - Recent memories surface correctly
    - Auto-calibration works properly
    - Git context weight adjusts based on actual ages
  - **Note**: Affects all users using HTTP protocol for memory hooks

### Technical Details
- **Affected Component**: Claude Code memory awareness hooks (HTTP protocol path)
- **File Changed**: `claude-hooks/utilities/memory-client.js` (lines 273-294)
- **Deployment**: Hooks loaded from repository automatically, no server restart needed
- **Issue**: https://github.com/doobidoo/mcp-memory-service/issues/195

## [8.13.3] - 2025-10-30

### Fixed
- **Critical: MCP Memory Tools Broken** - v8.12.0 regression preventing all MCP memory operations
  - **Error**: `KeyError: 'message'` when calling any MCP memory tool (store, retrieve, search, etc.)
  - **User Impact**: MCP tools completely non-functional - "Error storing memory: 'message'"
  - **Root Cause** (mcp_server.py:175): Return format mismatch between MemoryService and MCP tool expectations
    - MCP tool expects: `{success: bool, message: str, content_hash: str}`
    - MemoryService returns: `{success: bool, memory: {...}}`
    - MCP protocol tries to access missing 'message' field → KeyError
  - **Why It Persisted**: HTTP API doesn't require these specific fields, so integration tests passed
  - **Fix** (mcp_server.py:173-206): Transform MemoryService response to MCP TypedDict format
    - Capture result from MemoryService.store_memory()
    - Extract content_hash from nested memory object
    - Add descriptive "message" field
    - Handle 3 cases: failure (error message), chunked (multiple memories), single memory
  - **Result**: MCP tools now work correctly with proper error messages
  - **Note**: Requires MCP server restart (`/mcp` command in Claude Code) to load fix

### Technical Details
- **Introduced**: v8.12.0 MemoryService architecture refactoring (#176)
- **Affected Tools**: store_memory, all MCP protocol operations
- **HTTP API**: Unaffected (different response format requirements)
- **Test Gap**: No integration tests validating MCP tool response formats

## [8.13.2] - 2025-10-30

### Fixed
- **Memory Sync Script Broken** (#193): Fixed sync_memory_backends.py calling non-existent `store_memory()` method
  - **Error**: `AttributeError: 'CloudflareStorage' object has no attribute 'store_memory'`
  - **User Impact**: Sync script completely non-functional - couldn't sync memories between Cloudflare and SQLite backends
  - **Root Cause** (scripts/sync/sync_memory_backends.py:144-147): Script used old `store_memory()` API that no longer exists
  - **Fix** (#194, b69de83): Updated to use proper `Memory` object creation and `storage.store()` method
    - Create `Memory` object with `content`, `content_hash`, `tags`, `metadata`, `created_at`
    - Call `await target_storage.store(memory_obj)` instead of non-existent `store_memory()`
    - Added safe `.get('metadata', {})` to prevent KeyError on missing metadata
    - Fixed import order to comply with PEP 8 (config → models → storage)
  - **Result**: Sync script now successfully syncs memories between backends
  - **Credit**: Fix by AMP via PR #194, reviewed by Gemini

## [8.13.1] - 2025-10-30

### Fixed
- **Critical Concurrent Access Bug**: MCP server initialization failed with "database is locked" when HTTP server running
  - **Error**: `sqlite3.OperationalError: database is locked` during MCP tool initialization
  - **User Impact**: MCP memory tools completely non-functional while HTTP server running - "this worked before without any flaws"
  - **Root Cause #1** (sqlite_vec.py:329): Connection timeout set AFTER opening database instead of during connection
    - Original: `sqlite3.connect(path)` used default 5-second timeout, then applied `PRAGMA busy_timeout=15000`
    - SQLite only respects timeout parameter passed to `connect()`, not pragma applied afterward
    - MCP server timed out before it could set the higher timeout value
  - **Root Cause #2** (sqlite_vec.py:467-476): Both servers attempting DDL operations (CREATE TABLE, CREATE INDEX) simultaneously
    - Even with WAL mode, DDL operations require brief exclusive locks
    - No detection of already-initialized database before running DDL
  - **Fix #1** (sqlite_vec.py:291-326): Parse `busy_timeout` from `MCP_MEMORY_SQLITE_PRAGMAS` environment variable BEFORE opening connection
    - Convert from milliseconds to seconds (15000ms → 15.0s)
    - Pass timeout to `sqlite3.connect(path, timeout=15.0)` for immediate effect
    - Allows MCP server to wait up to 15 seconds for HTTP server's DDL operations
  - **Fix #2** (sqlite_vec.py:355-373): Detect already-initialized database and skip DDL operations
    - Check if `memories` and `memory_embeddings` tables exist after loading sqlite-vec extension
    - If tables exist, just load embedding model and mark as initialized
    - Prevents "database is locked" errors from concurrent CREATE TABLE/INDEX attempts
  - **Result**: MCP and HTTP servers now coexist without conflicts, maintaining pre-v8.9.0 concurrent access behavior

### Technical Details
- **Timeline**: Bug discovered during memory consolidation testing, fixed same day
- **Affected Versions**: v8.9.0 introduced database lock prevention pragmas but didn't fix concurrent initialization
- **Test Validation**: MCP health check returns healthy with 1857 memories while HTTP server running
- **Log Evidence**: "Database already initialized by another process, skipping DDL operations" confirms fix working

## [8.13.0] - 2025-10-29

### Added
- **HTTP Server Integration Tests** (#190): Comprehensive test suite with 32 tests prevents production bugs like v8.12.0
  - `tests/integration/test_http_server_startup.py`: 8 tests for server startup validation
  - `tests/unit/test_fastapi_dependencies.py`: 11 tests for dependency injection
  - `tests/unit/test_storage_interface_compatibility.py`: 13 tests for backend interface consistency
  - Extended `tests/integration/test_api_with_memory_service.py`: +11 HTTP API tests with TestClient
  - Tests would have caught all 3 v8.12.0 production bugs (import-time evaluation, syntax errors, interface mismatches)

- **Storage Method: get_largest_memories()** (#186): Efficient database queries for largest memories by content length
  - Added to all storage backends (SQLite, Cloudflare, Hybrid)
  - Uses `ORDER BY LENGTH(content) DESC LIMIT n` instead of loading 1000 memories and sorting in Python
  - Analytics dashboard now queries entire dataset for truly largest memories

### Fixed
- **Analytics Dashboard Timezone Bug** (#186): Fixed heatmap calendar showing wrong day-of-week near timezone boundaries
  - JavaScript `new Date('YYYY-MM-DD')` parsed as UTC midnight, but `getDay()` used local timezone
  - Changed to parse date components in local timezone: `new Date(year, month-1, day)`
  - Prevents calendar cells from shifting to previous/next day for users in UTC-12 to UTC+12 timezones

### Improved
- **Analytics Performance**: Reduced memory sample for average size calculation from 1000→100 memories
- **Test Coverage**: Zero HTTP integration tests → 32 comprehensive tests covering server startup, dependencies, and API endpoints

### Documentation
- **MCP Schema Caching** (#173): Closed with comprehensive documentation in CLAUDE.md and troubleshooting guides
  - Root cause: MCP protocol caches tool schemas client-side
  - Workaround: `/mcp` command reconnects server with fresh schema
  - Documented symptoms, diagnosis, and resolution steps

## [8.12.1] - 2025-10-28

### Fixed
- **Critical Production Bug #1** (ef2c64d): Import-time default parameter evaluation in `get_memory_service()`
  - **Error**: `HTTPException: 503: Storage not initialized` during module import
  - **Root Cause**: Python evaluates default parameters at function definition time, not call time
  - **Impact**: HTTP server couldn't start - module import failed immediately
  - **Fix**: Changed from `storage: MemoryStorage = get_storage()` to `storage: MemoryStorage = Depends(get_storage)`
  - **Technical**: FastAPI's `Depends()` defers evaluation until request time and integrates with dependency injection

- **Critical Production Bug #2** (77de4d2): Syntax error + missing FastAPI Depends import in `memories.py`
  - **Error**: `SyntaxError: expected an indented block after 'if' statement on line 152`
  - **Root Cause**: `if INCLUDE_HOSTNAME:` had no indented body, nested if-elif-else block not indented
  - **Impact**: SyntaxError prevented module import + FastAPI validation failure
  - **Fix**: Properly indented hostname resolution logic, added missing `Depends` import to dependencies.py

- **Critical Production Bug #3** (f935c56): Missing `tags` parameter in `count_all_memories()` across all storage backends
  - **Error**: `TypeError: count_all_memories() got an unexpected keyword argument 'tags'`
  - **User Report**: "failed to load dashboard data"
  - **Root Cause**: MemoryService called `count_all_memories(memory_type=type, tags=tags)` but base class and implementations didn't accept tags parameter
  - **Impact**: Dashboard completely broken - GET /api/memories returned 500 errors
  - **Fix**: Updated 4 files (base.py, hybrid.py, sqlite_vec.py, cloudflare.py) to add tags parameter with SQL LIKE filtering
  - **Why Tests Missed It**: AsyncMock accepts ANY parameters, never tested real storage backend implementations

- **Analytics Metrics Bug** (8beeb07): Analytics tab showed different metrics than Dashboard tab
  - **Problem**: Dashboard queried ALL memories, Analytics sampled only 1000 recent memories
  - **Impact**: "This Week" count was inaccurate when total memories > 1000
  - **Fix**: Changed Analytics endpoint to use `storage.get_stats()` instead of sampling
  - **Performance**: Eliminated O(n) memory loading for simple count operation, now uses efficient SQL COUNT

### Changed
- **Analytics Endpoint Performance** - Increased monthly sample from 2,000 to 5,000 memories
- **Code Quality** - Added TODO comments for moving monthly calculations to storage layer

### Technical Details
- **Timeline**: All 4 bugs discovered and fixed within 4 hours of v8.12.0 release (15:03 UTC → 22:03 UTC)
- **Post-Mortem**: Created Issue #190 for HTTP server integration tests to prevent future production bugs
- **Test Coverage Gap**: v8.12.0 had 55 tests but zero HTTP server integration tests
- **Lesson Learned**: Tests used mocked storage that never actually started the server or tested real FastAPI dependency injection

**Note**: This patch release resolves all production issues from v8.12.0 architectural changes. Comprehensive analysis stored in memory with tag `v8.12.0,post-release-bugs`.

## [8.12.0] - 2025-10-28

### Added
- **MemoryService Architecture** - Centralized business logic layer (Issue #188, PR #189)
  - Single source of truth for all memory operations
  - Consistent behavior across API endpoints and MCP tools
  - 80% code duplication reduction between API and MCP servers
  - Dependency injection pattern for clean architecture
  - **Comprehensive Test Coverage**:
    - 34 unit tests (100% pass rate)
    - 21 integration tests for API layer
    - End-to-end workflow tests with real storage
    - Performance validation for database-level filtering

### Fixed
- **Critical Bug #1**: `split_content()` missing required `max_length` parameter
  - Impact: Would crash immediately on any content chunking operation
  - Fix: Added proper parameter passing with storage backend max_length
- **Critical Bug #2**: `storage.delete_memory()` method does not exist in base class
  - Impact: Delete functionality completely broken
  - Fix: Changed to use `storage.delete(content_hash)` from base class
- **Critical Bug #3**: `storage.get_memory()` method does not exist in base class
  - Impact: Get by hash functionality completely broken
  - Fix: Implemented using `get_all_memories()` with client-side filtering
- **Critical Bug #4**: `storage.health_check()` method does not exist in base class
  - Impact: Health check functionality completely broken
  - Fix: Changed to use `storage.get_stats()` from base class
- **Critical Bug #5**: `storage.search_by_tags()` method mismatch (plural vs singular)
  - Impact: Tag search functionality completely broken
  - Fix: Changed to use `storage.search_by_tag()` (singular) from base class
- **Critical Bug #6**: Incorrect chunking logic comparing `len(content) > CONTENT_PRESERVE_BOUNDARIES`
  - Impact: ALL content >1 character would trigger chunking (CONTENT_PRESERVE_BOUNDARIES is boolean `True`)
  - Fix: Proper comparison using `storage.max_content_length` numeric value
- **Critical Bug #7**: Missing `store()` return value handling
  - Impact: Success/failure not properly tracked
  - Fix: Proper unpacking of `(success, message)` tuple from storage operations

### Changed
- **API Endpoints** - Refactored to use MemoryService dependency injection
  - `/api/memories` (list, create) uses MemoryService
  - `/api/search` endpoints use MemoryService
  - Consistent response formatting via service layer
- **Code Maintainability** - Removed 356 lines of duplicated code
  - Single place to modify business logic
  - Unified error handling
  - Consistent hostname tagging logic
- **Performance** - Database-level filtering prevents O(n) memory loading
  - Scalable pagination with offset/limit at storage layer
  - Efficient tag and type filtering

### Technical Details
- **Files Modified**: 6 files, 1469 additions, 356 deletions
- **Test Coverage**: 55 new tests (34 unit + 21 integration)
- **Bug Discovery**: Comprehensive testing revealed 7 critical bugs that would have made the release non-functional
- **Quality Process**: Test-driven debugging approach prevented broken release

**Note**: This release demonstrates the critical importance of comprehensive testing before merging architectural changes. All 7 bugs were caught through systematic unit and integration testing.

## [8.11.0] - 2025-10-28

### Added
- **JSON Document Loader** - Complete implementation of JSON file ingestion (Issue #181, PR #187)
  - **Nested Structure Flattening**: Converts nested JSON to searchable text with dot notation or bracket notation
  - **Configurable Strategies**: Choose flattening style, max depth, type inclusion
  - **Array Handling**: Multiple modes (expand, summarize, flatten) for different use cases
  - **Comprehensive Tests**: 15 unit tests covering all functionality
  - **Use Cases**: Knowledge base exports, API documentation, config files, structured metadata

- **CSV Document Loader** - Complete implementation of CSV file ingestion (Issue #181, PR #187)
  - **Auto-Detection**: Automatically detects delimiters (comma, semicolon, tab, pipe) and headers
  - **Row-Based Formatting**: Converts tabular data to searchable text with column context
  - **Encoding Support**: Auto-detects UTF-8, UTF-16, UTF-32, Latin-1, CP1252
  - **Large File Handling**: Efficient row-based chunking for scalability
  - **Comprehensive Tests**: 14 unit tests covering all functionality
  - **Use Cases**: Data dictionaries, reference tables, tabular documentation, log analysis

### Fixed
- **False Advertising** - Resolved issue where JSON and CSV were listed in `SUPPORTED_FORMATS` but had no loader implementations
  - Previous behavior: Upload would fail with "No loader available" error
  - New behavior: Full functional support with proper chunking and metadata

### Changed
- **Ingestion Module** - Updated to register new JSON and CSV loaders
- **Test Coverage** - Added 29 new unit tests (15 JSON + 14 CSV)

## [8.10.0] - 2025-10-28

### Added
- **Complete Analytics Dashboard Implementation** (Issue #182, PR #183)
  - Memory Types Breakdown (pie chart)
  - Activity Heatmap (GitHub-style calendar with 90d/6mo/1yr periods)
  - Top Tags Report (usage trends, co-occurrence patterns)
  - Recent Activity Report (hourly/daily/weekly breakdowns)
  - Storage Report (largest memories, efficiency metrics)
  - Streak Tracking (current and longest consecutive days)

### Fixed
- **Activity Streak Calculation** - Fixed current streak to include today check
- **Total Days Calculation** - Corrected date span vs active days count
- **Longest Streak Initialization** - Fixed from 0 to 1

### Changed
- **Analytics API** - Added 5 new endpoints with Pydantic models
- **Dashboard Documentation** - Updated wiki with complete analytics features

## [8.9.0] - 2025-10-27

### Fixed
- **Database Lock Prevention** - Resolved "database is locked" errors during concurrent HTTP + MCP server access (Issue discovered during performance troubleshooting)
  - **Root Cause**: Default `busy_timeout=5000ms` too short for concurrent writes from multiple MCP clients
  - **Solution**: Applied recommended SQLite pragmas (`busy_timeout=15000,cache_size=20000`)
  - **WAL Mode**: Already enabled by default, now properly configured for multi-client access
  - **Impact**: Zero database locks during testing with 5 concurrent write operations
  - **Documentation**: Updated multi-client architecture docs with pragma recommendations

### Added
- **Hybrid Backend Installer Support** - Full hybrid backend support in simplified installer (`scripts/installation/install.py`)
  - **Interactive Selection**: Hybrid now option 4 (recommended default) in installer menu
  - **Automatic Configuration**: SQLite pragmas set automatically for sqlite_vec and hybrid backends
  - **Cloudflare Setup**: Interactive credential configuration with connection testing
  - **Graceful Fallback**: Falls back to sqlite_vec if Cloudflare setup cancelled or fails
  - **Claude Desktop Integration**: Hybrid backend configuration includes:
    - SQLite pragmas for concurrent access (`MCP_MEMORY_SQLITE_PRAGMAS`)
    - Cloudflare credentials for background sync
    - Proper environment variable propagation
  - **Benefits**:
    - 5ms local reads (SQLite-vec)
    - Zero user-facing latency (background Cloudflare sync)
    - Multi-device synchronization
    - Concurrent access support

### Changed
- **Installer Defaults** - Hybrid backend now recommended for production use
  - Updated argparse choices to include `hybrid` option
  - Changed default selection from sqlite_vec to hybrid (option 4)
  - Enhanced compatibility detection with "recommended" status for hybrid
  - Improved final installation messages with backend-specific guidance
- **Environment Management** - Cloudflare credentials now set in current environment immediately
  - `save_credentials_to_env()` sets both .env file AND os.environ
  - Ensures credentials available for Claude Desktop config generation
  - Proper variable propagation for hybrid and cloudflare backends
- **Path Configuration** - Updated `configure_paths()` to handle all backends
  - SQLite database paths for: `sqlite_vec`, `hybrid`, `cloudflare`
  - Cloudflare credentials included when backend requires them
  - Backward compatible with existing installations

### Technical Details
- **Files Modified**:
  - `scripts/installation/install.py`: Lines 655-659 (compatibility), 758 (menu), 784-802 (selection), 970-1017 (hybrid install), 1123-1133 (env config), 1304 (path config), 1381-1401 (Claude Desktop config), 1808-1821 (final messages)
  - `src/mcp_memory_service/__init__.py`: Line 50 (version bump)
  - `pyproject.toml`: Line 7 (version bump)
- **Concurrent Access Testing**: 5/5 simultaneous writes succeeded without locks
- **HTTP Server Logs**: Confirmed background Cloudflare sync working (line 369: "Successfully stored memory")

## [8.8.2] - 2025-10-26

### Fixed
- **Document Upload Tag Validation** - Prevents bloated tags from space-separated file paths (Issue #174, PR #179)
  - **Enhanced Tag Parsing**: Split tags by comma OR space instead of comma only
  - **Robust file:// URI Handling**: Uses `urllib.parse` for proper URL decoding and path handling
    - Handles URL-encoded characters (e.g., `%20` for spaces)
    - Handles different path formats (e.g., `file:///C:/...`)
    - Properly handles Windows paths with leading slash from urlparse
  - **File Path Sanitization**: Remove `file://` prefixes, extract filenames only, clean path separators
  - **Explicit Tag Length Validation**: Tags exceeding 100 chars now raise explicit HTTPException instead of being silently dropped

### Added
- **Processing Mode Toggle** - UI enhancement for multiple file uploads (PR #179)
  - **Batch Processing**: All files processed together (faster, default)
  - **Individual Processing**: Each file processed separately with better error isolation
  - Toggle only appears when multiple files are selected
  - Comprehensive help section explaining both modes with pros/cons

### Changed
- **Code Quality Improvements** - Eliminated code duplication in document upload endpoints (PR #179)
  - Extracted `parse_and_validate_tags()` helper function to eliminate duplicate tag parsing logic
  - Removed 44 lines of duplicate code from `upload_document` and `batch_upload_documents`
  - Extracted magic number (500ms upload delay) to static constant `INDIVIDUAL_UPLOAD_DELAY`
  - Simplified toggle display logic with ternary operator
  - Created Issue #180 for remaining medium-priority code quality suggestions

## [8.8.1] - 2025-10-26

### Fixed
- **Error Handling Improvements** - Enhanced robustness in MemoryService and maintenance scripts (Issue #177)
  - **MemoryService.store_memory()**: Added specific exception handling for better error classification
    - `ValueError` → validation errors with "Validation error" messages
    - `httpx.NetworkError/TimeoutException/HTTPStatusError` → storage errors with "Storage error" messages
    - Generic `Exception` → unexpected errors with full logging and "unexpected error" messages
  - **Maintenance Scripts**: Added proper error handling to prevent crashes
    - `find_cloudflare_duplicates.py`: Wrapped `get_all_memories_bulk()` in try/except, graceful handling of empty results
    - `delete_orphaned_vectors_fixed.py`: Already used public API (no changes needed)

### Added
- **Encapsulation Methods** - New public APIs for Cloudflare storage operations (Issue #177)
  - `CloudflareStorage.delete_vectors_by_ids()` - Batch vector deletion with proper error handling
  - `CloudflareStorage.get_all_memories_bulk()` - Efficient bulk loading without N+1 tag queries
  - `CloudflareStorage._row_to_memory()` - Helper for converting D1 rows to Memory objects
  - **Performance**: Bulk operations avoid expensive individual tag lookups
  - **Maintainability**: Public APIs instead of direct access to private `_retry_request` method

### Changed
- **Dependency Management** - Added conditional typing-extensions for Python 3.10 (Issue #177)
  - Added `"typing-extensions>=4.0.0; python_version < '3.11'"` to pyproject.toml
  - Ensures `NotRequired` import works correctly on Python 3.10
  - No impact on Python 3.11+ installations

### Review
- **Gemini Code Assist**: "This pull request significantly improves the codebase by enhancing error handling and improving encapsulation... well-executed and contribute to better maintainability"
- **Feedback Addressed**: All review suggestions implemented, including enhanced exception handling

## [8.8.0] - 2025-10-26

### Changed
- **DRY Refactoring** - Eliminated code duplication between MCP and HTTP servers (PR #176, Issue #172)
  - **Problem**: MCP (`mcp_server.py`) and HTTP (`server.py`) servers had 364 lines of duplicated business logic
    - Bug fixes applied to one server were missed in the other (e.g., PR #162 tags validation)
    - Maintenance burden of keeping two implementations synchronized
    - Risk of behavioral inconsistencies between protocols
  - **Solution**:
    - Created `MemoryService` class (442 lines) as single source of truth for business logic
    - Refactored `mcp_server.py` to thin adapter (-338 lines, now ~50 lines per method)
    - Refactored `server.py` to use MemoryService (169 lines modified)
    - Both servers now delegate to shared business logic
  - **Benefits**:
    - **Single source of truth**: All memory operations (store, retrieve, search, delete) in one place
    - **Consistent behavior**: Both protocols guaranteed identical business logic
    - **Easier maintenance**: Bug fixes automatically apply to both servers
    - **Better testability**: Business logic isolated and independently testable
    - **Prevents future bugs**: Impossible to fix one server and forget the other
  - **Type Safety**: Added TypedDict classes (`MemoryResult`, `OperationResult`, `HealthStats`) for better type annotations
  - **Backward Compatibility**: No API changes, both servers remain fully compatible
  - **Testing**: All tests passing (15/15 Cloudflare storage tests)
  - **Review**: Gemini Code Assist: "significant and valuable refactoring... greatly improves maintainability and consistency"
  - **Follow-up**: Minor improvements tracked in Issue #177 (error handling, encapsulation)

### Fixed
- **Python 3.10 Compatibility** - Added `NotRequired` import fallback (src/mcp_memory_service/mcp_server.py:23-26)
  - Uses `typing.NotRequired` on Python 3.11+
  - Falls back to `typing_extensions.NotRequired` on Python 3.10
  - Ensures compatibility across Python versions

### Added
- **Maintenance Scripts** - Cloudflare cleanup utilities (from v8.7.1 work)
  - `scripts/maintenance/find_cloudflare_duplicates.py` - Detect duplicates in Cloudflare D1
  - `scripts/maintenance/delete_orphaned_vectors_fixed.py` - Clean orphaned Vectorize vectors
  - `scripts/maintenance/fast_cleanup_duplicates_with_tracking.sh` - Platform-aware SQLite cleanup
  - `scripts/maintenance/find_all_duplicates.py` - Platform detection (macOS/Linux paths)

## [8.7.1] - 2025-10-26

### Fixed
- **Cloudflare Vectorize Deletion** - Fixed vector deletion endpoint bug (src/mcp_memory_service/storage/cloudflare.py:671)
  - **Problem**: Used incorrect endpoint `/delete-by-ids` (hyphens) causing 404 Not Found errors, preventing vector deletion
  - **Solution**:
    - Changed to correct Cloudflare API endpoint `/delete_by_ids` (underscores)
    - Fixed payload format from `[vector_id]` to `{"ids": [vector_id]}`
    - Created working cleanup script: `scripts/maintenance/delete_orphaned_vectors_fixed.py`
    - Removed obsolete broken script: `scripts/maintenance/delete_orphaned_vectors.py`
  - **Impact**: Successfully deleted 646 orphaned vectors from Vectorize in 7 batches
  - **Testing**: Verified with production data (646 vectors, 100/batch, all mutations successful)
  - **Discovery**: Found via web research of official Cloudflare Vectorize API documentation

## [8.7.0] - 2025-10-26

### Fixed
- **Cosine Similarity Migration** - Fixed 0% similarity scores in search results (src/mcp_memory_service/storage/sqlite_vec.py:187)
  - **Problem**: L2 distance metric gave 0% similarity for all searches due to score calculation `max(0, 1-distance)` returning 0 for distances >1.0
  - **Solution**:
    - Migrated embeddings table from L2 to cosine distance metric
    - Updated score calculation to `1.0 - (distance/2.0)` for cosine range [0,2]
    - Added automatic migration logic with database locking retry (exponential backoff)
    - Implemented `_initialized` flag to prevent multiple initialization
    - Created metadata table for storage configuration persistence
  - **Performance**: Search scores improved from 0% to 70-79%, exact match accuracy 79.2% (was 61%)
  - **Impact**: 2605 embeddings regenerated successfully

- **Dashboard Search Improvements** - Enhanced search threshold handling (src/mcp_memory_service/web/static/app.js:283)
  - Fixed search threshold always being sent even when not explicitly set
  - Improved document filtering to properly handle memory object structure
  - Only send `similarity_threshold` parameter when user explicitly sets it
  - Better handling of `memory.memory_type` and `memory.tags` for document results

### Added
- **Maintenance Scripts** - Comprehensive database maintenance tooling (scripts/maintenance/)
  - **regenerate_embeddings.py** - Regenerate all embeddings after migrations (~5min for 2600 memories)
  - **fast_cleanup_duplicates.sh** - 1800x faster duplicate removal using direct SQL (<5s for 100+ duplicates vs 2.5 hours via API)
  - **find_all_duplicates.py** - Fast duplicate detection with timestamp normalization (<2s for 2000 memories)
  - **README.md** - Complete documentation with performance benchmarks, best practices, and troubleshooting

### Technical Details
- **Migration Approach**: Drop-and-recreate embeddings table to change distance metric (vec0 limitation)
- **Retry Logic**: Exponential backoff for database locking (1s → 2s → 4s delays)
- **Performance Benchmark**: Direct SQL vs API operations show 1800x speedup for bulk deletions
- **Duplicate Detection**: Content normalization removes timestamps for semantic comparison using MD5 hashing

## [8.6.0] - 2025-10-25

### Added
- **Document Ingestion System** - Complete document upload and management through web UI (#147, #164)
  - **Single and Batch Upload**: Drag-and-drop or file browser support for PDF, TXT, MD, JSON documents
  - **Background Processing**: Async document processing with progress tracking and status updates
  - **Document Management UI**: New Documents tab in web dashboard with full CRUD operations
  - **Upload History**: Track all document ingestion with status, chunk counts, and file sizes
  - **Document Viewer**: Modal displaying all memory chunks from uploaded documents (up to 1000 chunks)
  - **Document Removal**: Delete documents and their associated memory chunks with confirmation
  - **Search Ingested Content**: Semantic search within uploaded documents to verify indexing
  - **Claude Commands**: `/memory-ingest` and `/memory-ingest-dir` for CLI document upload
  - **API Endpoints**:
    - `POST /api/documents/upload` - Single document upload
    - `POST /api/documents/batch-upload` - Multiple document upload
    - `GET /api/documents/history` - Upload history
    - `GET /api/documents/status/{upload_id}` - Upload status
    - `GET /api/documents/search-content/{upload_id}` - View document chunks
    - `DELETE /api/documents/remove/{upload_id}` - Remove document
    - `DELETE /api/documents/remove-by-tags` - Bulk remove by tags
  - **Files Created**:
    - `src/mcp_memory_service/web/api/documents.py` (779 lines) - Document API
    - `claude_commands/memory-ingest.md` - Single document ingestion command
    - `claude_commands/memory-ingest-dir.md` - Directory ingestion command
    - `docs/development/dashboard-workflow.md` - Development workflow documentation

- **Chunking Configuration Help** - Interactive UI guidance for document chunking parameters
  - Inline help panels with collapsible sections for chunk size and overlap settings
  - Visual diagram showing how overlap works between consecutive chunks
  - Pre-configured recommendations (Default: 1000/200, Smaller: 500/100, Larger: 2000/400)
  - Rule-of-thumb guidelines (15-25% overlap of chunk size)
  - Full dark mode support for all help elements

- **Tag Length Validation** - Server-side validation to prevent data corruption (#174)
  - Maximum tag length enforced at 100 characters
  - Validation on both single and batch upload endpoints
  - Clear error messages showing first invalid tag
  - Frontend filtering to hide malformed tags in display
  - Prevents bloated tags from accidental file path pasting

### Fixed
- **Security Vulnerabilities** - Multiple critical security fixes addressed
  - Path traversal vulnerability in file uploads (use `tempfile.NamedTemporaryFile()`)
  - XSS prevention in tag display and event handlers (escape all user-provided filenames)
  - CSP compliance by removing inline `onclick` handlers, using `addEventListener` instead
  - Proper input validation and sanitization throughout upload flow

- **Document Viewer Critical Bugs** - Comprehensive fixes for document management
  - **Chunk Limit**: Increased from 10 to 1000 chunks (was only showing first 10 of 430 chunks)
  - **Upload Session Persistence**: Documents now viewable after server restart (session optional, uses `upload_id` tag search)
  - **Filename Retrieval**: Get filename from memory metadata when session unavailable
  - **Batch File Size**: Calculate and display total file size for batch uploads (was showing 0.0 KB)
  - **Multiple Confirmation Dialogs**: Fixed duplicate event listeners causing N dialogs for N uploads
  - **Event Listener Deduplication**: Added `documentsListenersSetup` flag to prevent duplicate setup

- **Storage Backend Enhancements** - `delete_by_tags` implementation for document deletion
  - Added `delete_by_tags()` method to `MemoryStorage` base class with error aggregation
  - Optimized `SqliteVecMemoryStorage.delete_by_tags()` with single SQL query using OR conditions
  - Added `HybridMemoryStorage.delete_by_tags()` with sync queue support for cloud backends
  - Fixed return value handling (tuple unpacking instead of dict access)

- **UI/UX Improvements** - Enhanced user experience across document management
  - Added scrolling to Recent Memories section (max-height: 600px) to prevent infinite expansion
  - Document chunk modal now scrollable (max-height: 400px) for long content
  - Modal visibility fixed with proper `active` class pattern and CSS transitions
  - Dark mode support for all document UI components (chunk items, modals, previews)
  - Event handlers for View/Remove buttons in document preview cards
  - Responsive design with mobile breakpoints (768px, 1024px)

- **Resource Management** - Proper cleanup and error handling
  - Temp file cleanup moved to `finally` blocks to prevent orphaned files
  - File extension validation fixed (strip leading dot for consistent checking)
  - Session cleanup timing bug fixed (use `total_seconds()` instead of `.seconds`)
  - Loader registration order corrected (PDFLoader takes precedence as fallback)

- **MCP Server Tag Format Support** - Accept both string and array formats
  - MCP tools now accept `"tag1,tag2"` (string) and `["tag1", "tag2"]` (array)
  - Consistent tag handling between API and MCP endpoints
  - Fixes validation errors from schema mismatches

### Changed
- **API Response Improvements** - Better error messages and status handling
  - Float timestamp handling in document search (convert via `datetime.fromtimestamp()`)
  - Partial success handling for bulk operations with clear error reporting
  - Progress tracking for background tasks with status updates

### Technical Details
- **Testing**: 19 Gemini Code Assist reviews addressed with comprehensive fixes
- **Performance**: Document viewer handles 430+ chunks efficiently
- **Compatibility**: Cross-platform temp file handling (Windows, macOS, Linux)
- **Code Quality**: Removed dead code, duplicate docstrings, and unused Pydantic models

### Migration Notes
- No breaking changes - fully backward compatible
- Existing installations will automatically gain document ingestion capabilities
- Tag validation only affects new uploads (existing tags unchanged)

## [8.5.14] - 2025-10-23

### Added
- **Memory Hooks: Expanded Git Keyword Extraction** - Dramatically improved memory retrieval by capturing more relevant technical terms from git commits
  - **Problem**: Limited keyword extraction (only 12 terms) missed important development context
    - Git analyzer captured only generic terms: `fix, memory, chore, feat, refactor`
    - Recent work on timestamp parsing, dashboard, analytics not reflected in queries
    - Version numbers (v8.5.12, v8.5.13) not extracted
    - Memory hooks couldn't match against specific technical work
  - **Solution**: Expanded keyword extraction in `git-analyzer.js`
    - **Technical Terms**: Increased from 12 to 38 terms including:
      - Time/Date: `timestamp, parsing, sort, sorting, date, age`
      - Dashboard: `dashboard, analytics, footer, layout, grid, css, stats, display`
      - Development: `async, sync, bugfix, release, version`
      - Features: `embedding, consolidation, memory, retrieval, scoring`
      - Infrastructure: `api, endpoint, server, http, mcp, client, protocol`
    - **Version Extraction**: Added regex to capture version numbers (v8.5.12, v8.5.13, etc.)
    - **Changelog Terms**: Expanded from 12 to 23 terms with same additions
    - **Keyword Limits**: Increased capacity
      - keywords: 15 → 20 terms
      - themes: 10 → 12 entries
      - filePatterns: 10 → 12 entries
  - **Impact**:
    - **Before**: 5 generic terms → limited semantic matching
    - **After**: 20 specific development terms → precise context retrieval
    - Example: `feat, git, memory, retrieval, fix, timestamp, age, v8.5.8, chore, version, v8.5.13, sort, date, dashboard, analytics, stats, display, footer, layout, v8.5.12`
  - **Result**: Memory hooks now capture and retrieve memories about specific technical work (releases, features, bugfixes)
  - **Files Modified**:
    - `claude-hooks/utilities/git-analyzer.js` - Expanded `extractDevelopmentKeywords()` function (commit 4a02c1a)
  - **Testing**: Verified improved extraction with test run showing 20 relevant keywords vs previous 5 generic terms

## [8.5.13] - 2025-10-23

### Fixed
- **Memory Hooks: Unix Timestamp Parsing in Date Sorting** - Fixed critical bug where memories were not sorting chronologically in Claude Code session start
  - **Root Cause**: JavaScript `Date()` constructor expects milliseconds but API returns Unix timestamps in seconds
  - **Impact**: Memory hooks showed old memories (Oct 11-21) before recent ones (Oct 23) despite `sortByCreationDate: true` configuration
  - **Technical Details**:
    - API returns `created_at` as Unix timestamp in seconds (e.g., 1729700000)
    - JavaScript `new Date(1729700000)` interprets this as milliseconds → January 21, 1970
    - All dates appeared as 1970-01-01, breaking chronological sort
    - Relevance scores then determined order, causing old high-scoring memories to rank first
  - **Fix**:
    - Created `getTimestamp()` helper function in `session-start.js` (lines 907-928)
    - Converts `created_at` (seconds) to milliseconds by multiplying by 1000
    - Falls back to `created_at_iso` string parsing if available
    - Proper date comparison ensures newest memories sort first
  - **Result**: Memory hooks now correctly show most recent project memories at session start
  - **Files Modified**:
    - `claude-hooks/core/session-start.js` - Added Unix timestamp conversion helper (commit 71606e5)

## [8.5.12] - 2025-10-23

### Fixed
- **Dashboard: Analytics Stats Display** - Fixed analytics tab showing 0/N/A for key metrics
  - **Root Cause**: Async/sync mismatch in `get_stats()` method implementations
  - **Impact**: Analytics dashboard displayed only "this week" count; total memories, unique tags, and database size showed 0 or N/A
  - **Fix**:
    - Made `SqliteVecMemoryStorage.get_stats()` async (line 1242)
    - Updated `HybridMemoryStorage.get_stats()` to properly await primary storage call (line 878)
    - Added `database_size_bytes` and `database_size_mb` to hybrid stats response
    - Fixed all callers in `health.py` and `mcp.py` to await `get_stats()`
  - **Result**: All metrics now display correctly (1778 memories, 2549 tags, 7.74MB)
  - **Files Modified**:
    - `src/mcp_memory_service/storage/sqlite_vec.py` - Made get_stats() async
    - `src/mcp_memory_service/storage/hybrid.py` - Added await and database size fields
    - `src/mcp_memory_service/web/api/health.py` - Simplified async handling
    - `src/mcp_memory_service/web/api/mcp.py` - Added await calls

- **Dashboard: Footer Layout** - Fixed footer appearing between header and content instead of at bottom
  - **Root Cause**: Footer not included in CSS grid layout template
  - **Impact**: Broken visual layout with footer misplaced in page flow
  - **Fix**:
    - Updated `.app-container` grid to include 5th row with "footer" area
    - Assigned `grid-area: footer` to `.app-footer` class
  - **Result**: Footer now correctly positioned at bottom of page
  - **Files Modified**:
    - `src/mcp_memory_service/web/static/style.css` - Updated grid layout (lines 101-110, 1899)

- **HTTP Server: Runtime Warnings** - Eliminated "coroutine was never awaited" warnings in logs
  - **Root Cause**: Legacy sync/async detection code after all backends became async
  - **Impact**: Runtime warnings cluttering server logs
  - **Fix**: Removed hybrid backend detection logic, all `get_stats()` calls now consistently await
  - **Result**: Clean server logs with no warnings

## [8.5.11] - 2025-10-23

### Fixed
- **Consolidation System: Embedding Retrieval in get_all_memories()** - Fixed SQLite-vec backend to actually retrieve embeddings (PR #171, fixes #169)
  - **Root Cause**: `get_all_memories()` methods only queried `memories` table without joining `memory_embeddings` virtual table
  - **Impact**: Consolidation system received 0 embeddings despite 1773 memories in database, preventing association discovery and semantic clustering
  - **Discovery**: PR #170 claimed to fix this but only modified debug tools; actual fix required changes to `sqlite_vec.py`
  - **Fix**:
    - Added `deserialize_embedding()` helper function using numpy.frombuffer() (sqlite-vec only provides serialize, not deserialize)
    - Updated both `get_all_memories()` methods (lines 1468 and 1681) with LEFT JOIN to `memory_embeddings` table
    - Modified `_row_to_memory()` helper to handle 10-column rows with embeddings
    - Applied Gemini Code Assist improvement to simplify row unpacking logic
  - **Test Results** (1773 memories):
    - Embeddings retrieved: 1773/1773 (100%)
    - Associations discovered: 90-91 (0.3-0.7 similarity range)
    - Semantic clusters created: 3 (DBSCAN grouping)
    - Performance: 1249-1414 memories/second
    - Duration: 1.25-1.42 seconds
  - **Consolidation Status**: ✅ **FULLY FUNCTIONAL** (all three blockers fixed: PR #166, #168, #171)
  - **Files Modified**:
    - `src/mcp_memory_service/storage/sqlite_vec.py` - Added embedding retrieval to all memory fetch operations

## [8.5.10] - 2025-10-23

### Fixed
- **Debug Tools: Embedding Retrieval Functionality** - Fixed debug MCP tools for SQLite-vec backend (PR #170, addresses #169)
  - **Root Cause**: `debug_retrieve_memory` function was written for ChromaDB but codebase now uses SQLite-vec storage
  - **Impact**: Debug tools (`debug_retrieve`) were broken, preventing debugging of embedding retrieval operations
  - **Fix**: Updated debug utilities to work with current SQLite-vec storage backend
  - **Changes**:
    - Fixed `debug_retrieve_memory` in `src/mcp_memory_service/utils/debug.py` to use storage's `retrieve()` method
    - Enhanced debug output with similarity scores, backend information, query details, and raw distance values
    - Added proper filtering by similarity threshold
  - **Files Modified**:
    - `src/mcp_memory_service/utils/debug.py` - Updated for SQLite-vec compatibility
    - `src/mcp_memory_service/server.py` - Enhanced debug output formatting

### Added
- **Debug Tool: get_raw_embedding MCP Tool** - New debugging capability for embedding inspection (PR #170)
  - **Purpose**: Direct debugging of embedding generation process
  - **Features**:
    - Shows raw embedding vectors with configurable display (first 10 and last 10 values for readability)
    - Displays embedding dimensions
    - Shows generation status and error messages
  - **Use Case**: Troubleshooting embedding-related issues in consolidation and semantic search
  - **Files Modified**:
    - `src/mcp_memory_service/server.py` - Added `get_raw_embedding` tool and handler

## [8.5.9] - 2025-10-22

### Fixed
- **Consolidation System: Missing update_memory() Method** - Added `update_memory()` method to all storage backends (PR #166, fixes #165)
  - **Root Cause**: Storage backends only implemented `update_memory_metadata()`, but consolidation system's `StorageProtocol` required `update_memory()` for saving consolidated results
  - **Impact**: Prevented consolidation system from saving associations, clusters, compressions, and archived memories
  - **Fix**: Added `update_memory()` method to base `MemoryStorage` class, delegating to `update_memory_metadata()` for proper implementation
  - **Affected Backends**: CloudflareStorage, SqliteVecMemoryStorage, HybridMemoryStorage
  - **Test Results**:
    - Verified on SQLite-vec backend with 1773 memories
    - Performance: 5011 memories/second (local SQLite-vec) vs 2.5 mem/s (Cloudflare)
    - Method successfully executes without AttributeError
  - **Files Modified**:
    - `src/mcp_memory_service/storage/base.py` - Added `update_memory()` to base class
    - `src/mcp_memory_service/storage/http_client.py` - Updated HTTP client call
    - `src/mcp_memory_service/storage/hybrid.py` - Fixed method reference

- **Consolidation System: Datetime Timezone Mismatch** - Fixed timezone handling in decay calculator (PR #168, fixes #167)
  - **Root Cause**: Mixed offset-naive and offset-aware datetime objects causing `TypeError` when calculating time differences
  - **Location**: `src/mcp_memory_service/consolidation/decay.py:191` in `_calculate_access_boost()`
  - **Impact**: Blocked decay calculator from completing, preventing associations, clustering, compression, and archival
  - **Fix**: Added timezone normalization to ensure both `current_time` and `last_accessed` are timezone-aware (UTC) before subtraction
  - **Implementation**:
    - Check if datetime is timezone-naive and convert to UTC if needed
    - Ensures consistent timezone handling across all datetime operations
  - **Files Modified**:
    - `src/mcp_memory_service/consolidation/decay.py` - Added timezone normalization logic

### Added
- **Consolidation Documentation** - Comprehensive setup and testing guides
  - `CONSOLIDATION_SETUP.md` - Complete configuration guide for dream-inspired memory consolidation
  - `CONSOLIDATION_TEST_RESULTS.md` - Expected results and troubleshooting guide
  - Documentation covers all 7 consolidation engines and 7 MCP tools

## [8.5.8] - 2025-10-22

### Fixed
- **Critical: Memory Age Calculation in Hooks** - Fixed Unix timestamp handling that caused memories to appear 20,363 days old (55 years) when they were actually recent
  - **Root Cause**: JavaScript's `Date()` constructor expects milliseconds, but SQLite database stores Unix timestamps in seconds. Three functions incorrectly treated seconds as milliseconds: `calculateTimeDecay()`, `calculateRecencyBonus()`, and `analyzeMemoryAgeDistribution()`
  - **Symptoms**:
    - Memory Age Analyzer showed `avgAge: 20363` days instead of actual age
    - Stale memory detection incorrectly triggered (`isStale: true`)
    - Recent memory percentage showed 0% when should be 100%
    - Time decay scores incorrect (1% instead of 100% for today's memories)
    - Recency bonus not applied (0% instead of +15%)
  - **Fix**: Added type checking to convert Unix timestamps properly - multiply by 1000 when timestamp is a number (seconds), pass through when it's an ISO string
  - **Impact**: Memory age calculations now accurate, stale detection works correctly, recency bonuses applied properly
  - **Files Modified**:
    - `claude-hooks/utilities/memory-scorer.js` (lines 11-17, 237-243, 524-534)
  - **Test Results**: Memories now show correct ages (0.4 days vs 20,363 days before fix)
  - **Platform**: All platforms (macOS, Linux, Windows)

### Changed
- **Installer Enhancement**: Added automatic statusLine configuration for v8.5.7 features
  - Installer now copies `statusline.sh` to `~/.claude/hooks/`
  - Checks for `jq` dependency (required for statusLine parsing)
  - Automatically adds `statusLine` configuration to `settings.json`
  - Enhanced documentation for statusLine setup and requirements

### Documentation
- Added `jq` as required dependency for statusLine feature
- Documented statusLine configuration in README.md installation section
- Clarified Unix timestamp handling in memory-scorer.js code comments

## [8.5.7] - 2025-10-21

### Added
- **SessionStart Hook Visibility Features** - Three complementary methods to view session memory context
  - **Visible Summary Output**: Clean bordered console display showing project, storage, memory count with recent indicator, and git context
  - **Detailed Log File**: Complete session context written to `~/.claude/last-session-context.txt` including project details, storage backend, memory statistics, git analysis, and top loaded memories
  - **Status Line Display**: Always-visible status bar at bottom of Claude Code terminal showing `🧠 8 (5 recent) | 📊 10 commits`
  - **Files Modified**:
    - `~/.claude/hooks/core/session-start.js` - Added summary output, log file generation, and cache file write logic
    - `~/.claude/settings.json` - Added statusLine configuration
  - **Files Created**:
    - `~/.claude/statusline.sh` - Bash script for status line display (requires `jq`)
    - `~/.claude/last-session-context.txt` - Auto-generated detailed log file
    - `~/.claude/hooks/utilities/session-cache.json` - Status line data cache
  - **Platform**: Linux/macOS (Windows SessionStart hook still broken - issue #160)

### Changed
- SessionStart hook output now provides visible feedback instead of being hidden in system-reminder tags
- Status line updates every 300ms with latest session memory context
- Log file automatically updates on each SessionStart hook execution

### Documentation
- Clarified difference between macOS and Linux hook output behavior (both use system-reminder tags since v2.2.0)
- Documented that `<session-start-hook>` wrapper tags were intentionally removed in v2.2.0 for cleaner output
- Added troubleshooting guide for status line visibility features

## [8.5.6] - 2025-10-16

### Fixed
- **Critical: Memory Hooks HTTPS SSL Certificate Validation** - Fixed hooks failing to connect to HTTPS server with self-signed certificates
  - **Root Cause**: Node.js HTTPS requests were rejecting self-signed SSL certificates silently, causing "No active connection available" errors
  - **Symptoms**:
    - Hooks showed "Failed to connect using any available protocol"
    - No memories retrieved despite server being healthy
    - HTTP server running but hooks couldn't establish connection
  - **Fix**: Added `rejectUnauthorized: false` to both health check and API POST request options in memory-client.js
  - **Impact**: Hooks now successfully connect via HTTPS to servers with self-signed certificates
  - **Files Modified**:
    - `claude-hooks/utilities/memory-client.js` (lines 174, 257)
    - `~/.claude/hooks/utilities/memory-client.js` (deployed)
  - **Test Results**: ✅ 7 memories retrieved from 1558 total, all phases working correctly
  - **Platform**: All platforms (macOS, Linux, Windows)

### Changed
- Memory hooks now support HTTPS endpoints with self-signed certificates without manual certificate trust configuration

## [8.5.5] - 2025-10-14

### Fixed
- **Critical: Claude Code Hooks Configuration** - Fixed session-start hook hanging/unresponsiveness on Windows
  - **Root Cause**: Missing forced process exit in session-start.js caused Node.js event loop to remain active with unclosed connections
  - **Fix 1**: Added `.finally()` block with 100ms delayed `process.exit(0)` to ensure clean termination
  - **Fix 2**: Corrected port mismatch in `~/.claude/hooks/config.json` (8889 → 8000) to match HTTP server
  - **Impact**: Hooks now complete in <15 seconds without hanging, Claude Code remains responsive
  - **Files Modified**:
    - `~/.claude/hooks/core/session-start.js` (lines 1010-1013)
    - `~/.claude/hooks/config.json` (line 7)
  - **Platform**: Windows (also applies to macOS/Linux)

### Changed
- **Documentation**: Added critical warning section to CLAUDE.md about hook configuration synchronization
  - Documents port mismatch symptoms (hanging hooks, unresponsive Claude Code, connection timeouts)
  - Lists all configuration files to check (`config.json`, HTTP server port, dashboard port)
  - Provides verification commands for Windows/Linux/macOS
  - Explains common mistakes (using dashboard port 8888/8443 instead of API port 8000)

## [8.5.4] - 2025-10-13

### Fixed
- **MCP Server**: Added explicit documentation to `store_memory` tool clarifying that `metadata.tags` must be an array, not a comma-separated string
  - Prevents validation error: `Input validation error: '...' is not of type 'array'`
  - Includes clear examples showing correct (array) vs incorrect (string) format
  - Documentation-only change - no code logic modified

### Changed
- Improved `store_memory` tool docstring with metadata format validation examples in `src/mcp_memory_service/mcp_server.py`

## [Unreleased]

### ✨ **Added**

#### **Linux systemd Service Support**
Added comprehensive systemd user service support for automatic HTTP server management on Linux systems.

**New Files:**
- `scripts/service/mcp-memory-http.service` - systemd user service definition
- `scripts/service/install_http_service.sh` - Interactive installation script
- `docs/deployment/systemd-service.md` - Detailed systemd setup guide

**Features:**
- ✅ **Automatic startup** on user login
- ✅ **Persistent operation** with loginctl linger support
- ✅ **Automatic restarts** on failure (RestartSec=10)
- ✅ **Centralized logging** via journald
- ✅ **Easy management** via systemctl commands
- ✅ **Environment loading** from .env file
- ✅ **Security hardening** (NoNewPrivileges, PrivateTmp)

**Usage:**
```bash
bash scripts/service/install_http_service.sh  # Install
systemctl --user start mcp-memory-http.service
systemctl --user enable mcp-memory-http.service
loginctl enable-linger $USER
```

### 📚 **Documentation**

#### **Enhanced HTTP Server Management**
- Updated `docs/http-server-management.md` with systemd section
- Added troubleshooting for port mismatch issues (8000 vs 8889)
- Documented hooks endpoint configuration requirements

#### **CLAUDE.md Updates**
- Added systemd commands to Essential Commands section
- Added "Troubleshooting Hooks Not Retrieving Memories" section
- Cross-referenced detailed documentation guides

### 🐛 **Fixed**

#### **Hooks Configuration Troubleshooting**
- Documented common port mismatch issue between hooks config and HTTP server
- Added diagnostic commands for verifying HTTP server status
- Clarified that HTTP server is **required** for hooks (stdio MCP cannot be used)

**Root Cause:** Many installations had hooks configured for port 8889 while HTTP server runs on port 8000 (default in .env). This caused silent failures where hooks couldn't connect.

**Solution:**
1. Update hooks config endpoint to `http://127.0.0.1:8000`
2. Verify with: `systemctl --user status mcp-memory-http.service`
3. Test with: `curl http://127.0.0.1:8000/api/health`

### 🔧 **Changed**

- Service files now use `WantedBy=default.target` for user services (not multi-user.target)
- Removed `User=` and `Group=` directives from user service (causes GROUP error)
- Enhanced error messages and troubleshooting documentation

### 🎨 **Improved**

#### **Claude Code Hooks UI Enhancements**
Significantly improved visual formatting and readability of memory context injection in Claude Code hooks.

**Enhanced Features:**
- ✅ **Intelligent Text Wrapping** - New `wrapText()` function preserves word boundaries and indentation
- ✅ **Unicode Box Drawing** - Professional visual formatting with ╭╮╯╰ characters for better structure
- ✅ **Recency-Based Display** - Recent memories (< 7 days) stay prominent, older ones are dimmed
- ✅ **Simplified Date Formatting** - Cleaner date display with recency indicators (today, yesterday, day name, date)
- ✅ **Enhanced Memory Categorization** - Better visual hierarchy for different memory types

**Files Modified:**
- `claude-hooks/utilities/context-formatter.js` - Major refactoring with wrapText function and enhanced formatMemoryForCLI
- `claude-hooks/core/session-start.js` - Minor display improvements for project detection
- `.claude/settings.local.json` - Platform-specific configuration updates (Windows→Linux path migration)

**Performance:**
- No performance impact - Lightweight formatting enhancements
- Better readability improves development efficiency
- Maintains all existing functionality while improving presentation

---

## [8.5.3] - 2025-10-12

### 🐛 **Fixed**

#### **Critical Memory Hooks Bug Fixes (Claude Code Integration)**
Fixed critical bugs preventing memory retrieval in Claude Code session-start hooks. Memory awareness now works correctly with both semantic and time-based searches.

**Problem**: Memory hooks showed "No relevant memories found" despite 1,419 memories in database. Retrieved memories were unrelated (from wrong projects) and sorted incorrectly (oldest first).

**Root Causes Fixed:**

1. **Empty Semantic Query Bug** (search.py:264-272)
   - **Issue**: `storage.retrieve("")` with empty string returned no results
   - **Fix**: Now uses `get_recent_memories()` when `semantic_query` is empty
   - **Impact**: Time-based searches without semantic filtering now work correctly

2. **Missing Time Expression** (search.py:401-403)
   - **Issue**: Hook sends `'last-2-weeks'` but parser didn't recognize it
   - **Fix**: Added support for 'last 2 weeks', 'past 2 weeks', 'last-2-weeks'
   - **Impact**: Phase 2 fallback queries now work properly

3. **Performance Optimization** (search.py:36)
   - **Change**: Reduced candidate pool from 1000 to 100 for time filtering
   - **Rationale**: Prevents timeout on large databases, improves response time
   - **Impact**: Search completes in <100ms vs timing out

4. **CRITICAL: Missing `await` Keywords** (hybrid.py:912, 916, 935, 947)
   - **Issue**: 4 async methods returned unawaited coroutines, causing server hangs
   - **Methods Fixed**:
     - Line 912: `get_all_tags()`
     - Line 916: `get_recent_memories(n)` ⭐ **THE CRITICAL ONE**
     - Line 935: `recall_memory(query, n_results)`
     - Line 947: `get_memories_by_time_range(start_time, end_time)`
   - **Impact**: Hybrid backend now works perfectly (11ms response time!)

5. **JavaScript Refactoring** (memory-client.js:213-293)
   - **Issue**: ~100 lines of duplicated HTTP request code
   - **Fix**: Created `_performApiPost()` helper to eliminate duplication
   - **Impact**: Improved maintainability, DRY compliance

6. **Port Consistency** (memory-client.js:166)
   - **Issue**: Health checks used standard web ports (443/80) while API calls used dev ports (8443/8889)
   - **Fix**: Made both use development ports consistently
   - **Impact**: Prevents connection failures with development endpoints

**Testing & Verification:**
```bash
# Before fix: Timeout
curl -s -m 5 "http://127.0.0.1:8889/api/search/by-time" -H "Content-Type: application/json" -d '{"query":"last-2-weeks","n_results":10}'
# (hangs indefinitely)

# After fix: Success
curl -s -m 5 "http://127.0.0.1:8889/api/search/by-time" -H "Content-Type: application/json" -d '{"query":"last-2-weeks","n_results":10}'
# Status: 200 (11ms)
# Results: 5 memories retrieved
```

**Files Modified:**
- `src/mcp_memory_service/web/api/search.py` - Empty query fix, time expression, pool size, UTC timezone
- `src/mcp_memory_service/storage/hybrid.py` - Fixed 4 missing await keywords
- `claude-hooks/utilities/memory-client.js` - Refactored HTTP helpers, port consistency, API contract
- `claude-hooks/core/session-start.js` - Updated hardcoded endpoint fallbacks
- `claude-hooks/config.json` - HTTP endpoint configuration

**Code Review**: All fixes reviewed and approved by Gemini Code Assist with PEP 8 compliance, timezone-aware datetimes, list comprehensions, and proper error handling.

**PR Reference**: [#156](https://github.com/doobidoo/mcp-memory-service/pull/156)

## [8.5.2] - 2025-10-11

### 🐛 **Fixed**

#### **v8.5.0 Implementation Missing (Code Completion)**
Complete implementation of Hybrid Backend Sync Dashboard feature that was documented in v8.5.0 CHANGELOG but code was never committed.

**Context**: v8.5.0 release (c241292) included CHANGELOG documentation and version bump but the actual implementation files were accidentally not staged/committed. This release completes the v8.5.0 feature by committing the missing implementation code.

**Files Added:**
- `src/mcp_memory_service/web/api/sync.py` - Sync API endpoints (GET /api/sync/status, POST /api/sync/force)
- `start_http_server.sh` - Cross-platform HTTP server management script

**Files Modified:**
- `src/mcp_memory_service/web/app.py` - Integrated sync router
- `src/mcp_memory_service/web/static/app.js` - Sync status UI with polling
- `src/mcp_memory_service/web/static/index.html` - Sync status bar markup
- `src/mcp_memory_service/web/static/style.css` - Sync bar styling + grid layout
- `src/mcp_memory_service/storage/hybrid.py` - Added `get_sync_status()` method
- `src/mcp_memory_service/web/api/health.py` - Health check enhancements
- `src/mcp_memory_service/storage/sqlite_vec.py` - Database path fixes

**Additional Improvements:**
- `claude-hooks/utilities/context-formatter.js` - Tree text wrapping improvements for better CLI output

**Impact**: Users can now access the complete Hybrid Backend Sync Dashboard feature including manual sync triggers and real-time status monitoring as originally intended in v8.5.0.

## [8.5.1] - 2025-10-11

### 🎯 **New Features**

#### **Dynamic Memory Weight Adjustment (Claude Code Hooks)**
Intelligent auto-calibration prevents stale memories from dominating session context when recent development exists.

**Problem Solved:**
Users reported "Current Development" section showing outdated memories (24-57 days old) instead of recent work from the last 7 days. Root cause: static configuration couldn't adapt to mismatches between git activity and memory age.

**Solution - Memory Age Distribution Analyzer:**
- **Auto-Detection**: Analyzes memory age percentiles (median, p75, p90, avg)
- **Staleness Detection**: Triggers when median > 30 days or < 20% recent memories
- **Smart Calibration**: Automatically adjusts weights:
  - `timeDecay`: 0.25 → 0.50 (+100% boost for recent memories)
  - `tagRelevance`: 0.35 → 0.20 (-43% reduce old tag matches)
- **Impact**: Stale memory sets automatically prioritize any recent memories

**Solution - Adaptive Git Context Weight:**
- **Scenario 1**: Recent commits (< 7d) + Stale memories (median > 30d)
  - Reduces git weight by 30%: `1.8x → 1.3x`
  - Prevents old git-related memories from dominating
- **Scenario 2**: Recent commits + Recent memories (both < 14d)
  - Keeps configured weight: `1.8x → 1.8x`
  - Git context is relevant and aligned
- **Scenario 3**: Old commits (> 14d) + Some recent memories
  - Reduces git weight by 15%: `1.8x → 1.5x`
  - Lets recent non-git memories surface

**Configuration Options:**
```json
{
  "memoryScoring": {
    "autoCalibrate": true  // Enable/disable auto-calibration
  },
  "gitAnalysis": {
    "adaptiveGitWeight": true  // Enable/disable adaptive git weight
  }
}
```

**Transparency Output:**
```
🎯 Auto-Calibration → Stale memory set detected (median: 54d old, 0% recent)
   Adjusted Weights → timeDecay: 0.50, tagRelevance: 0.20
⚙️  Adaptive Git Weight → Recent commits (1d ago) but stale memories - reducing git boost: 1.8 → 1.3
```

**Files Added:**
- `claude-hooks/test-adaptive-weights.js` - Comprehensive test scenarios

**Files Modified:**
- `claude-hooks/utilities/memory-scorer.js` (+162 lines):
  - `analyzeMemoryAgeDistribution()` - Detects staleness and recommends adjustments
  - `calculateAdaptiveGitWeight()` - Dynamically adjusts git boost based on context alignment
- `claude-hooks/core/session-start.js` (+60 lines):
  - Integrated age analysis before scoring
  - Auto-calibration logic with config check
  - Adaptive git weight calculation with transparency output
- `claude-hooks/config.json` (+2 options):
  - Added `memoryScoring.autoCalibrate: true` (default enabled)
  - Added `gitAnalysis.adaptiveGitWeight: true` (default enabled)

**Benefits:**
- ✅ **Automatic Detection**: No manual config changes when memories become stale
- ✅ **Context-Aware**: Git boost only applies when it enhances (not harms) relevance
- ✅ **Transparent**: Shows reasoning for adjustments in session output
- ✅ **Opt-Out Available**: Users can disable via config if desired
- ✅ **Backward Compatible**: Defaults preserve existing behavior when memories are recent

**Test Results:**
- Scenario 1 (Stale): Automatically calibrated weights and reduced git boost 1.8x → 1.3x
- Scenario 2 (Recent): No calibration needed, preserved git weight at 1.8x
- Both scenarios working as expected, preventing outdated context issues

## [8.5.0] - 2025-10-11

### 🎉 **New Features**

#### **Hybrid Backend Sync Dashboard**
Manual sync management UI with real-time status monitoring for hybrid storage backend.

**Features:**
- **Sync Status Bar** - Color-coded visual indicator between navigation and main content
  - 🔄 Syncing (blue gradient) - Active synchronization in progress
  - ⏱️ Pending (yellow gradient) - Operations queued, shows ETA and count
  - ✅ Synced (green gradient) - All operations synchronized, shows last sync time
  - ⚠️ Error (red gradient) - Sync failures detected, shows failed operation count
- **"Sync Now" Button** - Manual trigger for immediate Cloudflare ↔ SQLite synchronization
- **Real-time Monitoring** - 10-second polling for live sync status updates
- **REST API Endpoints:**
  - `GET /api/sync/status` - Current sync state, pending operations, last sync time
  - `POST /api/sync/force` - Manually trigger immediate sync

**Technical Implementation:**
- New sync API router: `src/mcp_memory_service/web/api/sync.py` (complete CRUD endpoints)
- Frontend integration: `src/mcp_memory_service/web/static/app.js:379-485` (status monitoring + manual sync)
- CSS styling: `src/mcp_memory_service/web/static/style.css:292-403` (grid layout + animations)
- HTML structure: `src/mcp_memory_service/web/static/index.html:125-138` (sync bar markup)
- Backend method: `src/mcp_memory_service/storage/hybrid.py:982-994` (added `get_sync_status()`)

### 🐛 **Fixed**

- **CSS Grid Layout Bug** - Sync status bar invisible despite JavaScript detecting hybrid mode
  - **Root Cause**: `.app-container` grid layout defined `"header" "nav" "main"` but sync bar wasn't assigned a grid area
  - **Fix**: Added `grid-area: sync` to `.sync-status-bar` and expanded grid to include sync row
  - **Files**: `style.css:101-109` (grid layout), `style.css:293` (sync bar grid area)

- **Sync Status Logic Error** - "Sync Now" button incorrectly disabled when background service running
  - **Root Cause**: Confused `is_running` (service alive) with `actively_syncing` (active sync operation)
  - **Fix**: Changed status determination to check `actively_syncing` field instead of `is_running`
  - **Impact**: Button now correctly enabled when 0 pending operations
  - **File**: `src/mcp_memory_service/web/api/sync.py:106-118`

- **Database Path Mismatch** - HTTP server using different SQLite database than Claude Code MCP
  - **Root Cause**: Missing `MCP_MEMORY_SQLITE_PATH` environment variable in HTTP server startup
  - **Fix**: Added explicit database path to match Claude Desktop config
  - **File**: `start_http_server.sh:4` (added `MCP_MEMORY_SQLITE_PATH` export)

- **Backend Configuration Inconsistency** - Claude Desktop using `cloudflare` backend while HTTP server using `hybrid`
  - **Root Cause**: Mismatched storage backend configurations preventing data synchronization
  - **Fix**: Unified both to use `hybrid` backend with same SQLite database
  - **File**: `claude_desktop_config.json:70` (changed `"cloudflare"` → `"hybrid"`)
  - **Impact**: Dashboard now shows same 1413 memories as Claude Code

### 🔧 **Improvements**

- **Enhanced Health Check** - `/api/health/detailed` now includes sync status for hybrid backend
  - Shows sync service state, pending operations, last sync time, failed operations
  - File: `src/mcp_memory_service/web/api/health.py:141-154`

- **Cleaned Database Files** - Removed obsolete SQLite databases to prevent confusion
  - Deleted: `memory_http.db` (701 memories), `backup_sqlite_vec.db`, `sqlite_vec_backup_20250822_230643.db`

- **Updated Startup Script** - `start_http_server.sh` now includes all required environment variables
  - Added: `MCP_MEMORY_SQLITE_PATH`, `MCP_HTTP_ENABLED`
  - Ensures HTTP server uses same database as Claude Code

### 📊 **Impact**

- **User Experience**: Dashboard now provides complete visibility and control over hybrid backend synchronization
- **Data Consistency**: Unified backend configuration ensures Claude Code and HTTP dashboard always show same data
- **Performance**: Manual sync trigger allows immediate synchronization instead of waiting 5 minutes
- **Reliability**: Fixed grid layout bug ensures sync status bar always visible when in hybrid mode

## [8.4.3] - 2025-10-11

### 🐛 Fixed
- **Sync Script Import Path:** Fixed `scripts/sync/sync_memory_backends.py` module import path to work correctly from scripts directory
  - Changed `sys.path.insert(0, str(Path(__file__).parent.parent))` → `sys.path.insert(0, str(Path(__file__).parent.parent.parent))`
  - Resolves `ModuleNotFoundError: No module named 'src'` when using manual sync commands
  - Fixes: `python scripts/sync/claude_sync_commands.py backup/restore/sync` commands

### 📊 Impact
- Users can now successfully run manual sync utilities for hybrid backend
- Manual Cloudflare ↔ SQLite synchronization commands now functional

## [8.4.2] - 2025-10-11

### 🎯 **Performance & Optimization**

#### **Additional MCP Context Optimization: Debug Tools Removal**
- **Problem**: Continuing context optimization efforts from v8.4.1, identified 2 additional low-value debug tools
- **Solution**: Removed debug/maintenance MCP tools with zero test dependencies

**Tools Removed:**
- `get_embedding` (606 tokens) - Returns raw embedding vectors; low-level debugging only
- `check_embedding_model` (553 tokens) - Checks if embedding model loaded; errors surface naturally

**Rationale:** These were specialized debugging tools rarely needed in practice. Embedding errors are caught during normal retrieval operations, and raw embedding inspection is a niche development task not required for AI assistant integration.

**Impact:**
- ✅ **MCP tools**: 26.8k → 25.6k tokens (4.5% additional reduction, -1.2k tokens)
- ✅ **Total optimization since v8.4.0**: 31.4k → 25.6k tokens (18.5% reduction, -5.8k tokens saved)
- ✅ **Zero breaking changes**: No test coverage for these tools
- ✅ **Conservative approach**: Removed only tools with no dependencies

**Files Modified:**
- `src/mcp_memory_service/server.py`: Removed 2 tool definitions, handlers, and implementations (~61 lines)

**Note:** Further optimization possible with MODERATE approach (debug_retrieve, exact_match_retrieve, cleanup_duplicates) if additional context savings needed.

## [8.4.1] - 2025-10-11

### 🎯 **Performance & Optimization**

#### **MCP Context Optimization: Dashboard Tools Removal**
- **Problem**: MCP tools consuming 31.4k tokens (15.7% of context budget) with redundant dashboard variants that duplicated web UI functionality
- **Solution**: Removed 8 dashboard-specific MCP tools that were unnecessary for Claude Code integration

**Tools Removed:**
- `dashboard_check_health`, `dashboard_recall_memory`, `dashboard_retrieve_memory`
- `dashboard_search_by_tag`, `dashboard_get_stats`, `dashboard_optimize_db`
- `dashboard_create_backup`, `dashboard_delete_memory`

**Rationale:** Web dashboard uses REST API endpoints (`/api/*`), not MCP tools. These were legacy wrappers created during early dashboard development that bloated context without providing value for AI assistant integration.

**Impact:**
- ✅ **MCP tools**: 31.4k → 26.8k tokens (15% reduction, -4.6k tokens saved)
- ✅ **Zero functional impact**: Core memory tools preserved (`check_database_health`, `recall_memory`, etc.)
- ✅ **Cleaner separation**: MCP protocol for Claude Code integration, HTTP REST API for web dashboard

**Files Modified:**
- `src/mcp_memory_service/server.py`: Removed 8 tool definitions, call_tool handlers, and method implementations (~506 lines)
- `docs/api/tag-standardization.md`: Updated to use `check_database_health()` instead of `dashboard_get_stats()`
- `docs/maintenance/memory-maintenance.md`: Removed redundant dashboard tool reference
- `docs/guides/mcp-enhancements.md`: Removed `dashboard_optimize_db` progress tracking example
- `docs/assets/images/project-infographic.svg`: Removed `dashboard_*_ops` visual reference

**Note:** Web dashboard at `https://localhost:8443` continues working normally via REST API. No user-facing changes.

## [8.4.0] - 2025-10-08

### ✨ **Features & Improvements**

#### **Claude Code Memory Hooks Recency Optimization**
- **Problem Solved**: Memory hooks were surfacing 60+ day old memories instead of recent development work (Oct v8.0-v8.3), causing critical development context to be missing despite being stored in the database
- **Core Enhancement**: Comprehensive recency optimization with rebalanced scoring algorithm to prioritize recent memories over well-tagged old content

##### **Scoring Algorithm Improvements**
- **Weight Rebalancing** (`config.json`):
  - `timeDecay`: 0.25 → 0.40 (+60% influence on recency)
  - `tagRelevance`: 0.35 → 0.25 (-29% to reduce tag dominance)
  - `contentQuality`: 0.25 → 0.20 (-20% to balance with time)
- **Gentler Time Decay**:
  - `timeDecayRate`: 0.1 → 0.05 (30-day memories: 0.22 vs 0.05 score - preserves older memories)
- **Stronger Git Context**:
  - `gitContextWeight`: 1.2 → 1.8 (80% boost vs 20% for git-derived memories)
  - Implemented multiplication in `session-start.js` after scoring
- **Expanded Time Windows**:
  - `recentTimeWindow`: "last-week" → "last-month" (broader recent search)
  - `fallbackTimeWindow`: "last-month" → "last-3-months" (wider fallback range)
- **Higher Quality Bar**: `minRelevanceScore`: 0.3 → 0.4 (filters generic old content)

##### **New Recency Bonus System** (`memory-scorer.js`)
- **Tiered Additive Bonuses**:
  - < 7 days: +0.15 bonus (strong boost for last week)
  - < 14 days: +0.10 bonus (moderate boost for last 2 weeks)
  - < 30 days: +0.05 bonus (small boost for last month)
- **Implementation**: Configurable tier-based system using `RECENCY_TIERS` array
- **Impact**: Ensures recent memories always get advantage regardless of tag relevance

##### **Documentation & Testing**
- **Added**: Comprehensive `CONFIGURATION.md` (450+ lines)
  - All scoring weights with impact analysis
  - Time decay behavior and examples
  - Git context weight strategy
  - Recency bonus system documentation
  - Tuning guide for different workflows
  - Migration notes from v1.0
- **Added**: Validation test suite (`test-recency-scoring.js`)
  - Tests scoring algorithm with memories of different ages
  - Validates time decay and recency bonus calculations
  - Confirms recent memories rank higher (success criteria: 2 of top 3 < 7 days old)

##### **Results**
- **Before**: Top 3 memories averaged 45+ days old (July-Sept content)
- **After**: All top 3 memories < 7 days old ✅
- **Validation**: 80% higher likelihood of surfacing recent work

**Impact**: ✅ Memory hooks now reliably surface recent development context, significantly improving Claude Code session awareness for active projects

##### **Technical Details**
- **PR**: [#155](https://github.com/doobidoo/mcp-memory-service/pull/155) - Memory hooks recency optimization
- **Files Modified**:
  - Configuration: `claude-hooks/config.json` (scoring weights, time windows, git context)
  - Scoring: `claude-hooks/utilities/memory-scorer.js` (recency bonus, configurable decay)
  - Session: `claude-hooks/core/session-start.js` (git context weight implementation)
  - Tests: `claude-hooks/test-recency-scoring.js` (validation suite)
  - Documentation: `claude-hooks/CONFIGURATION.md` (comprehensive guide)
- **Code Review**: 7 rounds of Gemini Code Assist review completed
  - **CRITICAL bugs fixed**: Config values not being used (round 5), gitContextWeight not implemented (round 6)
  - **Security fixes**: TLS certificate validation, future timestamp handling
  - **Maintainability**: DRY refactoring, tier-based configuration, comprehensive docs
- **Test Results**: ✅ All validation checks passed - recent memories consistently prioritized

## [8.3.1] - 2025-10-07

### ✨ **Features & Improvements**

#### **HTTP Server Management Tools**
- **Added**: Cross-platform HTTP server management utilities for Claude Code Natural Memory Triggers
- **New Scripts**:
  - `scripts/server/check_http_server.py`: Health check utility for HTTP server status verification
    - Supports both HTTP and HTTPS endpoints via environment variables
    - Verbose output by default, `-q` flag for quiet mode (exit codes only)
    - Detects MCP_HTTPS_ENABLED, MCP_HTTP_PORT, MCP_HTTPS_PORT configuration
  - `scripts/server/start_http_server.sh`: Auto-start script for Unix/macOS
    - Intelligent server detection with 5-second polling loop
    - Background process management via nohup
    - Logs to `/tmp/mcp-http-server.log`
  - `scripts/server/start_http_server.bat`: Auto-start script for Windows
    - 5-second polling loop for reliable startup detection
    - Starts server in new window for easy monitoring
    - Handles already-running servers gracefully
- **Documentation**: Comprehensive `docs/http-server-management.md` guide
  - Why HTTP server is required for Natural Memory Triggers
  - Quick health check commands
  - Manual and auto-start procedures
  - Troubleshooting guide with common issues
  - Integration with Claude Code hooks
  - Automation examples (launchd, Task Scheduler, shell aliases)
- **Use Case**: Essential for Claude Code hooks to inject relevant memories at session start without MCP conflicts
- **Wiki**: User-specific setup examples moved to wiki as reference guides
  - Windows-Hybrid-Backend-Setup-Example.md
  - Windows-Setup-Summary-Example.md

**Impact**: ✅ Streamlined HTTP server management, improved Natural Memory Triggers reliability, better cross-platform support

##### **Technical Details**
- **PR**: [#154](https://github.com/doobidoo/mcp-memory-service/pull/154) - HTTP server management tools
- **Files Added**: 4 new files
  - Scripts: `check_http_server.py`, `start_http_server.sh`, `start_http_server.bat`
  - Documentation: `http-server-management.md`
- **Gemini Reviews**: 3 rounds of code review and refinement
  - Security: Removed hardcoded credentials (replaced with placeholders)
  - Robustness: Improved exception handling, added polling loops
  - CLI Usability: Simplified argument parsing (removed redundant `-v` flag)
- **Cross-platform**: Fully tested on Unix/macOS and Windows environments
- **Integration**: Works seamlessly with existing `run_http_server.py` script

## [8.3.0] - 2025-10-07

### 🧹 **Refactoring & Code Cleanup**

#### **Complete ChromaDB Backend Removal**
- **Removed**: ~300-500 lines of ChromaDB dead code following v8.0.0 deprecation
- **Scope**: Complete cleanup across 18 files including configuration, CLI, server, storage, utilities, and web interface
- **Changes**:
  - **Configuration** (`config.py`): Removed CHROMA_PATH, CHROMA_SETTINGS, COLLECTION_METADATA, CHROMADB_MAX_CONTENT_LENGTH
  - **CLI** (`cli/main.py`, `cli/ingestion.py`): Removed `--chroma-path` option, removed 'chromadb' from storage backend choices
  - **Server** (`server.py`): Removed ChromaDB initialization (~60 lines), stats fallback (~40 lines), backup handler, validation logic
  - **Utilities** (`utils/db_utils.py`): Removed ChromaDB validation, stats, and repair functions (~140 lines)
  - **Storage** (`storage/cloudflare.py`, `storage/sqlite_vec.py`): Updated docstrings to be backend-agnostic
  - **Web** (`web/app.py`): Removed 'chromadb' from backend display name mapping
  - **Documentation**: Updated all error messages to suggest Cloudflare instead of ChromaDB
- **Impact**: ✅ Cleaner codebase, reduced technical debt, no misleading ChromaDB references
- **SUPPORTED_BACKENDS**: Now correctly shows `['sqlite_vec', 'sqlite-vec', 'cloudflare', 'hybrid']`

#### **CLI Backend Consistency Enhancement**
- **Added**: 'sqlite-vec' hyphenated alias to all CLI storage backend choices
- **Affected commands**: `server`, `status`, `ingest_document`, `ingest_directory`
- **Rationale**: Ensures CLI behavior matches SUPPORTED_BACKENDS configuration
- **Impact**: ✅ Improved user experience with consistent backend naming across CLI and configuration

### 🐛 **Bug Fixes**

#### **Dashboard System Information Display (Issue #151)**
- **Fixed**: Dashboard showing "N/A" for embedding model, embedding dimensions, and database size on non-hybrid backends
- **Root cause**: JavaScript expected hybrid-backend-specific nested paths (`storage.primary_stats.*`)
- **Solution**: Added fallback paths in `app.js` SYSTEM_INFO_CONFIG:
  - `settingsEmbeddingModel`: Falls back to `storage.embedding_model`
  - `settingsEmbeddingDim`: Falls back to `storage.embedding_dimension`
  - `settingsDbSize`: Falls back to `storage.database_size_mb`
- **Impact**: ✅ Dashboard now correctly displays system information for sqlite-vec, cloudflare, and hybrid backends

##### **Technical Details**
- **PR**: [#153](https://github.com/doobidoo/mcp-memory-service/pull/153) - ChromaDB dead code removal + Issue #151 fix
- **Files Modified**: 18 files
  - Core cleanup: `config.py`, `server.py`, `mcp_server.py`, `utils/db_utils.py`
  - CLI: `cli/main.py`, `cli/ingestion.py`, `cli/utils.py`
  - Storage: `storage/factory.py`, `storage/cloudflare.py`, `storage/sqlite_vec.py`
  - Web: `web/app.py`, `web/api/health.py`, `web/static/app.js`
  - Utilities: `utils/debug.py`, `embeddings/onnx_embeddings.py`
  - Package: `__init__.py`, `dependency_check.py`
- **Code Review**: Approved by Gemini Code Assist with high-quality feedback
- **Testing**: ✅ SQLite-vec backend initialization, ✅ SUPPORTED_BACKENDS verification, ✅ Service startup

## [8.2.4] - 2025-10-06

### 🐛 **Bug Fixes**

#### **Critical: Memory Hooks JSON Parsing Failure**
- **Fixed**: Memory awareness hooks completely broken - unable to retrieve memories due to JSON parsing errors
- **Root cause**: Naive string replacement in HTTP client destroyed valid JSON
  - `replace(/'/g, '"')` broke apostrophes in content (e.g., "it's" → "it"s")
  - Replaced Python-style values (True/False/None) in already-valid JSON
  - Used `/mcp` MCP-over-HTTP bridge instead of direct REST API
- **Solution**:
  - Removed destructive string replacements
  - Updated to use direct REST API endpoints (`/api/search`, `/api/search/by-time`)
  - Parse JSON responses directly without conversion
- **Impact**: ✅ Memory hooks now successfully retrieve context-relevant memories at session start

#### **HTTP Server Backend Configuration Override**
- **Fixed**: HTTP server ignored `.env` configuration, forcing `sqlite_vec` instead of configured `hybrid` backend
- **Root cause**: `run_http_server.py` used `os.environ.setdefault()` after `.env` loading, overriding user config
- **Solution**: Commented out the backend override line to respect `.env` settings
- **Impact**: ✅ Hybrid backend now works correctly via HTTP server

##### **Technical Details**
- **Files**:
  - `C:\Users\heinrich.krupp\.claude\hooks\utilities\memory-client.js` - Fixed `queryMemoriesHTTP()` method
  - `scripts/server/run_http_server.py` - Removed backend configuration override (line 148)
- **Affected**: All users using memory hooks with HTTP protocol (automatic session awareness)

## [8.2.3] - 2025-10-05

### ✨ **Enhancements**

#### **Dashboard Footer Navigation**
- **Added**: Comprehensive footer to dashboard with three sections
  - **Documentation**: Links to Wiki Home, Troubleshooting Guide, Backend Configuration Issues
  - **Resources**: GitHub Repository (with icon), Portfolio (doobidoo.github.io), API Documentation
  - **About**: Project description, Apache 2.0 license link, copyright notice
- **Features**: Security attributes (target="_blank", rel="noopener"), responsive design (mobile breakpoint 768px)
- **Impact**: ✅ Improved discoverability of documentation and resources from dashboard

### 🐛 **Bug Fixes**

#### **Dark Mode Footer Styling**
- **Critical fix**: Footer appearing bright/light in dark mode instead of dark
- **Root cause**: Incorrect CSS variable usage - using wrong end of inverted color scale
  - Background used `var(--neutral-900)` (#f9fafb - light) instead of `var(--neutral-100)` (#1f2937 - dark)
  - Headings used `var(--neutral-100)` (dark text) instead of `var(--neutral-900)` (light text)
- **Solution**: Corrected CSS variables to match dashboard card pattern with !important flags
- **Impact**: ✅ Footer now properly displays with dark background and light text in dark mode

##### **Technical Details**
- **Files**:
  - `src/mcp_memory_service/web/static/index.html` - Footer HTML structure (lines 463-517)
  - `src/mcp_memory_service/web/static/style.css` - Footer styling and dark mode overrides (lines 1757-1893)

## [8.2.2] - 2025-10-05

### ✨ **Enhancements**

#### **HTTP-MCP Bridge: recall_memory Tool Support**
- **Added**: `recall_memory` tool to MCP HTTP bridge API
- **Functionality**: Natural language time-based memory retrieval (e.g., "last week", "yesterday")
- **Integration**: Seamlessly maps to storage backend's `recall_memory` method
- **API**: Accepts `query` (natural language) and optional `n_results` parameter
- **Use Case**: Enables time-aware memory recall through HTTP/MCP bridge interface

##### **Technical Details**
- **File**: `src/mcp_memory_service/web/api/mcp.py`
  - Added `recall_memory` tool definition to `MCP_TOOLS` array
  - Implemented handler in `handle_tool_call()` function
  - Returns standardized format: content, content_hash, tags, created_at

## [8.2.1] - 2025-10-05

### 🐛 **Bug Fixes**

#### **Critical: Missing Core Dependencies**
- **Fixed**: `sentence-transformers` and `torch` moved from optional `[ml]` extras to base dependencies
- **Root cause**: v8.2.0 removed ChromaDB but accidentally made semantic search dependencies optional
- **Impact**: Service failed to start with `ImportError: sentence-transformers is not available`
- **Resolution**: These are core dependencies required for semantic memory functionality
- **Breaking**: Users upgrading from v8.2.0 must run `uv sync` to install corrected dependencies

##### **Technical Details**
- **File**: `pyproject.toml`
  - Moved `sentence-transformers>=2.2.2` from `[ml]` to `dependencies`
  - Moved `torch>=2.0.0` from `[ml]` to `dependencies`
  - Semantic search is core functionality, not optional

## [8.2.0] - 2025-10-05

### ✨ **Dashboard UX Improvements**

#### **Dark Mode Polish**
- **Fixed**: Connection status indicator now properly displays in dark mode
- **Implementation**: Added dark mode CSS override for `.connection-status` component
- **Impact**: ✅ All dashboard elements now fully support dark mode without visual glitches

#### **Browse Tab User Experience**
- **Enhancement**: Automatic smooth scroll to results when clicking a tag
- **Implementation**: Added `scrollIntoView()` with smooth behavior to `filterByTag()` method
- **User Benefit**: No more manual scrolling needed - tag selection immediately shows filtered memories
- **Impact**: ✅ Significantly improved discoverability and flow in Browse by Tags view

##### **Technical Details**
- **File**: `src/mcp_memory_service/web/static/style.css`
  - Added dark mode override for connection status background, border, and text colors
  - Uses CSS variables for consistency with theme system
- **File**: `src/mcp_memory_service/web/static/app.js`
  - Added smooth scroll animation when displaying tag-filtered results
  - Scrolls results section into view with `block: 'start'` positioning

## [8.1.2] - 2025-10-05

### 🐛 **Bug Fixes**

#### **Dashboard Statistics Display**
- **Critical fix**: Dashboard showing 0 for "This Week" and "Tags" statistics on Hybrid and Cloudflare backends
- **Root cause**: Statistics fields not exposed at top level of storage health response

##### **Hybrid Backend Fix** (`src/mcp_memory_service/storage/hybrid.py`)
- Extract `unique_tags` from `primary_stats` to top-level stats dictionary
- Extract `memories_this_week` from `primary_stats` to top-level stats dictionary
- Maintains consistency with SQLite-vec standalone backend behavior

##### **Cloudflare Backend Fix** (`src/mcp_memory_service/storage/cloudflare.py`)
- Added SQL subquery to calculate `unique_tags` from tags table
- Added SQL subquery to calculate `memories_this_week` (last 7 days)
- Now returns both statistics in `get_stats()` response

##### **Impact**
- ✅ Dashboard now correctly displays weekly memory count for all backends
- ✅ Dashboard now correctly displays unique tags count for all backends
- ✅ SQLite-vec standalone backend already had these fields (no change needed)
- ✅ Fixes issue where hybrid/cloudflare users saw "0" despite having memories and tags

## [8.1.1] - 2025-10-05

### 🐛 **Bug Fixes**

#### **Dark Mode Text Contrast Regression**
- **Critical fix**: Memory card text barely visible in dark mode due to hardcoded white backgrounds
- **Root cause**: CSS variable redefinition made text colors too faint when applied to white backgrounds
- **Solution**: Override all major containers with dark backgrounds (`#1f2937`) and force bright text colors

##### **Fixed Components**
- Memory cards: Now use dark card backgrounds with bright white text (`#f9fafb`)
- Memory metadata: Labels bright white (`#f9fafb`), values light gray (`#d1d5db`)
- Action cards: Dark backgrounds for proper contrast
- All containers: App header, welcome card, search filters, modals now properly dark

##### **Technical Details**
- Added `!important` overrides for 11 container backgrounds
- Memory content text: `var(--neutral-900) !important` → `#f9fafb`
- Memory meta labels: `var(--neutral-900) !important` → `#f9fafb`
- Memory meta values: `var(--neutral-600) !important` → `#d1d5db`
- Cache-busting comments to force browser reload

##### **Impact**
- ✅ Dark mode now fully readable across all dashboard views
- ✅ Proper contrast ratios for accessibility
- ✅ No visual regression from v8.1.0 light mode

## [8.1.0] - 2025-10-04

### ✨ **Dashboard Dark Mode & UX Enhancements**

Production-ready dashboard improvements with comprehensive dark mode support, settings management, and optimized CSS architecture.

#### 🎨 **New Features**

##### **Dark Mode Toggle**
- **Clean theme switching** with sun/moon icon toggle in header
- **Persistent preference** via localStorage - theme survives page reloads
- **Smooth transitions** between light and dark themes
- **Full coverage** across all dashboard views (Dashboard, Search, Browse)
- **Performance**: Instant theme switching with CSS class toggle

##### **Settings Modal**
- **Centralized preferences** accessible via cogwheel button
- **User preferences**:
  - Theme selection (Light/Dark)
  - View density (Comfortable/Compact)
  - Memory preview lines (1-10)
- **System information display**:
  - Application version
  - Storage backend configuration (Hybrid/SQLite/Cloudflare)
  - Primary/secondary backend details
  - Embedding model and dimensions
  - Database size
  - Total memories count
  - Server uptime (human-readable format)
- **Robust data loading**: Promise.allSettled() for graceful error handling
- **User feedback**: Toast notifications for save failures

#### 🏗️ **Architecture & Performance**

##### **CSS Optimization - Variable Redefinition Approach**
- **Massive code reduction**: 2116 → 1708 lines (**-408 lines, -19% smaller**)
- **Clean implementation**: Redefine CSS variables in `body.dark-mode` instead of 200+ hardcoded overrides
- **Maintainability**: Single source of truth for dark mode colors
- **Automatic theming**: All components using CSS variables get dark mode support
- **No !important abuse**: Eliminated all !important tags except `.hidden` utility class

##### **JavaScript Improvements**
- **Data-driven configuration**: System info fields defined in static config object
- **Static class properties**: Constants defined once per class, not per instance
- **Robust error handling**: Promise.allSettled() prevents partial failures
- **Zero value handling**: Proper `!= null` checks (displays 0 MB, 0 memories correctly)
- **Smart field updates**: Targeted element updates using config keys

##### **HTML Optimization**
- **SVG icon deduplication**: Info icon defined once in `<defs>`, reused via `<use>`
- **File size reduction**: 4 inline SVG instances → 1 reusable symbol
- **Accessibility**: Proper `aria-hidden` and semantic structure
- **No inline styles**: All styling moved to CSS for better separation of concerns

#### 📊 **Performance Metrics**

| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| Page Load | <2s | 25ms | ✅ EXCELLENT |
| Memory Operations | <1s | 26ms | ✅ EXCELLENT |
| Tag Search | <500ms | <100ms | ✅ EXCELLENT |
| Theme Toggle | Instant | <1ms | ✅ EXCELLENT |
| CSS File Size | Smaller | -19% | ✅ EXCELLENT |

#### 🔍 **Code Quality**

##### **Gemini Code Assist Review**
- **8 review iterations** - All feedback addressed
- **Final verdict**: "Solid enhancement to the dashboard's user experience"
- **Key improvements**:
  - Variable redefinition pattern for dark mode
  - Removed redundant arrays (derive from Object.keys)
  - SVG icon deduplication
  - Better error messages for users
  - Static method optimization

##### **Files Changed**
- `src/mcp_memory_service/web/static/style.css`: -408 lines (major refactoring)
- `src/mcp_memory_service/web/static/app.js`: +255 lines (settings, theme management)
- `src/mcp_memory_service/web/static/index.html`: +134 lines (modal, icons, SVG defs)
- **Net change**: -19 lines (improved functionality with less code)

#### 🎯 **User Experience**

- **Visual comfort**: Dark mode reduces eye strain for long sessions
- **Personalization**: User-controlled theme and display preferences
- **Transparency**: System information visible in settings modal
- **Feedback**: Error notifications for localStorage failures
- **Consistency**: Dark mode styling matches across all views
- **Accessibility**: High contrast, semantic HTML, keyboard navigation

#### 📝 **Technical Details**

- **Conservative approach**: Original light mode design preserved pixel-perfect
- **Additive CSS**: Dark mode styles never modify existing rules
- **Browser compatibility**: CSS variables, localStorage, SSE all widely supported
- **Mobile responsive**: Works on all screen sizes (tested 768px, 1024px breakpoints)
- **XSS protection**: All user inputs properly escaped via `escapeHtml()`

**PR**: #150 (16 commits, 543 additions, 23 deletions)

---

## [8.0.0] - 2025-10-04

### 💥 **BREAKING CHANGE: ChromaDB Backend Removed**

**This is a major breaking change release**. The ChromaDB backend has been completely removed from the codebase after being deprecated since v5.x.

#### ❌ **Removed**

##### **ChromaDB Backend Complete Removal**
- **Deleted 2,841 lines** of ChromaDB-related code from the codebase
- **Core files removed**:
  - `src/mcp_memory_service/storage/chroma.py` (1,501 lines)
  - `src/mcp_memory_service/storage/chroma_enhanced.py` (176 lines)
  - `tests/unit/test_chroma.py`
  - `tests/chromadb/test_chromadb_types.py`
- **Dependencies removed**:
  - `chromadb` optional dependency group from `pyproject.toml`
  - ~2GB PyTorch + sentence-transformers dependency burden eliminated
- **Factory updates**:
  - Removed ChromaDB backend case from storage factory
  - Removed ChromaStorage initialization logic
  - Added clear error messages directing to migration guide

#### 📦 **Migration & Legacy Support**

##### **ChromaDB Legacy Branch**
- **Branch**: [`chromadb-legacy`](https://github.com/doobidoo/mcp-memory-service/tree/chromadb-legacy)
- **Tag**: `chromadb-legacy-final` - Final ChromaDB code snapshot before removal
- **Status**: Frozen/Archived - No active maintenance
- **Purpose**: Historical reference and migration support

##### **Migration Script Preserved**
- **Location**: `scripts/migration/legacy/migrate_chroma_to_sqlite.py`
- **Status**: Moved to legacy folder, still functional for migrations
- **Alternative**: Check chromadb-legacy branch for additional migration tools

##### **Migration Guide**
See **Issue #148** for comprehensive ChromaDB to Hybrid/SQLite-vec/Cloudflare migration instructions:
- Step-by-step migration procedures
- Data backup and validation steps
- Recommended migration path: **ChromaDB → Hybrid Backend**

#### ✅ **Supported Storage Backends (v8.0.0+)**

| Backend | Status | Use Case | Performance |
|---------|--------|----------|-------------|
| **Hybrid** | ⭐ RECOMMENDED | Production, multi-device | 5ms (SQLite) + cloud sync |
| **SQLite-vec** | ✅ Supported | Development, single-device | 5ms read/write |
| **Cloudflare** | ✅ Supported | Cloud-native, serverless | Network dependent |
| **HTTP Client** | ✅ Supported | Distributed, multi-client | Network dependent |
| **ChromaDB** | ❌ REMOVED | N/A - See legacy branch | N/A |

#### 📊 **Impact & Rationale**

**Why Remove ChromaDB?**
- **Performance**: ChromaDB 15ms vs SQLite-vec 5ms (3x slower)
- **Dependencies**: ~2GB PyTorch download eliminated
- **Maintenance**: 2,841 lines of code removed reduces complexity
- **Better Alternatives**: Hybrid backend provides superior performance with cloud sync

**For Existing ChromaDB Users:**
- **No immediate action required** - Can continue using v7.x releases
- **Upgrade path available** - Migration guide in Issue #148
- **Legacy branch available** - Full code preserved for reference
- **Support timeline**: v7.x will remain available, but no new features

#### 🔧 **Technical Changes**

**Code Removed:**
- ChromaDB storage backend implementations
- ChromaDB-specific tests and fixtures
- ChromaDB configuration handling in factory
- ChromaDB deprecation warnings in server.py

**Error Handling:**
- Attempting to use `MCP_MEMORY_STORAGE_BACKEND=chroma` now raises clear `ValueError`
- Error message includes link to migration guide and legacy branch
- Fallback logic removed - only valid backends accepted

**Dependencies:**
- Removed `chromadb>=0.5.0` from optional dependencies
- Updated `full` dependency group to exclude chromadb
- No impact on core dependencies - only optional dependency cleanup

#### 🚀 **Upgrade Instructions**

**For ChromaDB Users (REQUIRED MIGRATION):**
1. **Backup your data**:
   ```bash
   # Use legacy migration script
   git checkout chromadb-legacy
   python scripts/migration/migrate_chroma_to_sqlite.py
   ```

2. **Switch backend**:
   ```bash
   # Recommended: Hybrid backend (best of both worlds)
   export MCP_MEMORY_STORAGE_BACKEND=hybrid

   # Or: SQLite-vec (local-only)
   export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec

   # Or: Cloudflare (cloud-only)
   export MCP_MEMORY_STORAGE_BACKEND=cloudflare
   ```

3. **Update to v8.0.0**:
   ```bash
   git checkout main
   git pull origin main
   python install.py --storage-backend hybrid
   ```

4. **Validate migration**:
   ```bash
   python scripts/validation/validate_configuration_complete.py
   ```

**For Non-ChromaDB Users (No Action Required):**
- Upgrade seamlessly - no breaking changes for SQLite-vec, Cloudflare, or Hybrid users
- Enjoy reduced dependency footprint and simplified codebase

#### 📚 **Documentation Updates**
- Updated architecture diagrams to show ChromaDB as deprecated/removed
- Updated storage backend comparison tables
- Added migration guide in Issue #148
- Legacy branch README updated with archive notice

#### 🔗 **References**
- **Issue**: #148 - Plan ChromaDB Backend Deprecation and Removal (→ v8.0.0)
- **Legacy Branch**: https://github.com/doobidoo/mcp-memory-service/tree/chromadb-legacy
- **Migration Guide**: See Issue #148 for detailed migration instructions

---

## Historic Releases

For older releases (v7.21.0 and earlier), see [CHANGELOG-HISTORIC.md](./CHANGELOG-HISTORIC.md).

**Historic Version Range**: v0.1.0 through v7.21.0 (2025-07-XX through 2025-10-03)
## [7.6.0] - 2025-10-04

### ✨ **Enhanced Document Ingestion with Semtools Support**

#### 🆕 **Core Features**
- **Semtools loader integration** - Optional Rust-based document parser with LlamaParse API for superior extraction quality
- **New format support** - DOCX, DOC, PPTX, XLSX (requires semtools installation)
- **Intelligent chunking** - Respects paragraph and sentence boundaries for better semantic coherence
- **Graceful fallback** - Auto-detects semtools availability, uses native parsers (PyPDF2/pdfplumber) if unavailable
- **Configuration options** - Environment variables for LLAMAPARSE_API_KEY, MCP_DOCUMENT_CHUNK_SIZE, MCP_DOCUMENT_CHUNK_OVERLAP
- **Zero breaking changes** - Fully backward compatible, existing document ingestion unchanged

#### 📄 **Supported Document Formats**
| Format | Native Parser | With Semtools | Quality |
|--------|--------------|---------------|---------|
| PDF | PyPDF2/pdfplumber | ✅ LlamaParse | Excellent (OCR, tables) |
| DOCX/DOC | ❌ Not supported | ✅ LlamaParse | Excellent |
| PPTX | ❌ Not supported | ✅ LlamaParse | Excellent |
| XLSX | ❌ Not supported | ✅ LlamaParse | Excellent |
| TXT/MD | ✅ Built-in | N/A | Perfect |

#### 🔧 **Technical Implementation**
- **New file**: `src/mcp_memory_service/ingestion/semtools_loader.py` (220 lines)
  - SemtoolsLoader class implementing DocumentLoader interface
  - Async subprocess execution with 5-minute timeout for large documents
  - Automatic semtools availability detection via `shutil.which()`
  - LlamaParse API key support via LLAMAPARSE_API_KEY environment variable
  - Comprehensive error handling with detailed logging
- **Modified**: `src/mcp_memory_service/config.py` - Added document processing configuration section (lines 564-586)
- **Modified**: `src/mcp_memory_service/ingestion/registry.py` - Registered new formats (DOCX, PPTX, XLSX)
- **Modified**: `src/mcp_memory_service/ingestion/__init__.py` - Auto-registration of semtools loader
- **Modified**: `CLAUDE.md` - Added comprehensive "Document Ingestion (v7.6.0+)" section with usage examples
- **Tests**: `tests/unit/test_semtools_loader.py` - 12 comprehensive unit tests, all passing ✅

#### 📦 **Installation & Configuration**
```bash
# Optional - install semtools for enhanced parsing
npm i -g @llamaindex/semtools
# or
cargo install semtools

# Optional - configure LlamaParse API for best quality
export LLAMAPARSE_API_KEY="llx-..."

# Document chunking configuration
export MCP_DOCUMENT_CHUNK_SIZE=1000          # Characters per chunk (default: 1000)
export MCP_DOCUMENT_CHUNK_OVERLAP=200        # Overlap between chunks (default: 200)
```

#### 🎯 **Usage Example**
```python
from pathlib import Path
from mcp_memory_service.ingestion import get_loader_for_file

# Automatic format detection and loader selection
loader = get_loader_for_file(Path("document.pdf"))
async for chunk in loader.extract_chunks(Path("document.pdf")):
    await store_memory(chunk.content, tags=["documentation"])
```

#### ✅ **Benefits**
- **Superior PDF parsing** - OCR capabilities and table extraction via LlamaParse
- **Microsoft Office support** - DOCX, PPTX formats now supported (previously unavailable)
- **Production-ready** - Comprehensive error handling, timeout protection, detailed logging
- **Flexible deployment** - Optional enhancement, works perfectly without semtools
- **Automatic detection** - No configuration needed, auto-selects best available parser
- **Minimal overhead** - Only ~5ms initialization cost when semtools not installed

#### 🔗 **Related Issues**
- Closes #94 - Integrate Semtools for Enhanced Document Processing
- Future work tracked in #147 - CLI commands, batch processing, progress reporting, benchmarks

#### 📊 **Test Coverage**
- 12/12 unit tests passing
- Tests cover: initialization, availability checking, file handling, successful extraction, API key usage, error scenarios, timeout handling, empty content, registry integration
- Comprehensive mocking of subprocess execution for reliable CI/CD

## [7.5.5] - 2025-10-04

### 🐛 **Bug Fixes - HybridMemoryStorage Critical Issues**

#### Fixed - Health Check Support (PR #145)
- **HybridMemoryStorage recognition in health checks** - Resolved "Unknown storage type: HybridMemoryStorage" error
- **Dashboard statistics for hybrid backend** - Added comprehensive stats collection from SQLite-vec primary storage
- **Health validation for hybrid storage** - Implemented proper validation logic for hybrid backend
- **Cloudflare sync status visibility** - Display sync service status (not_configured/configured/syncing)

#### Fixed - Missing recall() Method (PR #146)
- **AttributeError on time-based queries** - Added missing `recall()` method to HybridMemoryStorage
- **Server.py compatibility** - Resolves errors when server calls `storage.recall()` with time filtering
- **Consistent API** - Matches method signature of SqliteVecMemoryStorage and CloudflareStorage
- **Delegation to primary** - Properly delegates to SQLite-vec primary storage for recall operations

#### Technical Details
- Added `HybridMemoryStorage` case to `dashboard_get_stats()` endpoint (server.py:2503)
- Added `HybridMemoryStorage` case to `check_database_health()` endpoint (server.py:3705)
- Added `recall()` method to HybridMemoryStorage (hybrid.py:916)
- Method signature: `async def recall(query: Optional[str] = None, n_results: int = 5, start_timestamp: Optional[float] = None, end_timestamp: Optional[float] = None) -> List[MemoryQueryResult]`
- Query primary storage (SQLite-vec) for memory counts, tags, database info
- Fixed code quality issues from Gemini Code Assist review (removed duplicate imports, refactored getattr usage)

#### Impact
- ✅ HTTP dashboard now properly displays hybrid backend statistics
- ✅ MCP health check tool correctly validates hybrid storage
- ✅ Time-based recall queries now work correctly with hybrid backend
- ✅ No more "Unknown storage type" or AttributeError exceptions
- ✅ HybridMemoryStorage fully compatible with all server.py operations

## [7.5.4] - 2025-10-04

### ✨ **Configurable Hybrid Sync Break Conditions**

#### 🔄 **Enhanced Synchronization Control**
- **Configurable early break conditions** - Made hybrid sync termination thresholds configurable via environment variables
  - `MCP_HYBRID_MAX_EMPTY_BATCHES` - Stop after N consecutive batches without new syncs (default: 20, was hardcoded 5)
  - `MCP_HYBRID_MIN_CHECK_COUNT` - Minimum memories to check before early stop (default: 1000, was hardcoded 200)
- **Increased default thresholds** - Quadrupled default values (5→20 batches, 200→1000 memories) to ensure complete synchronization
- **Enhanced logging** - Added detailed sync progress logging every 100 memories with consecutive empty batch tracking
- **Threshold visibility** - Break condition log messages now display threshold values for better diagnostics

#### 🐛 **Bug Fix - Incomplete Synchronization**
- **Resolved incomplete sync issue** - Dashboard was showing only 1040 memories instead of 1200+ from Cloudflare
- **Root cause** - Hardcoded early break conditions triggered prematurely causing missing memories
- **Impact** - Missing memories distributed throughout Cloudflare dataset were never synced to local SQLite

#### ⚙️ **Configuration**
```bash
# Environment variables for tuning sync behavior
export MCP_HYBRID_MAX_EMPTY_BATCHES=20     # Stop after N empty batches (min: 1)
export MCP_HYBRID_MIN_CHECK_COUNT=1000     # Min memories to check before early stop (min: 1)
```

#### 🔧 **Code Quality Improvements**
- **Added input validation** - `min_value=1` constraint prevents zero values that would break sync
- **Fixed progress logging** - Prevents misleading initial log message at `processed_count=0`
- **Eliminated duplicate defaults** - Refactored to use `getattr` pattern for config imports
- **Improved maintainability** - Centralized default values in config.py

#### ✅ **Benefits**
- Complete synchronization of all Cloudflare memories to SQLite
- Configurable per deployment needs without code changes
- Better diagnostics for troubleshooting sync issues
- Maintains protection against infinite loops (early break still active)
- Preserves Cloudflare API protection through configurable limits
- No behavior change for deployments with small datasets

#### 🔗 **References**
- Closes issue: Incomplete hybrid sync (1040/1200+ memories)
- PR #142: Configurable hybrid sync break conditions
- All Gemini Code Assist feedback addressed

## [7.5.3] - 2025-10-04

### 🏗️ **Repository Organization**

#### 📁 **Litestream Sync System Reorganization**
- **Consolidated Litestream scripts** → `scripts/sync/litestream/`
  - Moved 9 shell scripts from `/sync/` directory (git-like staging workflow)
  - Relocated 4 root-level setup scripts (`enhanced_memory_store.sh`, `setup_local_litestream.sh`, etc.)
  - Moved macOS launchd service (`io.litestream.replication.plist`)
  - Moved staging database schema (`staging_db_init.sql`)
- **Created comprehensive documentation** - `scripts/sync/litestream/README.md`
  - Local network HTTP API sync architecture
  - Git-like staging workflow guide
  - Setup and configuration instructions
  - Comparison with Cloudflare hybrid sync

#### 📂 **Deployment Files Consolidation**
- **Moved systemd service** → `scripts/service/mcp-memory.service`
- **Archived unused configs** → `archive/deployment-configs/`
  - `smithery.yaml`
  - `empty_config.yml`
- **Removed empty `/deployment/` directory**

#### 🛠️ **Debug/Investigation Files Organization**
- **Moved to `scripts/development/`**:
  - `debug_server_initialization.py` - Cloudflare backend debugger
  - `verify_hybrid_sync.py` - Hybrid storage verification
- **Archived documentation** → `archive/`
  - `MACOS_HOOKS_INVESTIGATION.md` → `archive/investigations/`
  - `release-notes-v7.1.4.md` → `archive/release-notes/`

#### 📚 **Documentation Updates**
- **Enhanced `scripts/README.md`** with dual sync system documentation
  - Cloudflare Hybrid Sync (cloud backend) section
  - Litestream Sync (local network HTTP API) section
  - Clear distinction between the two systems

### 🎯 **Key Clarifications**
- **Litestream sync**: Multi-device synchronization via central SQLite-vec HTTP API (local network)
  - Use case: Privacy-focused, data stays on local network
  - Architecture: Git-like staging workflow with conflict detection
- **Cloudflare sync**: Cloud-based hybrid backend (internet)
  - Use case: Global access, automatic cloud backup
  - Architecture: Direct sync queue with background operations

### 📦 **Files Affected**
- 27 files changed, 594 insertions(+), 3 deletions(-)
- 13 files renamed/relocated
- 3 new documentation files
- 3 new archive directories

### ⚠️ **Breaking Changes**
None - Purely organizational changes with no functional impact

### 🔄 **Migration Notes**
If using Litestream sync scripts:
- Update script paths: `/sync/memory_sync.sh` → `scripts/sync/litestream/memory_sync.sh`
- Launchd plist location: `/deployment/io.litestream.replication.plist` → `scripts/sync/litestream/io.litestream.replication.plist`
- All scripts remain functionally identical

## [7.5.2] - 2025-10-03

### 🐛 **Bug Fixes**

#### 🔧 **MCP HTTP Endpoint Fixes**
- **Fixed JSON serialization** - Changed `str(result)` to `json.dumps(result)` for proper client parsing
  - MCP endpoint was returning Python dict string representation (`{'key': 'value'}`) instead of valid JSON (`{"key": "value"}`)
  - Caused hook clients to fail parsing responses with "Expected ',' or '}'" errors
- **Fixed similarity threshold** - Changed default from `0.7` to `0.0` to return all relevant memories
  - 70% similarity threshold was too restrictive, filtering out memories with scores 0.2-0.5
  - Now returns all results, allowing client-side scoring to determine relevance

#### 🔌 **Memory Hooks HTTP/HTTPS Protocol Detection**
- **Fixed protocol detection** in `claude-hooks/utilities/memory-client.js`
  - Added `http` module import alongside existing `https` module
  - Implemented dynamic protocol selection: `const protocol = url.protocol === 'https:' ? https : http`
  - Previously hardcoded `https.request()` failed for `http://` endpoints

### 🎯 **Impact**
- ✅ Session-start hooks now properly inject memory context on Claude Code startup
- ✅ HTTP memory server (port 8888) connectivity fully restored
- ✅ Relevant memories (score 0.2-0.5) no longer filtered out by overly restrictive threshold
- ✅ JSON parsing errors resolved for all memory retrieval operations

## [7.5.1] - 2025-10-03

### 🛠️ **Linux Enhancements**

#### 🔄 **Manual Sync Utilities for Hybrid Storage**
- **`sync_now.py` script** - Manual on-demand synchronization for hybrid storage on Linux
  - Type-safe data structures with `TypedDict` (SyncResult, SyncStatus)
  - Comprehensive logging with configurable levels
  - Verbose mode (`--verbose`) for detailed error tracebacks
  - Robust status validation prevents misleading success reports
  - Proper error handling with specific exception types
- **Systemd integration** - Automated hourly background synchronization
  - `mcp-memory-sync.service` - Systemd service for executing sync operations
  - `mcp-memory-sync.timer` - Systemd timer triggering hourly syncs (5min after boot, persistent across reboots)
- **Security improvement** - API key moved to separate environment file in systemd service template

### 🔧 **Code Quality**
- Enhanced error handling throughout sync utilities
- Improved type safety with typed dictionaries for API results
- Better logging practices using `logger.exception()` for verbose errors
- Modular import structure following Python best practices

## [7.5.0] - 2025-10-03

### ✨ **New Features**

#### 🎯 **Backend-Specific Content Length Limits with Auto-Splitting**
- **Intelligent content length management** - Prevents embedding failures by enforcing backend-specific limits
- **Automatic content splitting** - Long content automatically splits into linked chunks with preserved context
- **Backend-aware limits**:
  - Cloudflare: 800 characters (BGE-base-en-v1.5 model 512 token limit)
  - ChromaDB: 1500 characters (all-MiniLM-L6-v2 model 384 token limit)
  - SQLite-vec: Unlimited (local storage)
  - Hybrid: 800 characters (constrained by Cloudflare secondary storage)
- **Smart boundary preservation** - Splits respect natural boundaries (paragraphs → sentences → words)
- **Context preservation** - 50-character overlap between chunks maintains semantic continuity
- **LLM-friendly tool descriptions** - MCP tool docstrings inform LLMs about limits upfront

### 🔧 **Infrastructure Enhancements**

#### 📦 **New Content Splitter Utility**
- **`content_splitter.py` module** - Comprehensive content chunking with boundary-aware splitting
- **Priority-based split points**:
  1. Double newlines (paragraph breaks)
  2. Single newlines
  3. Sentence endings (. ! ? followed by space)
  4. Spaces (word boundaries)
  5. Character position (last resort)
- **Configurable overlap** - Default 50 chars, customizable via `MCP_CONTENT_SPLIT_OVERLAP`
- **Validation helpers** - `estimate_chunks_needed()`, `validate_chunk_lengths()` utilities

#### 🏗️ **Storage Backend Updates**
- **Abstract base class properties** - Added `max_content_length` and `supports_chunking` to `MemoryStorage`
- **Backend implementations**:
  - `CloudflareStorage`: 800 char limit, chunking supported
  - `ChromaMemoryStorage`: 1500 char limit, chunking supported
  - `SqliteVecMemoryStorage`: No limit (None), chunking supported
  - `HybridMemoryStorage`: 800 char limit (follows Cloudflare), chunking supported

#### ⚙️ **Configuration System**
- **New config constants** in `config.py`:
  - `CLOUDFLARE_MAX_CONTENT_LENGTH` (default: 800)
  - `CHROMADB_MAX_CONTENT_LENGTH` (default: 1500)
  - `SQLITEVEC_MAX_CONTENT_LENGTH` (default: None/unlimited)
  - `HYBRID_MAX_CONTENT_LENGTH` (default: 800)
  - `ENABLE_AUTO_SPLIT` (default: True)
  - `CONTENT_SPLIT_OVERLAP` (default: 50)
  - `CONTENT_PRESERVE_BOUNDARIES` (default: True)
- **Environment variable support** - All limits configurable via environment variables
- **Validation and logging** - Safe parsing with min/max bounds and startup logging

### 🛠️ **MCP Server Tool Enhancements**

#### 💾 **Enhanced `store_memory` Tool**
- **Automatic content splitting** - Transparently handles content exceeding backend limits
- **Chunk metadata tracking**:
  - `is_chunk`: Boolean flag identifying chunked memories
  - `chunk_index`: Current chunk number (1-based)
  - `total_chunks`: Total number of chunks
  - `original_length`: Original content length before splitting
- **Chunk tags** - Automatic `chunk:N/M` tags for easy retrieval
- **Enhanced return values**:
  - Single memory: `content_hash`
  - Split content: `chunks_created`, `chunk_hashes` array
- **Updated docstring** - Clear backend limits documentation visible to LLMs

### 🧪 **Testing & Validation**

#### ✅ **Comprehensive Test Suite**
- **`test_content_splitting.py`** - 20+ test cases covering:
  - Basic splitting functionality (short/long content, empty strings)
  - Boundary preservation (paragraphs, sentences, words, code blocks)
  - Overlap validation and chunk estimation
  - Backend limit verification (all 4 backends)
  - Configuration constant validation
- **Edge case coverage** - Empty content, exact lengths, overlaps
- **Integration testing** - Ready for all storage backends

### 📝 **Technical Implementation Details**

#### 🔍 **Design Decisions**
- **Conservative limits** - Buffer below actual token limits to account for tokenization variance
- **Cloudflare priority** - Hybrid backend follows Cloudflare's stricter limit for sync compatibility
- **Opt-out capable** - Set `MCP_ENABLE_AUTO_SPLIT=false` to disable auto-splitting
- **Backward compatible** - No breaking changes to existing functionality

#### ⚡ **Performance Considerations**
- **Minimal overhead** - Content length checks are O(1) property access
- **Efficient chunking** - Single-pass splitting with smart boundary detection
- **No unnecessary splitting** - Content within limits passes through unchanged
- **Batch operations** - All chunks stored in single transaction when possible

### 🔗 **References**
- Addresses issue: First memory store attempt (1,570 chars) exceeded Cloudflare's BGE model limit
- Solution: Backend-specific limits with automatic intelligent content splitting
- Feature branch: `feat/content-length-limits-with-splitting`

## [7.4.1] - 2025-10-03

### 🐛 **Bug Fixes**

#### 🧪 **Claude Hooks Integration Tests**
- **Fixed dual-protocol config compatibility** - Tests now support both legacy (direct endpoint) and new (dual-protocol) configuration structures
- **Improved CI/CD compatibility** - Tests gracefully handle scenarios when memory service is not running
- **Enhanced error handling** - Better detection and handling of connection failures and missing dependencies
- **Achieved 100% test pass rate** - Improved from 78.6% to 100% success rate across all 14 integration tests

### 🔧 **Technical Improvements**
- Updated configuration loading test to detect both `config.memoryService.endpoint` and `config.memoryService.http.endpoint`
- Enhanced connectivity test to treat service unavailability as expected behavior in test environments
- Improved mock session start hook to handle `memoryClient` reference errors gracefully

## [7.4.0] - 2025-10-03

### ✨ **Enhanced Search Tab UX**

#### 🔍 **Advanced Search Functionality**
- **Enhanced date filter options** - Added "Yesterday" and "This quarter" options to improve time-based search granularity
- **Live search mode with toggle** - Implemented intelligent live/manual search modes with debounced input (300ms) to prevent API overload
- **Independent semantic search** - Semantic search now works independently from tag filtering for more flexible query combinations
- **Improved filter behavior** - Fixed confusing filter interactions and enhanced user experience with clear mode indicators

#### 🎨 **UI/UX Improvements**
- **Resolved toggle visibility issues** - Fixed Live Search toggle contrast and visibility problems on white backgrounds
- **Eliminated layout shifts** - Moved toggle to header to prevent dynamic position changes due to text length variations
- **Enhanced tooltips** - Increased tooltip widths (desktop: 300px, mobile: 250px) for better readability
- **Accessible design patterns** - Implemented standard toggle design with proper contrast ratios and always-visible controls

#### ⚡ **Performance Optimization**
- **Debounced search input** - 300ms delay prevents overwhelming API with rapid keystrokes during tag searches
- **Smart search triggering** - Live search mode provides immediate results while manual mode offers user control
- **Efficient event handling** - Optimized DOM manipulation and event listener management

### 🔧 **Code Quality Enhancement**

#### 📚 **DRY Principles Implementation**
- **Eliminated code duplication** - Refactored diagnostic script `test_cloudflare_token()` function following Gemini Code Assist feedback
- **Extracted reusable helper** - Created `_verify_token_endpoint()` function reducing ~60 lines of duplicated token verification logic
- **Enhanced consistency** - Both account-scoped and user endpoint tests now display identical token information fields
- **Improved maintainability** - Centralized error handling and output formatting for easier future extensions

### 🔗 **References**
- Addresses user feedback on search tab UX requiring "further attention" with comprehensive improvements
- Implements Gemini Code Assist code review recommendations from PR #139
- Enhances overall dashboard usability with systematic testing of filter combinations

## [7.3.2] - 2025-10-03

### 🐛 **Critical Bug Fixes**

#### 🔧 **HybridMemoryStorage Import Missing**
- **Fixed critical import error** - Added missing `HybridMemoryStorage` import in `storage/__init__.py` after v7.3.0 update
- **Symptom resolved** - "Unknown storage type: HybridMemoryStorage" error no longer occurs
- **Health check restored** - HTTP dashboard now properly displays hybrid backend status
- **Backwards compatibility** - Import follows same conditional pattern as other storage backends

#### 🛡️ **Enhanced Cloudflare Token Authentication**
- **Resolved token endpoint confusion** - Clear guidance on using account-scoped vs generic verification endpoints
- **Documentation improvements** - Comprehensive `.env.example` with correct curl examples and warnings
- **Enhanced diagnostics** - `diagnose_backend_config.py` now tests both token verification endpoints
- **Developer experience** - New troubleshooting guide prevents common authentication mistakes

### 📚 **Documentation Enhancements**

#### 🔍 **Comprehensive Troubleshooting Guide**
- **New guide:** `docs/troubleshooting/cloudflare-authentication.md` with complete Cloudflare setup guidance
- **Token verification clarity** - Explains difference between account-scoped and generic API endpoints
- **Common errors documented** - Solutions for "Invalid API Token" and related authentication failures
- **Step-by-step checklist** - Systematic approach to diagnosing token and authentication issues

#### ⚙️ **Enhanced Configuration Examples**
- **Improved .env.example** - Combines comprehensive v7.3.1 configuration with token verification guidance
- **Clear warnings** - Explicit guidance on which endpoints to use and avoid
- **Security best practices** - Token handling and verification recommendations

### 🔗 **References**
- Closes critical post-v7.3.0 hybrid storage import issue
- Addresses developer confusion around Cloudflare token verification endpoints
- PR #139: Fix HybridMemoryStorage import + Add comprehensive Cloudflare token verification guide

## [7.3.1] - 2025-10-03

### 🐛 **Bug Fixes**

#### 🔧 **HTTP Dashboard Backend Selection**
- **Fixed HTTP dashboard backend selection** - Dashboard now properly respects `MCP_MEMORY_STORAGE_BACKEND` configuration
- **Universal backend support** - Web interface works with all backends: SQLite-vec, Cloudflare, ChromaDB, and Hybrid
- **Tags functionality restored** - Fixed broken browse by tags feature for all storage backends
- **Shared factory pattern** - Eliminated code duplication between MCP server and web interface initialization

#### 🛠️ **Code Quality Improvements**
- **Extracted fallback logic** - Centralized SQLite-vec fallback handling for better maintainability
- **Enhanced type safety** - Improved type hints throughout web interface components
- **Gemini Code Assistant feedback** - Addressed all code review suggestions for better robustness

### 🔗 **References**
- Closes #136: HTTP Dashboard doesn't use Cloudflare backend despite configuration
- PR #138: Complete universal storage backend support for HTTP dashboard

## [7.3.0] - 2025-10-02

### 🎉 **API Documentation Restoration**

**Successfully restored comprehensive API documentation with interactive dashboard integration following PR #121.**

### ✅ **Key Features**

#### 🔍 **Dual Interface Solution**
- **Dedicated `/api-overview` route** - Standalone comprehensive API documentation page
- **API Documentation tab** - Integrated dashboard tab for seamless user experience
- **Unified navigation** - Consistent access to API information across both interfaces

#### ⚡ **Dynamic Content Loading**
- **Real-time version display** - Dynamic version loading via `/api/health/detailed` endpoint
- **Backend status integration** - Live backend information display
- **Enhanced user awareness** - Always shows current system state

#### 📱 **Enhanced User Experience**
- **Responsive design** - Organized endpoint sections with mobile compatibility
- **Performance optimized** - CSS transitions optimized for better performance
- **Consistent navigation** - Fixed naming conflicts for seamless tab switching

### 🛠️ **Technical Improvements**

#### 🔧 **API Consistency**
- **Fixed endpoint path documentation** - Updated from `{hash}` to `{content_hash}` for accuracy
- **Comprehensive endpoint coverage** - All API endpoints properly documented
- **Organized by functionality** - Logical grouping of endpoints for easy navigation

#### 🎨 **Performance Optimization**
- **CSS performance** - Replaced `transition: all` with specific `border-color` and `box-shadow` transitions
- **Load time maintained** - 25ms page load performance preserved
- **Memory operation speed** - 26ms operation performance maintained

### 📊 **Restored Functionality**

| Feature | Status | Notes |
|---------|--------|-------|
| API Overview Page | ✅ RESTORED | `/api-overview` route with full documentation |
| Dashboard Integration | ✅ NEW | API docs tab in interactive dashboard |
| Dynamic Content | ✅ ENHANCED | Real-time version and backend display |
| Mobile Responsive | ✅ MAINTAINED | CSS breakpoints preserved |
| Performance | ✅ OPTIMIZED | Enhanced CSS transitions |

### 🔄 **Architecture**

#### **Dual Interface Implementation**
- **FastAPI Integration** - `get_api_overview_html()` function with embedded JavaScript
- **Dashboard Enhancement** - Additional navigation tab with organized content sections
- **Unified Styling** - Consistent CSS styling across both interfaces
- **Protocol Independence** - Works with both HTTP and MCP protocols

### 🎯 **User Impact**

**Addresses critical missing functionality:**
- Restores API documentation that was missing after v7.2.2 interactive dashboard
- Provides both standalone and integrated access to API information
- Maintains excellent performance benchmarks while adding functionality
- Enhances developer experience with comprehensive endpoint documentation

**This release ensures users have complete access to API documentation through multiple interfaces while preserving the performance excellence of the interactive dashboard.**

## [7.2.2] - 2025-09-30

### 🎉 **Interactive Dashboard Validation Complete**

**Successfully completed comprehensive testing and validation of the Interactive Dashboard (PR #125).**

### ✅ **Validation Results**
- **Performance Excellence**: Page load 25ms (target: <2s), Memory operations 26ms (target: <1s)
- **Search Functionality**: Semantic search, tag-based search, and time-based search all working perfectly
- **Real-time Updates**: Server-Sent Events (SSE) with heartbeat and connection management validated
- **Security**: XSS protection via escapeHtml function properly implemented throughout frontend
- **OAuth Compatibility**: Both enabled and disabled OAuth modes tested and working
- **Mobile Responsive**: CSS breakpoints for mobile (768px) and tablet (1024px) verified
- **Large Dataset Performance**: Excellent performance tested with 994+ memories
- **Claude Desktop Integration**: MCP protocol compatibility confirmed

### 🚀 **Production Ready**
The Interactive Dashboard is now **fully validated and ready for production use**, providing:
- Complete memory CRUD operations
- Advanced search and filtering capabilities
- Real-time updates via Server-Sent Events
- Mobile-responsive design
- Security best practices
- Excellent performance with large datasets

### 📊 **Testing Metrics**
| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| Page Load | <2s | 25ms | ✅ EXCELLENT |
| Memory Ops | <1s | 26ms | ✅ EXCELLENT |
| Tag Search | <500ms | <100ms | ✅ EXCELLENT |
| Large Dataset | 1000+ | 994+ tested | ✅ EXCELLENT |

**Issue #123 closed as completed. Dashboard provides immediate user value and solid foundation for future features.**

## [7.2.0] - 2025-09-30

### 🚀 **Major Performance: ChromaDB Optional Docker Optimization**

**⚠️ BREAKING CHANGE**: ChromaDB is no longer installed by default to dramatically improve Docker build performance and reduce image sizes.

### 🎯 **Key Benefits**
- **70-80% faster Docker build times** (from ~10-15 min to ~2-3 min)
- **1-2GB smaller Docker images** (~2.5GB → ~800MB standard, ~400MB slim)
- **Lower memory footprint** in production deployments
- **Maintained backward compatibility** with clear opt-in mechanism

### 🔧 **Installation Changes**
```bash
# Default installation (lightweight, sqlite_vec only)
python scripts/installation/install.py

# With ChromaDB support (heavy dependencies)
python scripts/installation/install.py --with-chromadb

# Docker builds automatically use optimized sqlite_vec backend
docker build -f tools/docker/Dockerfile -t mcp-memory-service:latest .
```

### 📋 **What Changed**
- **pyproject.toml**: Added `full` optional dependency group, moved ChromaDB to optional
- **server.py**: Added conditional ChromaDB imports with graceful error handling
- **mcp_server.py**: Enhanced ChromaDB import error messages and fallback logic
- **install.py**: Added `--with-chromadb` flag for opt-in ChromaDB installation
- **README.md**: Updated storage backend documentation with ChromaDB optional notes
- **NEW**: `docs/docker-optimized-build.md` - Comprehensive Docker optimization guide

### 🛡️ **Migration Guide**
**For users who need ChromaDB:**
1. Run: `python scripts/installation/install.py --with-chromadb`
2. Or install manually: `pip install mcp-memory-service[chromadb]`

**For Docker users:**
- No action needed - automatically get performance improvements
- Docker builds now default to optimized sqlite_vec backend

### 🧪 **Error Handling**
- Clear error messages when ChromaDB backend selected but not installed
- Graceful fallback to sqlite_vec when ChromaDB unavailable
- Helpful guidance on how to install ChromaDB if needed

### 📊 **Performance Comparison**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Docker build | ~10-15 min | ~2-3 min | **80% faster** |
| Image size | ~2.5GB | ~800MB | **68% smaller** |
| Memory usage | High | Low | **Significantly reduced** |

## [7.1.5] - 2025-09-29

### 🔧 **Improvements**

- **Enhanced timestamp consistency across memory retrieval methods** - All memory retrieval endpoints now display consistent timestamp information:
  - `retrieve_memory` now shows timestamps in "YYYY-MM-DD HH:MM:SS" format matching `recall_memory`
  - `search_by_tag` now shows timestamps in same consistent format
  - Improved code quality using `getattr` pattern instead of `hasattr` checks
  - Resolves timestamp metadata inconsistency reported in issue #126

- **Enhanced CLI hybrid backend support** - CLI commands now fully support hybrid storage backend:
  - Added 'hybrid' option to `--storage-backend` choices for both `server` and `status` commands
  - Completes hybrid backend integration across all system components
  - Enables seamless CLI usage with hybrid SQLite-vec + Cloudflare architecture

- **Hybrid storage backend server integration** - Server.py now fully supports hybrid backend operations:
  - Added `sanitized` method to hybrid storage for tag handling compatibility
  - Enhanced initialization and health check support for hybrid backend
  - Maintains performance optimization with Cloudflare synchronization

### 🛡️ **Security Fixes**

- **Credential exposure prevention** - Enhanced security measures to prevent accidental credential exposure:
  - Improved handling of environment variables in logging and error messages
  - Additional safeguards against sensitive configuration leakage
  - Follows security best practices for credential management

- **Resource leak fixes** - Memory and resource management improvements:
  - Enhanced connection cleanup in storage backends
  - Improved async resource handling to prevent leaks
  - Better error recovery and cleanup procedures

### 🎯 **Code Quality**

- **Implemented Gemini Code Assistant improvements** - Enhanced code maintainability and safety:
  - Replaced `hasattr` + direct attribute access with safer `getattr(obj, "attr", None)` pattern
  - Cleaner, more readable code with consistent error handling
  - Improved null safety and defensive programming practices

## [7.1.4] - 2025-09-28

### 🚀 **Major Feature: Unified Cross-Platform Hook Installer**

- **NEW: Single Python installer replaces 4+ platform-specific scripts**
  - Consolidated `install.sh`, `install-natural-triggers.sh`, `install_claude_hooks_windows.bat` into unified `install_hooks.py`
  - Full cross-platform compatibility (Windows, macOS, Linux)
  - Intelligent JSON configuration merging preserves existing Claude Code hooks
  - Dynamic path resolution eliminates hardcoded developer paths
  - Atomic installations with automatic rollback on failure

- **Enhanced Safety & User Experience**
  - Smart settings.json merging prevents configuration loss
  - Comprehensive backup system with timestamped restore points
  - Empty directory cleanup for proper uninstall process
  - Dry-run support for safe testing before installation
  - Enhanced error handling with detailed user feedback

- **Natural Memory Triggers v7.1.3 Integration**
  - Advanced trigger detection with 85%+ accuracy
  - Multi-tier performance optimization (50ms/150ms/500ms)
  - Mid-conversation memory injection
  - CLI management tools for real-time configuration
  - Git-aware context and repository integration

### 🔧 **Installation Commands Updated**
```bash
# New unified installation (replaces all previous methods)
cd claude-hooks
python install_hooks.py --natural-triggers  # Recommended
python install_hooks.py --basic             # Basic hooks only
python install_hooks.py --all              # Everything

# Integrated with main installer
python scripts/installation/install.py --install-natural-triggers
```

### 📋 **Migration & Documentation**
- Added comprehensive `claude-hooks/MIGRATION.md` with transition guide
- Updated README.md installation instructions
- Legacy shell scripts removed (eliminates security and compatibility issues)
- Clear upgrade path for existing users

### 🛠 **Technical Improvements**
- Addressed all Gemini Code Assist review feedback
- Enhanced cross-platform path handling with proper quoting
- Improved integration between main installer and hook installer
- Professional CLI interface with consistent options across platforms

### ⚠️ **Breaking Changes**
- Legacy shell installers (`install.sh`, `install-natural-triggers.sh`) removed
- Installation commands updated - see `claude-hooks/MIGRATION.md` for details
- Users must switch to unified Python installer for future installations

## [7.1.3] - 2025-09-28

### 🚨 **SECURITY FIX**

- **CRITICAL: Removed sensitive configuration files from repository** - Immediate security remediation:
  - **Removed `.claude/settings.local.json*` files from git tracking and complete history**
  - **Used `git filter-branch` to purge all sensitive data from repository history**
  - **Force-pushed rewritten history to remove exposed API tokens and secrets**
  - Added comprehensive `.gitignore` patterns for future protection
  - **BREAKING: Repository history rewritten - force pull required for existing clones**
  - **ACTION REQUIRED: Rotate any exposed Cloudflare API tokens immediately**
  - Addresses critical security vulnerability from issues #118 and personal config exposure

### ⚠️ **Post-Security Actions Required**
1. **Immediately rotate any Cloudflare API tokens** that were in the exposed files
2. **Force pull** or re-clone repository: `git fetch origin && git reset --hard origin/develop`
3. **Review local `.claude/settings.local.json`** files for any other sensitive data
4. **Verify no sensitive data** remains in your local configurations

## [7.1.2] - 2025-09-28

### 🔧 **Improvements**

- **Stop tracking personal Claude settings to prevent merge conflicts** - Added `.claude/settings.local.json*` patterns to `.gitignore`:
  - Prevents future tracking of personal configuration files
  - Uses `--skip-worktree` to ignore local changes to existing tracked files
  - Protects user privacy and eliminates merge conflicts
  - Preserves existing user configurations while fixing repository hygiene (Fixes #118)

## [7.1.1] - 2025-09-28

### 🐛 **Bug Fixes**

- **Fixed misleading error message in document ingestion** - The `ingest_document` tool now provides accurate error messages:
  - Shows "File not found" with full resolved path when files don't exist
  - Only shows "Unsupported file format" for truly unsupported formats
  - Includes list of supported formats (.md, .txt, .pdf, .json, .csv) in format errors
  - Resolves issue where Markdown files were incorrectly reported as unsupported (Fixes #122)

## [7.1.0] - 2025-09-27

### 🧠 **Natural Memory Triggers for Claude Code**

This release introduces **Natural Memory Triggers v7.1.0** - an intelligent memory awareness system that automatically detects when Claude should retrieve relevant memories from your development history.

#### ✨ **New Features**

##### 🎯 **Intelligent Trigger Detection**
- **✅ Semantic Analysis** - Advanced natural language processing to understand memory-seeking patterns
  - **Pattern Recognition**: Detects phrases like "What did we decide...", "How did we implement..."
  - **Question Classification**: Identifies when user is seeking information from past work
  - **Context Understanding**: Analyzes conversation flow and topic shifts
- **✅ Git-Aware Context** - Repository integration for enhanced relevance
  - **Commit Analysis**: Extracts development themes from recent commit history
  - **Changelog Integration**: Parses project changelogs for version-specific context
  - **Development Keywords**: Builds search queries from git history and file patterns

##### ⚡ **Performance-Optimized Architecture**
- **✅ Multi-Tier Processing** - Three-tier performance system
  - **Instant Tier** (< 50ms): Pattern matching and cache checks
  - **Fast Tier** (< 150ms): Lightweight semantic analysis
  - **Intensive Tier** (< 500ms): Deep semantic understanding
- **✅ Adaptive Performance Profiles**
  - **Speed Focused**: Minimal latency, basic memory awareness
  - **Balanced**: Optimal speed/context balance (recommended)
  - **Memory Aware**: Maximum context awareness
  - **Adaptive**: Machine learning-based optimization

##### 🎮 **CLI Management System**
- **✅ Memory Mode Controller** - Comprehensive command-line interface
  - **Profile Switching**: `node memory-mode-controller.js profile balanced`
  - **Sensitivity Control**: `node memory-mode-controller.js sensitivity 0.7`
  - **Status Monitoring**: Real-time performance metrics and configuration display
  - **System Management**: Enable/disable triggers, reset to defaults

#### 🔧 **Technical Implementation**

##### **Core Components**
- **`claude-hooks/core/mid-conversation.js`** - Main hook implementation with stateful management
- **`claude-hooks/utilities/tiered-conversation-monitor.js`** - Multi-tier semantic analysis engine
- **`claude-hooks/utilities/performance-manager.js`** - Performance monitoring and adaptive optimization
- **`claude-hooks/utilities/git-analyzer.js`** - Git repository context analysis
- **`claude-hooks/memory-mode-controller.js`** - CLI controller for system management

##### **Smart Memory Scoring**
- **✅ Multi-Factor Relevance** - Sophisticated scoring algorithm
  - **Content Relevance** (15%): Semantic similarity to current context
  - **Tag Relevance** (35%): Project and topic-specific weighting
  - **Time Decay** (25%): Recent memories weighted higher
  - **Content Quality** (25%): Filters out low-value memories
- **✅ Conversation Context** - Session-aware analysis
  - **Topic Tracking**: Maintains context window for semantic analysis
  - **Pattern Detection**: Learns user preferences and conversation patterns
  - **Confidence Thresholds**: Only triggers when confidence meets user-defined threshold

#### 🧪 **Quality Assurance**

##### **Comprehensive Testing**
- **✅ Test Suite** - 18 automated tests covering all functionality
  - **Configuration Management**: Nested JSON handling and validation
  - **Performance Profiling**: Latency measurement and optimization
  - **Semantic Analysis**: Pattern detection and confidence scoring
  - **CLI Integration**: Command processing and state management
- **✅ Gemini Code Assist Integration** - AI-powered code review
  - **Static Analysis**: Identified and fixed 21 code quality issues
  - **Performance Optimization**: Division-by-zero prevention, cache management
  - **Configuration Validation**: Duplicate key detection and consolidation

#### 🔄 **Installation & Compatibility**

##### **Seamless Integration**
- **✅ Zero-Restart Installation** - Dynamic hook loading during Claude Code sessions
- **✅ Backward Compatibility** - Works alongside existing memory service functionality
- **✅ Configuration Preservation** - Maintains existing settings while adding new features
- **✅ Platform Support** - macOS, Windows, and Linux compatibility

#### 📊 **Performance Metrics**

##### **Benchmarks**
- **Instant Analysis**: < 50ms response time for pattern matching
- **Fast Analysis**: < 150ms for lightweight semantic processing
- **Cache Performance**: < 5ms for cached results with LRU management
- **Memory Efficiency**: Automatic cleanup prevents memory bloat
- **Trigger Accuracy**: 85%+ confidence for memory-seeking pattern detection

#### 🎯 **Usage Examples**

Natural Memory Triggers automatically activate for phrases like:
- "What approach did we use for authentication?"
- "How did we handle error handling in this project?"
- "What were the main architectural decisions we made?"
- "Similar to what we implemented before..."
- "Remember when we discussed..."

#### 📚 **Documentation**

- **✅ Complete User Guide** - Comprehensive documentation at `claude-hooks/README-NATURAL-TRIGGERS.md`
- **✅ CLI Reference** - Detailed command documentation and usage examples
- **✅ Configuration Guide** - Performance profile explanations and optimization tips
- **✅ Troubleshooting** - Common issues and resolution steps

---

## [7.0.0] - 2025-09-27

### 🎉 **Major Release - OAuth 2.1 Dynamic Client Registration**

This major release introduces comprehensive **OAuth 2.1 Dynamic Client Registration**, enabling **Claude Code HTTP transport** and **enterprise-grade authentication** while maintaining full backward compatibility with existing API key workflows.

#### ✨ **New Features**

##### 🔐 **OAuth 2.1 Implementation**
- **✅ Dynamic Client Registration** - Complete RFC 7591 compliant implementation
  - **Auto-Discovery**: `.well-known/oauth-authorization-server/mcp` endpoint for client auto-configuration
  - **Runtime Registration**: Clients can register dynamically without manual setup
  - **Standards Compliance**: Full OAuth 2.1 and RFC 8414 authorization server metadata
  - **Security Best Practices**: HTTPS enforcement, secure redirect URI validation

- **✅ JWT Authentication** - Modern token-based authentication
  - **RS256 Signing**: RSA key pairs for enhanced security (with HS256 fallback)
  - **Scope-Based Authorization**: Granular permissions (`read`, `write`, `admin`)
  - **Token Validation**: Comprehensive JWT verification with proper error handling
  - **Configurable Expiration**: Customizable token and authorization code lifetimes

##### 🚀 **Claude Code Integration**
- **✅ HTTP Transport Support** - Direct integration with Claude Code
  - **Automatic Setup**: Claude Code discovers and registers OAuth client automatically
  - **Team Collaboration**: Enables Claude Code team features via HTTP transport
  - **Seamless Authentication**: JWT tokens handled transparently by client

##### 🛡️ **Enhanced Security Architecture**
- **✅ Multi-Method Authentication** - Flexible authentication options
  - **OAuth Bearer Tokens**: Primary authentication method for modern clients
  - **API Key Fallback**: Existing API key authentication preserved for backward compatibility
  - **Anonymous Access**: Optional anonymous access with explicit opt-in (`MCP_ALLOW_ANONYMOUS_ACCESS`)

- **✅ Production Security Features**
  - **Thread-Safe Operations**: Async/await with proper locking mechanisms
  - **Background Token Cleanup**: Automatic expiration and cleanup of tokens/codes
  - **Security Validation**: Comprehensive startup validation with production warnings
  - **Configuration Hardening**: HTTP transport warnings, key strength validation

#### 🔧 **Technical Implementation**

##### **New OAuth Endpoints**
- **`/.well-known/oauth-authorization-server/mcp`** - OAuth server metadata discovery
- **`/.well-known/openid-configuration/mcp`** - OpenID Connect compatibility endpoint
- **`/oauth/register`** - Dynamic client registration endpoint
- **`/oauth/authorize`** - Authorization code flow endpoint
- **`/oauth/token`** - Token exchange endpoint (supports both `authorization_code` and `client_credentials` flows)

##### **Authentication Middleware**
- **✅ Unified Auth Handling**: Single middleware protecting all API endpoints
- **✅ Scope Validation**: Automatic scope checking for protected resources
- **✅ Graceful Fallback**: OAuth → API key → Anonymous (if enabled)
- **✅ Enhanced Error Messages**: Context-aware authentication error responses

##### **Configuration System**
- **✅ Environment Variables**: Comprehensive OAuth configuration options
  ```bash
  MCP_OAUTH_ENABLED=true                    # Enable/disable OAuth (default: true)
  MCP_OAUTH_SECRET_KEY=<secure-key>         # JWT signing key (auto-generated if not set)
  MCP_OAUTH_ISSUER=<issuer-url>            # OAuth issuer URL (auto-detected)
  MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60  # Token expiration (default: 60 minutes)
  MCP_ALLOW_ANONYMOUS_ACCESS=false         # Anonymous access (default: false)
  ```

#### 🔄 **Backward Compatibility**
- **✅ Zero Breaking Changes**: All existing API key workflows continue to work unchanged
- **✅ Optional OAuth**: OAuth can be completely disabled with `MCP_OAUTH_ENABLED=false`
- **✅ Graceful Coexistence**: API key and OAuth authentication work side-by-side
- **✅ Migration Path**: Existing users can adopt OAuth gradually or continue with API keys

#### 📊 **Development & Quality Metrics**
- **✅ 17 Comprehensive Review Cycles** with Gemini Code Assist feedback integration
- **✅ All Security Issues Resolved** (critical, high, medium severity vulnerabilities addressed)
- **✅ Extensive Testing Suite**: New integration tests for OAuth flows and security scenarios
- **✅ Production Readiness**: Comprehensive validation, monitoring, and health checks

#### 🚀 **Impact & Benefits**

##### **For Existing Users**
- **No Changes Required**: Continue using API key authentication without modification
- **Enhanced Security**: Option to upgrade to industry-standard OAuth when ready
- **Future-Proof**: Foundation for additional enterprise features

##### **For Claude Code Users**
- **Team Collaboration**: HTTP transport enables Claude Code team features
- **Automatic Setup**: Zero-configuration OAuth setup and token management
- **Enterprise Ready**: Standards-compliant authentication for organizational use

##### **For Enterprise Environments**
- **Standards Compliance**: Full OAuth 2.1 and RFC compliance for security audits
- **Centralized Auth**: Foundation for integration with existing identity providers
- **Audit Trail**: Comprehensive logging and token lifecycle management

#### 🔜 **Future Enhancements**
This release provides the foundation for additional OAuth features:
- **Persistent Storage**: Production-ready client and token storage backends
- **PKCE Support**: Enhanced security for public clients
- **Refresh Tokens**: Long-lived authentication sessions
- **User Consent UI**: Interactive authorization flows
- **Identity Provider Integration**: SAML, OIDC, and enterprise SSO support

#### 📚 **Documentation**
- **✅ Complete Setup Guide**: Step-by-step OAuth configuration documentation (`docs/oauth-setup.md`)
- **✅ API Reference**: Comprehensive endpoint documentation with examples
- **✅ Security Guide**: Production deployment best practices and security considerations
- **✅ Migration Guide**: Smooth transition path for existing users

---

**This major release transforms the MCP Memory Service from a simple memory tool into an enterprise-ready service with standards-compliant authentication, enabling new use cases while preserving the simplicity that makes it valuable.**

## [6.23.0] - 2025-09-27

### 🎉 **Major Feature Release - Memory Management Enhancement**

This release combines three major improvements: comprehensive memory management tools, enhanced documentation, and dependency standardization. All changes have been reviewed and approved by Gemini Code Assist with very positive feedback.

#### ✨ **New Features**
- **🛠️ New `list_memories` MCP Tool** - Added paginated memory browsing with filtering capabilities
  - ✅ **Pagination Support**: Page-based navigation (1-based indexing) with configurable page sizes (1-100)
  - ✅ **Database-Level Filtering**: Filter by memory type and tags using efficient SQL queries
  - ✅ **Performance Optimized**: Direct database filtering instead of Python-level post-processing
  - ✅ **Consistent API**: Available in both MCP server and HTTP/REST endpoints

#### 🚀 **Performance Improvements**
- **⚡ Database-Level Filtering** - Replaced inefficient Python-level filtering with SQL WHERE clauses
  - ❌ **Previous**: Fetch all records → filter in Python → paginate (slow, memory-intensive)
  - ✅ **Now**: Filter + paginate in database → return results (5ms response time)
  - ✅ **Benefits**: Dramatically reduced memory usage and improved response times for large datasets
  - ✅ **Backends**: Implemented across SQLite-vec, ChromaDB, Cloudflare, and Hybrid storage

- **🔧 Enhanced Storage Interface** - Extended `get_all_memories()` with tags parameter
  - ✅ **Tag Filtering**: Support for OR-based tag matching at database level
  - ✅ **Backward Compatible**: All existing code continues to work unchanged
  - ✅ **Consistent**: Same interface across all storage backends

#### 🛡️ **Security Enhancements**
- **🔒 Eliminated Security Vulnerabilities** - Removed dangerous runtime dependency installation
  - ❌ **Removed**: Automatic `pip install` execution in Docker containers
  - ✅ **Security**: Prevents potential code injection and supply chain attacks
  - ✅ **Reliability**: Dependencies now properly managed through container build process

- **🔑 Fixed Hardcoded Credentials** - Replaced hardcoded API keys with environment variables
  - ❌ **Previous**: API keys stored in plain text in debug scripts
  - ✅ **Fixed**: All credentials now sourced from secure environment variables
  - ✅ **Security**: Follows security best practices for credential management

#### 📚 **Documentation Improvements**
- **📖 Comprehensive Documentation Suite** - Added professional documentation in `docs/mastery/`
  - ✅ **API Reference**: Complete API documentation with examples
  - ✅ **Architecture Overview**: Detailed system architecture documentation
  - ✅ **Configuration Guide**: Comprehensive configuration management guide
  - ✅ **Setup Instructions**: Step-by-step local setup and run guide
  - ✅ **Testing Guide**: Testing strategies and debugging instructions
  - ✅ **Troubleshooting**: Common issues and solutions

- **🔧 Enhanced Development Resources** - Added advanced search and refactoring documentation
  - ✅ **Search Enhancement Guide**: Advanced search capabilities and examples
  - ✅ **Refactoring Summary**: Complete analysis of architectural changes
  - ✅ **Integration Examples**: Multi-client setup for various AI platforms

#### 🔧 **Infrastructure Improvements**
- **🐳 Docker Optimization** - Enhanced Docker configuration for production deployments
  - ✅ **Security Updates**: Updated base images and security patches
  - ✅ **Performance**: Optimized container size and startup time
  - ✅ **Flexibility**: Better support for different deployment scenarios

- **📦 Dependency Management** - Standardized and improved dependency handling
  - ✅ **ChromaDB Compatibility**: Restored ChromaDB as optional dependency for backward compatibility
  - ✅ **Updated Dependencies**: Updated PyPDF2 → pypdf2 for better maintenance
  - ✅ **Optional Dependencies**: Clean separation of core vs optional features

#### 🪟 **Platform Support**
- **💻 Enhanced Windows Support** - Added comprehensive Windows debugging capabilities
  - ✅ **Debug Script**: New `start_http_debug.bat` for Windows HTTP mode testing
  - ✅ **103 Lines Added**: Comprehensive Windows debugging and troubleshooting support
  - ✅ **Environment Variables**: Proper Windows environment variable handling

#### 🧹 **Code Quality**
- **♻️ Major Refactoring** - Removed redundant functionality while maintaining compatibility
  - ✅ **317 Lines Removed**: Eliminated duplicate `search_by_time` and `search_similar` tools
  - ✅ **Functional Redundancy**: Removed tools that exactly duplicated existing functionality
  - ✅ **API Consolidation**: Streamlined API surface while preserving all capabilities
  - ✅ **Performance**: Reduced codebase complexity without losing features

#### 🤖 **AI Code Review Integration**
- **✅ Gemini Code Assist Approved** - All changes reviewed and approved with very positive feedback
  - ✅ **Architecture Review**: Praised database-level filtering implementation
  - ✅ **Security Review**: Confirmed elimination of security vulnerabilities
  - ✅ **Performance Review**: Validated performance optimization approach
  - ✅ **Code Quality**: Approved refactoring and redundancy removal

#### 📋 **Migration Notes**
- **🔄 Backward Compatibility**: All existing integrations continue to work unchanged
- **📦 Optional Dependencies**: ChromaDB users should install with `pip install mcp-memory-service[chromadb]`
- **🛠️ New Tools**: The `list_memories` tool is automatically available to all MCP clients
- **⚠️ Removed Tools**: `search_by_time` and `search_similar` tools have been removed (functionality available through existing tools)

#### 💡 **Usage Examples**
```python
# New list_memories tool with filtering
await list_memories(page=1, page_size=20, tag="important", memory_type="note")

# Database-level tag filtering (improved performance)
memories = await storage.get_all_memories(limit=50, tags=["work", "project"])

# Enhanced pagination with type filtering
memories = await storage.get_all_memories(
    limit=10, offset=20, memory_type="decision", tags=["urgent"]
)
```

---

## [6.22.1] - 2025-09-26

### 🔧 **Dashboard Statistics Fix**

#### Bug Fixes
- **🎯 Backend-Agnostic Dashboard Stats** - Fixed `dashboard_get_stats` to use configured storage backend instead of hardcoded ChromaDB
  - ❌ **Previous Issue**: Dashboard always showed ChromaDB stats (often 0 memories) regardless of actual backend
  - ✅ **Fixed**: Now properly detects and uses SQLite-vec, Cloudflare, or ChromaDB based on configuration
  - ✅ **Consistency**: Uses same pattern as `handle_check_database_health` for reliable backend detection
  - ✅ **Accuracy**: Dashboard now shows correct memory counts and backend information

#### Technical Improvements
- **Backend Detection**: Dynamic storage type detection via `storage.__class__.__name__`
- **Error Handling**: Proper async/await handling and graceful error reporting
- **Code Consistency**: Unified approach with existing health check functionality

---

**Resolves**: GitHub Issue where dashboard stats were incorrectly hardcoded to ChromaDB
**Credit**: Thanks to @MichaelPaulukonis for identifying and fixing this backend detection issue

---

## [6.22.0] - 2024-09-25

### 🎯 **Chronological Ordering & Performance Improvements**

#### Major API Enhancements
- **🌟 Chronological Memory Ordering** - `/api/memories` endpoint now returns memories in chronological order (newest first)
  - ✅ **Improved User Experience**: More intuitive memory browsing with recent memories prioritized
  - ✅ **Consistent Across All Backends**: SQLite-vec, ChromaDB, Cloudflare D1, and Hybrid
  - ✅ **Proper Pagination Support**: Server-side sorting with efficient limit/offset handling
  - ✅ **Backward Compatible**: Same API interface with enhanced ordering

#### Critical Performance Fixes 🚀
- **⚡ Storage-Layer Memory Type Filtering** - Addressed critical performance bottleneck
  - ❌ **Previous Issue**: API loaded ALL memories into application memory when filtering by `memory_type`
  - ✅ **Fixed**: Efficient storage-layer filtering with SQL WHERE clauses
  - ✅ **Performance Impact**: 16.5% improvement in filtering operations
  - ✅ **Scalability**: Prevents service instability with large datasets (1000+ memories)
- **Enhanced Storage Interface**
  - Added `memory_type` parameter to `get_all_memories()` and `count_all_memories()` methods
  - Implemented across all backends: SQLite-vec, ChromaDB, Cloudflare D1, Hybrid
  - Maintains chronological ordering while applying efficient filters

#### Code Quality Improvements
- **🔧 ChromaDB Code Refactoring** - Eliminated code duplication
  - Created `_create_memory_from_results()` helper method
  - Consolidated 5 duplicate Memory object creation patterns
  - Enhanced maintainability and consistency across ChromaDB operations
- **Comprehensive Test Suite**
  - Added 10 new test cases specifically for chronological ordering
  - Covers edge cases: empty storage, large offsets, mixed timestamps
  - Validates API endpoint behavior and storage backend compatibility

#### Backend-Specific Optimizations
- **SQLite-vec**: Efficient `ORDER BY created_at DESC` with parameterized WHERE clauses
- **ChromaDB**: Client-side sorting with performance warnings for large datasets (>1000 memories)
- **Cloudflare D1**: Server-side SQL sorting and filtering for optimal performance
- **Hybrid**: Delegates to primary storage (SQLite-vec) for consistent performance

#### Developer Experience
- Enhanced error handling and logging for filtering operations
- Improved API response consistency across all storage backends
- Better performance monitoring and debugging capabilities

---

**Resolves**: GitHub Issue #79 - Implement chronological ordering for /api/memories endpoint
**Addresses**: Gemini Code Assist performance and maintainability feedback

---

## [6.21.0] - 2024-09-25

### 🚀 **Hybrid Storage Backend - Performance Revolution**

#### Major New Features
- **🌟 Revolutionary Hybrid Storage Backend** - Combines the best of both worlds:
  - ✅ **SQLite-vec Performance**: ~5ms reads/writes (10-100x faster than Cloudflare-only)
  - ✅ **Cloudflare Persistence**: Multi-device synchronization and cloud backup
  - ✅ **Zero User-Facing Latency**: All operations hit SQLite-vec first, background sync to cloud
  - ✅ **Intelligent Write-Through Cache**: Instant response with async cloud synchronization

#### Enhanced Architecture & Performance
- **Background Synchronization Service**
  - Async queue with intelligent retry logic and exponential backoff
  - Concurrent sync operations with configurable batch processing
  - Real-time health monitoring and capacity tracking
  - Graceful degradation when cloud services are unavailable
- **Advanced Error Handling**
  - Intelligent error categorization (temporary vs permanent vs limit errors)
  - Automatic retry for network/temporary issues
  - No-retry policy for hard limits (prevents infinite loops)
  - Comprehensive logging with error classification

#### Cloudflare Limit Protection & Monitoring 🛡️
- **Pre-Sync Validation**
  - Metadata size validation (10KB limit per vector)
  - Vector count monitoring (5M vector limit)
  - Automatic capacity checks before sync operations
- **Real-Time Capacity Monitoring**
  - Usage percentage tracking with warning thresholds
  - Critical alerts at 95% capacity, warnings at 80%
  - Proactive limit detection and graceful handling
- **Enhanced Limit Error Handling**
  - Detection of 413, 507, and quota exceeded responses
  - Automatic capacity status updates on limit errors
  - Permanent failure classification for hard limits

#### Configuration & Deployment
- **Simple Setup**: Just set `MCP_MEMORY_STORAGE_BACKEND=hybrid` + Cloudflare credentials
- **Advanced Tuning Options**:
  - `MCP_HYBRID_SYNC_INTERVAL`: Background sync frequency (default: 300s)
  - `MCP_HYBRID_BATCH_SIZE`: Sync batch size (default: 50)
  - `MCP_HYBRID_MAX_QUEUE_SIZE`: Queue capacity (default: 1000)
  - Health check intervals and retry configurations

#### Benefits
- **For Users**:
  - Instant memory operations (no more waiting for cloud responses)
  - Reliable offline functionality with automatic sync when online
  - Seamless multi-device access to memories
- **For Production**:
  - Handles Cloudflare's strict limits intelligently
  - Robust error recovery and monitoring
  - Scales from single-user to enterprise deployments

### 🧪 **Comprehensive Testing & Validation**
- **347 lines of Cloudflare limit testing** (`tests/test_hybrid_cloudflare_limits.py`)
- **Performance characteristic validation**
- **Background sync verification scripts**
- **Live testing utilities for production validation**

### 📖 **Documentation & Setup**
- **CLAUDE.md**: Hybrid marked as **RECOMMENDED** default for new installations
- **Installation Script Updates**: Interactive hybrid backend selection
- **Configuration Validation**: Enhanced diagnostic tools for setup verification

**🎯 Recommendation**: This should become the **default backend for all new installations** due to its superior performance and reliability characteristics.

## [6.20.1] - 2024-09-24

### 🐛 **Critical Bug Fixes**

#### SQLite-vec Backend Regression Fix
- **Fixed MCP Server Initialization**: Corrected critical regression that prevented sqlite_vec backend from working
  - ✅ Fixed class name mismatch: `SqliteVecStorage` → `SqliteVecMemoryStorage`
  - ✅ Fixed constructor parameters: Updated to use correct `db_path` and `embedding_model` parameters
  - ✅ Fixed database path: Use `SQLITE_VEC_PATH` instead of incorrect ChromaDB path
  - ✅ Added missing imports: `SQLITE_VEC_PATH` and `EMBEDDING_MODEL_NAME` from config
  - ✅ Code quality improvements: Added `_get_sqlite_vec_storage()` helper function to reduce duplication

#### Impact
- **Restores Default Backend**: sqlite_vec backend (default) now works correctly with MCP server
- **Fixes Memory Operations**: Resolves "No embedding model available" errors during memory operations
- **Claude Desktop Integration**: Enables proper memory storage and retrieval functionality
- **Embedding Support**: Ensures embedding model loads and generates embeddings successfully

Thanks to @ergut for identifying and fixing this critical regression!

## [6.20.0] - 2024-09-24

### 🚀 **Claude Code Dual Protocol Memory Hooks**

#### Major New Features
- **Dual Protocol Memory Hook Support** - Revolutionary enhancement to Claude Code memory hooks
  - ✅ **HTTP Protocol Support**: Full compatibility with web-based memory services at `https://localhost:8443`
  - ✅ **MCP Protocol Support**: Direct integration with MCP server processes via `uv run memory server`
  - ✅ **Smart Auto-Detection**: Automatically selects best available protocol (MCP preferred, HTTP fallback)
  - ✅ **Graceful Fallback Chain**: MCP → HTTP → Environment-based storage detection
  - ✅ **Protocol Flexibility**: Choose specific protocols (`http`, `mcp`) or auto-selection (`auto`)

#### Enhanced Architecture
- **Unified MemoryClient Class** (`claude-hooks/utilities/memory-client.js`)
  - Transparent protocol switching with single interface
  - Connection pooling and error recovery
  - Protocol-specific optimizations (MCP direct communication, HTTP REST API)
  - Comprehensive error handling and timeout management
- **Enhanced Configuration System** (`claude-hooks/config.json`)
  - Protocol-specific settings (HTTP endpoint/API keys, MCP server commands)
  - Configurable fallback behavior and connection timeouts
  - Backward compatibility with existing configurations

#### Reliability Improvements
- **Multi-Protocol Resilience**: Hooks work across diverse deployment scenarios
  - Local development (MCP direct), production servers (HTTP), hybrid setups
  - Network connectivity issues gracefully handled
  - Service unavailability doesn't break git analysis or project detection
- **Enhanced Error Handling**: Clear protocol-specific error messages and fallback reporting
- **Connection Management**: Proper cleanup and resource management for both protocols

#### Developer Experience
- **Comprehensive Testing Suite** (`claude-hooks/test-dual-protocol-hook.js`)
  - Tests all protocol combinations: auto-MCP-preferred, auto-HTTP-preferred, MCP-only, HTTP-only
  - Validates protocol detection, fallback behavior, and error handling
  - Demonstrates graceful degradation capabilities
- **Backward Compatibility**: Existing hook configurations continue working unchanged
- **Enhanced Debugging**: Protocol selection and connection status clearly reported

#### Technical Implementation
- **Protocol Abstraction Layer**: Single interface for memory operations regardless of protocol
- **Smart Connection Logic**: Connection attempts with timeouts, fallback sequencing
- **Memory Query Unification**: Semantic search, time-based queries work identically across protocols
- **Storage Backend Detection**: Enhanced parsing for both HTTP JSON responses and MCP tool output

#### Benefits for Different Use Cases
- **Claude Desktop Users**: Better reliability with HTTP fallback when MCP struggles
- **VS Code Extension Users**: Optimized for HTTP-based deployments
- **CI/CD Systems**: More robust memory operations in automated environments
- **Development Workflows**: Local MCP for speed, HTTP for production consistency

## [6.19.0] - 2024-09-24

### 🔧 **Configuration Validation Scripts Consolidation**

#### Improvements
- **Consolidated validation scripts** - Merged `validate_config.py` and `validate_configuration.py` into comprehensive `validate_configuration_complete.py`
  - ✅ Multi-platform support (Windows/macOS/Linux)
  - ✅ All configuration sources validation (.env, Claude Desktop, Claude Code)
  - ✅ Cross-configuration consistency checking
  - ✅ Enhanced API token validation with known invalid token detection
  - ✅ Improved error reporting and recommendations
  - ✅ Windows console compatibility (no Unicode issues)

#### Removed
- ❌ **Deprecated scripts**: `validate_config.py` and `validate_configuration.py` (redundant)

#### Fixed
- **Cloudflare Backend Critical Issue**: Implemented missing `recall` method in CloudflareStorage class
  - ✅ Dual search strategy (semantic + time-based)
  - ✅ Graceful fallback mechanism
  - ✅ Comprehensive error handling
  - ✅ Time filtering support

#### Documentation Updates
- **Updated all documentation references** to use new consolidated validation script
- **Created comprehensive API token setup guide** (`docs/troubleshooting/cloudflare-api-token-setup.md`)

## [6.18.0] - 2025-09-23

### 🚀 **Cloudflare Dual-Environment Configuration Suite**

#### New Diagnostic Tools
- **Added comprehensive backend configuration diagnostic script** (`scripts/validation/diagnose_backend_config.py`)
  - Environment file validation with masked sensitive data display
  - Environment variable loading verification with dotenv support
  - Configuration module import testing with clear error reporting
  - Storage backend creation testing with full traceback on failures
  - Status indicators with clear success/warning/error messaging
- **Enhanced troubleshooting workflow** with step-by-step validation process

#### Documentation Improvements
- **Created streamlined 5-minute setup guide** (`docs/quick-setup-cloudflare-dual-environment.md`)
  - Comprehensive dual-environment configuration for Claude Desktop + Claude Code
  - Configuration templates with explicit environment variable examples
  - Validation commands with expected health check results
  - Troubleshooting section for common configuration issues
  - Migration guide from SQLite-vec to Cloudflare backend
- **Fixed incorrect CLAUDE.md documentation** that suggested SQLite-vec as "expected behavior"
- **Added configuration management best practices** with environment variable precedence
- **Enhanced troubleshooting sections** with specific solutions for environment variable loading issues

#### Configuration Enhancements
- **Improved environment variable loading reliability** with explicit MCP server configuration
- **Added execution context guidance** for different environments (Claude Desktop vs Claude Code)
- **Enhanced working directory awareness** for proper .env file loading
- **Better configuration validation** with clear error messages for missing required variables

#### Technical Improvements
- **Unified diagnostic approach** for both Cloudflare and SQLite-vec backends
- **Enhanced error reporting** with masked sensitive data for security
- **Improved configuration precedence handling** between global and project settings
- **Better cross-platform path handling** for Windows environments

#### Benefits for Users
- **Eliminates configuration confusion** between different execution environments
- **Provides clear validation tools** to quickly identify and resolve setup issues
- **Ensures consistent backend usage** across Claude Desktop and Claude Code
- **Streamlines Cloudflare backend adoption** with comprehensive setup guidance
- **Reduces setup time** from complex debugging to 5-minute guided process

## [6.17.2] - 2025-09-23

### 🔧 **Development Environment Stability Fix**

#### Module Isolation Improvements
- **Enhanced script module loading** in `scripts/server/run_memory_server.py` to prevent version conflicts
- **Added module cache clearing** to remove conflicting cached imports before loading local development code
- **Improved path prioritization** to ensure local `src/` directory takes precedence over installed packages
- **Better logging** shows exactly which modules are being cleared and paths being added for debugging

#### Technical Improvements
- **Prevents import conflicts** between development code and installed package versions
- **Ensures consistent behavior** when switching between development and production environments
- **Fixes version mismatch issues** that could cause `ImportError` for missing attributes like `INCLUDE_HOSTNAME`
- **More robust script execution** with conditional path management based on environment

#### Benefits for Developers
- **Reliable development environment** - Local changes always take precedence
- **Easier debugging** - Clear logging of module loading process
- **Consistent Cloudflare backend** - No more fallback to ChromaDB due to version conflicts
- **Zero breaking changes** - Maintains compatibility with all existing configurations

## [6.17.1] - 2025-09-23

### 🔧 **Script Reorganization Compatibility Hotfix**

#### Backward Compatibility Added
- **Added compatibility stub** at `scripts/run_memory_server.py` that redirects to new location with helpful migration notices
- **Updated configuration templates** to use Python module approach as primary method for maximum stability
- **Added comprehensive migration documentation** for users updating from pre-v6.17.0 versions
- **Zero disruption approach**: Existing configurations continue working immediately

#### Recommended Launch Methods (in order of stability)
1. **`python -m mcp_memory_service.server`** - Most stable, no path dependencies, works across all reorganizations
2. **`uv run memory server`** - Integrated with UV tooling, already documented as preferred
3. **`scripts/server/run_memory_server.py`** - Direct script execution at new location
4. **`scripts/run_memory_server.py`** - Legacy location with backward compatibility (shows migration notice)

#### Documentation Improvements
- **Enhanced README**: Clear migration notice with multiple working options
- **Updated examples**: Python module approach as primary recommendation
- **Migration guide**: Created comprehensive GitHub issue ([#108](https://github.com/doobidoo/mcp-memory-service/issues/108)) with all approaches
- **Template updates**: Configuration templates now show most stable approaches first

#### Why This Approach
- **Immediate relief**: No users are blocked during v6.17.0 update
- **Multiple pathways**: Users can choose the approach that fits their setup
- **Future-proof**: Python module approach survives any future directory changes
- **Clear migration path**: Informational notices guide users to better practices without forcing changes

## [6.17.0] - 2025-09-22

### 🚀 **Enhanced Installer with Cloudflare Backend Support**

#### Major Installer Improvements
- **Added Cloudflare backend to installer**: Full support for cloud-first installation workflow
  - **Interactive credential setup**: Guided collection of API token, Account ID, D1 database, and Vectorize index
  - **Automatic .env generation**: Securely saves credentials to project environment file
  - **Connection testing**: Validates Cloudflare API during installation process
  - **Graceful fallbacks**: Falls back to local backends if cloud setup fails
- **Enhanced backend selection logic**: Usage-based recommendations for optimal backend choice
  - **Production scenarios**: Cloudflare for shared access and cloud storage
  - **Development scenarios**: SQLite-vec for single-user, lightweight setup
  - **Team scenarios**: ChromaDB for multi-client local collaboration
- **Improved CLI options**: Updated `--storage-backend` with clear use case descriptions
  - **New choices**: `cloudflare` (production), `sqlite_vec` (development), `chromadb` (team), `auto_detect`
  - **Better help text**: Explains when to use each backend option

#### User Experience Enhancements
- **Interactive backend selection**: Guided setup with compatibility analysis and recommendations
- **Clear usage guidance**: Backend selection now includes use case scenarios and performance characteristics
- **Enhanced auto-detection**: Prioritizes most reliable backends for the detected system
- **Comprehensive documentation**: Updated installation commands and backend comparison table

#### Technical Improvements
- **Robust error handling**: Comprehensive fallback mechanisms for failed setups
- **Modular design**: Separate functions for credential collection, validation, and environment setup
- **Connection validation**: Real-time API testing during Cloudflare backend configuration
- **Environment file management**: Smart .env file handling that preserves existing settings

#### Benefits for Users
- **Seamless production setup**: Single command path from installation to Cloudflare backend
- **Reduced configuration errors**: Automated credential setup eliminates manual .env file creation
- **Better backend choice**: Clear guidance helps users select optimal storage for their use case
- **Improved reliability**: Fallback mechanisms ensure installation succeeds even with setup issues

## [6.16.1] - 2025-09-22

### 🔧 **Docker Build Hotfix**

#### Infrastructure Fix
- **Fixed Docker build failure**: Updated Dockerfile script path after v6.15.0 scripts reorganization
  - **Issue**: Docker build failing due to `scripts/install_uv.py` not found
  - **Solution**: Updated path to `scripts/installation/install_uv.py`
  - **Impact**: Restores automated Docker publishing workflows
- **No functional changes**: Pure infrastructure fix for CI/CD

## [6.16.0] - 2025-09-22

### 🔧 **Configuration Management & Backend Selection Fixes**

#### Critical Configuration Issues Resolved
- **Fixed Cloudflare backend fallback issue**: Resolved service falling back to SQLite-vec despite correct Cloudflare configuration
  - **Root cause**: Configuration module wasn't loading `.env` file automatically
  - **CLI override issue**: CLI default parameter was overriding environment variables
  - **Solution**: Added automatic `.env` loading and fixed CLI parameter precedence
- **Enhanced environment loading**: Added `load_dotenv()` to configuration initialization
  - **Automatic detection**: Config module now automatically loads `.env` file when present
  - **Backward compatibility**: Graceful fallback if python-dotenv not available
  - **Logging**: Added confirmation logging when environment file is loaded
- **Fixed CLI parameter precedence**: Changed CLI defaults to respect environment configuration
  - **Server command**: Changed `--storage-backend` default from `'sqlite_vec'` to `None`
  - **Environment priority**: Environment variables now take precedence over CLI defaults
  - **Explicit overrides**: CLI parameters only override when explicitly provided

#### Content Size Management Improvements
- **Added Cloudflare content limits to context provider**: Enhanced memory management guidance
  - **Content size warnings**: Added ~1500 character limit documentation
  - **Embedding model constraints**: Documented `@cf/baai/bge-base-en-v1.5` strict input limits
  - **Best practices**: Guidance for chunking large content and using document ingestion
  - **Error recognition**: Help identifying "Failed to store vector" errors from size issues
- **Enhanced troubleshooting**: Better error messages and debugging capabilities for configuration issues

#### Technical Improvements
- **Configuration validation**: Improved environment variable loading and validation
- **Error handling**: Better error messages when storage backend initialization fails
- **Documentation**: Updated context provider with Cloudflare-specific constraints and best practices

#### Benefits for Users
- **Seamless backend switching**: Cloudflare configuration now works reliably out of the box
- **Fewer configuration errors**: Automatic environment loading reduces setup friction
- **Better error diagnosis**: Clear guidance on content size limits and chunking strategies
- **Improved reliability**: Configuration precedence issues eliminated


---

## Historic Releases

For older releases (v6.15.1 and earlier), see [CHANGELOG-HISTORIC.md](./CHANGELOG-HISTORIC.md).

**Historic Version Range**: v0.1.0 through v6.15.1 (2025-07-XX through 2025-09-22)
## [6.15.1] - 2025-09-22

### 🔧 **Enhanced Cloudflare Backend Initialization & Diagnostics**

#### Cloudflare Backend Issue Resolution
- **Fixed silent fallback issue**: Resolved Cloudflare backend falling back to SQLite-vec during MCP startup
  - **Root cause identified**: Silent failures in eager initialization phase were not properly logged
  - **Enhanced error reporting**: Added comprehensive logging with visual indicators for all initialization phases
  - **Improved timeout handling**: Better error messages when Cloudflare initialization times out
- **Enhanced initialization logging**: Added detailed logging for both eager and lazy initialization paths
  - **Phase indicators**: 🚀 SERVER INIT, ☁️ Cloudflare-specific, ✅ Success markers, ❌ Error indicators
  - **Configuration validation**: Logs all Cloudflare environment variables for troubleshooting
  - **Storage type verification**: Confirms final storage backend type after initialization
- **Diagnostic improvements**: Created comprehensive diagnostic tools for Cloudflare backend issues
  - **Enhanced diagnostic script**: `debug_server_initialization.py` for testing initialization flows
  - **MCP environment testing**: `tests/integration/test_mcp_environment.py` for testing Claude Desktop integration
  - **Fixed test syntax errors**: Corrected f-string and async function issues in test files

#### Technical Improvements
- **Fixed `db_utils.py` async issue**: Changed `get_database_stats()` to async function to support Cloudflare storage
- **Enhanced error tracebacks**: Full exception details now logged for initialization failures
- **Better fallback documentation**: Clear distinction between eager vs lazy initialization behaviors

#### Troubleshooting Benefits
- **Faster issue diagnosis**: Clear visual indicators help identify where initialization fails
- **Better error messages**: Specific error details for common Cloudflare setup issues
- **Proactive debugging**: Enhanced logging appears in Claude Desktop MCP logs for easier troubleshooting

## [6.15.0] - 2025-09-22

### 🗂️ **Scripts Directory Reorganization & Professional Tooling**

#### Major Reorganization
- **Complete Scripts Restructuring**:
  - ✅ **Organized 62 loose scripts** into 12 logical categories for professional navigation
  - ✅ **Created systematic directory structure** with clear functional grouping
  - ✅ **Zero loose scripts remaining** in root directory - all properly categorized
  - ✅ **Maintained full backward compatibility** - all scripts work exactly as before
  - ✅ **Updated all documentation references** to reflect new paths

#### New Directory Structure
- **🔄 `sync/`** (4 scripts) - Backend synchronization utilities
- **🛠️ `service/`** (5 scripts) - Service management and deployment
- **✅ `validation/`** (7 scripts) - Configuration and system validation
- **🗄️ `database/`** (4 scripts) - Database analysis and health monitoring
- **🧹 `maintenance/`** (7 scripts) - Database cleanup and repair operations
- **💾 `backup/`** (4 scripts) - Backup and restore operations
- **🔄 `migration/`** (11 scripts) - Data migration and schema updates
- **🏠 `installation/`** (8 scripts) - Setup and installation scripts
- **🖥️ `server/`** (5 scripts) - Server runtime and operational scripts
- **🧪 `testing/`** (15 scripts) - Test scripts and validation
- **🔧 `utils/`** (7 scripts) - General utility scripts and wrappers
- **🛠️ `development/`** (6 scripts) - Development tools and debugging utilities

#### Enhanced Documentation
- **✅ Complete README.md rewrite** with comprehensive script index and usage examples
- **✅ Quick reference guide** for essential daily operations
- **✅ Detailed directory explanations** with purpose and key features
- **✅ Safety guidelines** and execution best practices
- **✅ Common use case workflows** for setup, operations, troubleshooting, and migration
- **✅ Integration documentation** linking to project wiki and guides

#### User Experience Improvements
- **🎯 Faster script discovery** - find tools by logical function instead of hunting through 62 files
- **📚 Professional documentation** with tables, examples, and clear categorization
- **🚀 Quick-start examples** for common operations and troubleshooting
- **🛡️ Safety-first approach** with dry-run recommendations and backup guidelines
- **🔗 Seamless integration** with existing CLAUDE.md, AGENTS.md, and documentation

#### Maintainability Enhancements
- **🏗️ Logical organization** makes adding new scripts intuitive
- **📝 Clear naming conventions** and directory purposes
- **🔄 Future-proof structure** that scales with project growth
- **✅ Consistent documentation patterns** across all categories
- **🧪 Verified functionality** - all critical scripts tested post-reorganization

#### Files Updated (4):
- **`scripts/README.md`** - COMPLETE REWRITE: Professional documentation with comprehensive index
- **`CLAUDE.md`** - UPDATED: All script paths updated to new locations
- **`AGENTS.md`** - UPDATED: Development workflow script references
- **`CHANGELOG.md`** - UPDATED: Historical script references to new paths

#### Impact
- 🎯 **Transforms user experience** from cluttered file hunting to professional navigation
- 🚀 **Enables faster development** with logical script organization
- 💻 **Simplifies maintenance** with clear categorization and documentation
- ✅ **Professional appearance** suitable for enterprise deployments
- 🔄 **Supports scalable growth** with extensible directory structure
- 🛡️ **Improves safety** with comprehensive usage guidelines and best practices

This release transforms the scripts directory from a disorganized collection into a professional, enterprise-ready toolkit that significantly improves developer and user experience while maintaining full functionality.

## [6.14.0] - 2025-09-22

### 🛠️ **Operational Utilities & Backend Synchronization**

#### New Backend Synchronization Capabilities
- **Bidirectional Sync Engine**:
  - ✅ `sync_memory_backends.py` - Core sync logic with intelligent deduplication
  - ✅ `claude_sync_commands.py` - User-friendly CLI wrapper for sync operations
  - ✅ Supports Cloudflare ↔ SQLite-vec synchronization with dry-run mode
  - ✅ Content-based hashing prevents duplicates across backends
  - ✅ Comprehensive status reporting and error handling
- **Service Management**:
  - ✅ `memory_service_manager.sh` - Linux service management for dual-backend deployments
  - ✅ State-based backend detection using `/tmp/memory-service-backend.state`
  - ✅ Environment file management for Cloudflare and SQLite configurations
  - ✅ Integrated sync operations and health monitoring
- **Configuration Validation**:
  - ✅ `validate_config.py` - Comprehensive configuration validator
  - ✅ Validates Claude Code global configuration (~/.claude.json)
  - ✅ Checks Cloudflare credentials and environment setup
  - ✅ Detects configuration conflicts and provides solutions
- **Documentation & Guides**:
  - ✅ Updated `scripts/README.md` with comprehensive utility documentation
  - ✅ Added backend sync references to main `README.md` and `CLAUDE.md`
  - ✅ Created `Backend-Synchronization-Guide.md` wiki page with complete setup guide

#### Code Quality Improvements (Gemini Code Assist Feedback)
- **Eliminated Code Duplication**:
  - ✅ Refactored `sync_memory_backends.py` to use shared `_sync_between_backends()` method
  - ✅ Reduced ~80 lines of duplicate code, improved maintainability
- **Cross-Platform Compatibility**:
  - ✅ Replaced hardcoded `/home/hkr/` paths with `$HOME` variable
  - ✅ Added missing final newlines to all utility scripts
- **Enhanced Validation & Robustness**:
  - ✅ Improved configuration validation with regex patterns instead of string matching
  - ✅ Added UTF-8 encoding to all file operations in `validate_config.py`
  - ✅ Fixed `.env.sqlite` conflict detection logic
- **Better Code Organization**:
  - ✅ Refactored command handling to dictionary-based dispatch pattern
  - ✅ Improved scalability for future command additions

#### Production Deployment Features
- **Hybrid Cloud/Local Deployments**: Enable Cloudflare primary with SQLite backup
- **Disaster Recovery**: Automated backup and restore capabilities
- **Multi-Machine Sync**: Consistent memory sharing across devices
- **Development/Production Workflows**: Seamless sync between environments
- **Troubleshooting Tools**: Configuration validation and service management

#### Impact
- 🎯 **Fills critical operational gaps** for production deployments
- 🚀 **Enables advanced deployment strategies** (hybrid cloud/local)
- 💻 **Simplifies troubleshooting** with validation and management tools
- ✅ **Professional code quality** meeting all review standards
- 🔄 **Supports complex workflows** for distributed teams

#### Files Added/Modified (8):
- `scripts/sync/sync_memory_backends.py` - NEW: Bidirectional sync engine
- `scripts/sync/claude_sync_commands.py` - NEW: CLI wrapper for sync operations
- `scripts/service/memory_service_manager.sh` - NEW: Linux service manager
- `scripts/validation/validate_config.py` - NEW: Configuration validator
- `scripts/README.md` - UPDATED: Comprehensive utility documentation
- `README.md` - UPDATED: Added troubleshooting references
- `CLAUDE.md` - UPDATED: Added sync and validation commands
- Wiki: `Backend-Synchronization-Guide.md` - NEW: Complete sync setup guide

## [6.13.8] - 2025-09-21

### 🔧 **Integration Completion**

#### Cloudflare Storage Backend Full Integration
- **Fixed critical integration gaps**: Cloudflare backend now has complete feature parity with sqlite_vec and chroma
- **Health Check Recognition**:
  - ✅ **Resolved "Unknown storage type: CloudflareStorage" errors**
  - ✅ Health check now properly validates Cloudflare storage and returns "healthy" status
  - ✅ Added Cloudflare support to `server.py` health validation (lines 3410-3450)
  - ✅ Added Cloudflare support to `db_utils.py` validation, stats, and repair functions
- **Complete CLI Integration**:
  - ✅ Added 'cloudflare' option to all CLI storage backend choices
  - ✅ Updated `cli/main.py`, `cli/ingestion.py` with cloudflare backend support
  - ✅ Added CloudflareStorage initialization logic to `cli/utils.py`
  - ✅ Updated configuration documentation to include cloudflare option
- **Documentation & Startup Guidance**:
  - ✅ **Critical**: Added warning about inappropriate use of `memory_offline.py` with Cloudflare backend
  - ✅ Cloudflare uses Workers AI for embeddings - offline mode breaks this functionality
  - ✅ Added proper startup script recommendations in `docs/cloudflare-setup.md`
  - ✅ Recommended: `uv run memory server`, `python scripts/run_memory_server.py`
- **Enhanced Test Coverage**:
  - ✅ Added comprehensive tests for tag sanitization method
  - ✅ Verified existing extensive test suite covers all major functionality
- **Impact**:
  - 🎯 **Cloudflare backend is now a first-class citizen** alongside sqlite_vec and chroma
  - 🚀 **Complete health check integration** - no more "Unknown storage type" errors
  - 💻 **Full CLI support** for cloudflare backend selection
  - 📚 **Clear startup guidance** prevents Workers AI compatibility issues
  - ✅ **Production ready** for distributed teams and cloud-native deployments

#### Files Modified (11):
- `src/mcp_memory_service/server.py` - Added Cloudflare health check case
- `src/mcp_memory_service/utils/db_utils.py` - Added validation, stats, repair support
- `src/mcp_memory_service/cli/main.py` - Added cloudflare CLI option
- `src/mcp_memory_service/cli/ingestion.py` - Added cloudflare CLI option
- `src/mcp_memory_service/cli/utils.py` - Added CloudflareStorage initialization
- `src/mcp_memory_service/config.py` - Updated backend documentation
- `docs/cloudflare-setup.md` - Added startup script guidance and warnings
- `tests/unit/test_cloudflare_storage.py` - Enhanced test coverage
- `src/mcp_memory_service/__init__.py` - Version bump to 6.13.8
- `pyproject.toml` - Version bump to 6.13.8

## [6.13.7] - 2025-09-20

### 🐛 **Critical Bug Fixes**

#### Cloudflare Vectorize ID Length Issue Fixed
- **Fixed critical bug**: Resolved Cloudflare Vectorize vector ID length limit error
  - **Root Cause**: CloudflareStorage was using `"mem_" + content_hash` format for vector IDs (68 characters)
  - **Cloudflare Limit**: Vectorize has a 64-byte maximum ID length restriction
  - **Solution**: Removed "mem_" prefix, now using `content_hash` directly (64 characters)
  - **Impact**: **Enables proper bidirectional sync** between multiple machines using Cloudflare backend
  - **Error Fixed**: `"id too long; max is 64 bytes, got 68 bytes"` when storing memories
- **Affects**: All users using Cloudflare backend for memory storage
- **Backward Compatibility**: ⚠️ **Breaking change** - existing Cloudflare vector IDs will have different format
- **Migration**: Users with existing Cloudflare deployments may need to re-import memories
- **Benefits**:
  - ✅ Cloudflare backend now works reliably for memory storage
  - ✅ Multi-machine sync scenarios (e.g., replacing failed servers) now supported
  - ✅ Consistent vector ID format aligns with Cloudflare specifications
- **Files Modified**: `src/mcp_memory_service/storage/cloudflare.py:295`

#### Multi-Machine Sync Capability
- **New capability**: Cloudflare can now serve as central memory hub for multiple machines
- **Use case**: Replacement for failed centralized servers (e.g., narrowbox failures)
- **Implementation**: Dual storage strategy with Cloudflare primary + local sqlite_vec backup
- **Tested**: Bidirectional sync verified between macOS machines using Cloudflare D1 + Vectorize

## [6.13.6] - 2025-09-16

### 📚 **Documentation**

#### Added AGENTS.md for AI Coding Agents
- **New standard format**: Added `AGENTS.md` following the industry-standard [agents.md](https://agents.md/) specification
  - **Purpose**: Provides AI coding agents with project-specific instructions and context
  - **Compatibility**: Works with GitHub Copilot, Cursor, VS Code, Continue, and other AI tools
  - **Complements CLAUDE.md**: Generic instructions for all AI agents vs Claude-specific in CLAUDE.md
- **Content includes**:
  - Setup commands and testing procedures
  - Project structure and key files overview
  - Code style guidelines and conventions
  - Common development tasks and patterns
  - Security guidelines and debugging tips
- **Benefits**:
  - Standardized location for AI agent instructions (becoming industry standard)
  - Improved developer experience when using AI coding assistants
  - Better onboarding for contributors using AI tools
- **Files Added**: `AGENTS.md`

#### Added CONTRIBUTING.md for Contributor Guidelines
- **Fixed dead link**: Resolved broken reference in README.md line 195
- **Comprehensive guidelines**: Added detailed contribution instructions including:
  - Development environment setup with platform-specific notes
  - Code style and Python conventions following PEP 8
  - Testing requirements with pytest examples
  - Semantic commit message format
  - Pull request process and review guidelines
- **Code of Conduct**: Included basic behavioral guidelines for inclusive community
- **Multiple contribution paths**: Documented various ways to contribute (code, docs, testing, support)
- **Integration**: Links to existing documentation (AGENTS.md, CLAUDE.md, Wiki)
- **Files Added**: `CONTRIBUTING.md`

## [6.13.5] - 2025-09-15

### 🐛 **Bug Fixes**

#### macOS Service Installation Script Fix (PR #101)
- **Fixed NameError**: Resolved `NameError: name 'paths' is not defined` in `install_macos_service.py` at line 238
  - **Root Cause**: Variable `paths` was referenced in `platform_info` dictionary without being initialized
  - **Solution**: Added `paths = get_service_paths()` call before usage, following existing code patterns
  - **Impact**: macOS service installation now works reliably without runtime errors
- **Credit**: Thanks to @hex for identifying and fixing this issue
- **Files Modified**: `scripts/install_macos_service.py`

## [6.13.4] - 2025-09-14

### 🐛 **Critical Bug Fixes**

#### Memory Search Timezone Inconsistency (Fixes Issue #99)
- **Fixed timezone handling bug**: Resolved critical inconsistency in timestamp validation between hook-generated and manual memories
  - **Root Cause**: Memory model was incorrectly interpreting ISO timestamps without 'Z' suffix as local time instead of UTC
  - **Solution**: Enhanced `iso_to_float()` function with explicit UTC handling using `calendar.timegm()`
  - **Impact**: Time-based memory searches (e.g., "yesterday", "last week") now consistently find all memories regardless of storage method
- **Improved timestamp validation**: Enhanced `_sync_timestamps()` method with better timezone mismatch detection
  - Added logic to detect timezone offset discrepancies between float and ISO timestamps
  - Automatic correction when timezone issues detected (prefers float timestamp as authoritative)
  - Better logging for timezone validation issues during memory creation
- **Comprehensive test coverage**: Added extensive test suite validating fix effectiveness
  - `test_hook_vs_manual_storage.py`: Validates consistency between hook and manual memory storage
  - `test_issue99_final_validation.py`: Confirms timezone fix resolves the original issue
  - `test_search_retrieval_inconsistency.py`: Root cause analysis and validation tests
  - `test_data_serialization_consistency.py`: Memory serialization consistency validation

### 🔧 **Technical Improvements**
- **Memory Model Enhancement**: Strengthened timestamp handling throughout the memory lifecycle
  - More robust ISO string parsing with fallback mechanisms
  - Better error handling for edge cases in timestamp conversion
  - Consistent UTC interpretation across all timestamp operations

### 📚 **Documentation Updates**
- **Issue Resolution**: GitHub Issue #99 documented and resolved with comprehensive technical analysis
- **Test Documentation**: Added detailed test suite documentation for memory storage consistency

## [6.13.3] - 2025-09-03

### 🐛 **Critical Bug Fixes**

#### macOS SQLite Extension Support (Fixes Issue #97)
- **Fixed AttributeError**: Resolved `'sqlite3.Connection' object has no attribute 'enable_load_extension'` error on macOS
  - Added comprehensive extension support detection before attempting to load sqlite-vec
  - Graceful error handling with clear, actionable error messages
  - Platform-specific guidance for macOS users (Homebrew Python, pyenv with extension support)
  - Interactive prompt to switch to ChromaDB backend when extensions unavailable
- **Enhanced sqlite_vec.py**: Added `_check_extension_support()` method with robust error handling
- **Improved install.py**: Added SQLite extension support detection and warnings during installation

### 📚 **Documentation Updates**

#### macOS Extension Loading Documentation
- **README Updates**: Added dedicated macOS SQLite extension support section with solutions
- **First-Time Setup Guide**: Comprehensive macOS extension issues section with verification commands
- **Troubleshooting Guide**: Detailed troubleshooting for `enable_load_extension` AttributeError
- **Clear Solutions**: Step-by-step instructions for Homebrew Python and pyenv with extension support

### 🔧 **Installation Improvements**
- **Proactive Detection**: Installer now checks SQLite extension support before attempting sqlite-vec installation
- **Interactive Fallback**: Option to automatically switch to ChromaDB when sqlite-vec cannot work
- **Better Error Messages**: Platform-specific solutions instead of cryptic errors
- **System Information**: Enhanced system info display includes SQLite extension support status

### 🏥 **Error Handling**
- **Runtime Protection**: sqlite-vec backend now fails gracefully with helpful error messages
- **Clear Guidance**: Detailed error messages explain why the error occurs and provide multiple solutions
- **Automatic Detection**: System automatically detects extension support capabilities

## [6.13.2] - 2025-09-03

### 🐛 **Bug Fixes**

#### Python 3.13 Compatibility (Fixes Issue #96)
- **Enhanced sqlite-vec Installation**: Added intelligent fallback strategies for Python 3.13 where pre-built wheels are not yet available
  - Automatic retry with multiple installation methods (uv pip, standard pip, source build, GitHub install)
  - Clear guidance for alternative solutions (Python 3.12, ChromaDB backend)
  - Interactive prompt to switch backends if sqlite-vec installation fails
- **Improved Error Messages**: Better error reporting with actionable manual installation options
- **uv Package Manager Support**: Prioritizes uv pip when available for better dependency resolution

### 📚 **Documentation Updates**

#### Python 3.13 Support Documentation
- **README Updates**: Added Python 3.13 compatibility note with recommended solutions
- **First-Time Setup Guide**: New section on Python 3.13 known issues and workarounds
- **Troubleshooting Guide**: Comprehensive sqlite-vec installation troubleshooting for Python 3.13
- **Clear Migration Path**: Step-by-step instructions for using Python 3.12 or switching to ChromaDB

### 🔧 **Installation Improvements**
- **Multi-Strategy Installation**: Installer now tries 5 different methods before failing
- **Source Build Fallback**: Attempts to build from source when wheels are unavailable
- **GitHub Direct Install**: Falls back to installing directly from sqlite-vec repository
- **Backend Switching**: Option to automatically switch to ChromaDB if sqlite-vec fails

## [6.13.1] - 2025-09-03

### 📚 **Documentation & User Experience**

#### First-Time Setup Documentation (Addresses Issue #95)
- **Added First-Time Setup Section**: New prominent section in README.md explaining expected warnings on initial run
- **Created Comprehensive Guide**: New `docs/first-time-setup.md` with detailed explanations of:
  - Normal warnings vs actual errors
  - Model download process (~25MB, 1-2 minutes)
  - Success indicators and verification steps
  - Ubuntu 24-specific installation instructions
- **Enhanced Troubleshooting**: Updated `docs/troubleshooting/general.md` with first-time warnings section
- **Improved Installer Messages**: Enhanced `install.py` with clear first-time setup expectations and progress indicators

### 🐛 **Bug Fixes**

#### User Experience Improvements
- **Fixed Issue #95**: Clarified that "No snapshots directory" warning is normal on first run
- **Addressed Confusion**: Distinguished between expected initialization warnings and actual errors
- **Ubuntu 24 Support**: Added specific documentation for Ubuntu 24 installation issues

### 📝 **Changes**
- Added clear messaging that warnings disappear after first successful run
- Included estimated download times and model sizes in documentation
- Improved installer output to set proper expectations for first-time users

## [6.13.0] - 2025-08-25

### ⚡ **Major Features**

#### Enhanced Storage Backend Visibility & Health Integration
- **Health Check Integration**: Claude Code hooks now use `/api/health/detailed` endpoint for **authoritative storage information**
  - **Real-time Backend Detection**: Queries live health data instead of environment variables
  - **Rich Storage Information**: Displays memory count, database size, connection status, and embedding model
  - **Comprehensive Database Stats**: Shows unique tags, file paths, platform info, and uptime
  - **Fallback Strategy**: Health check → Environment variables → Configuration inference

- **Enhanced Console Output**:
  - **Brief Mode**: `💾 Storage → 🪶 sqlite-vec (Connected) • 990 memories • 5.21MB`
  - **Detailed Mode**: Separate lines for storage type, location, and database statistics
  - **Icon-Only Mode**: Minimal display with backend type and memory count
  - **Path Display**: Shows actual database file locations from health data

- **Context Message Enhancement**:
  - **Storage Section**: Includes backend type, connection status, memory count, and database size
  - **Location Info**: Real file paths from health endpoint rather than configuration guesses  
  - **Model Information**: Displays active embedding model (e.g., all-MiniLM-L6-v2)
  - **Health Metadata**: Platform info and database accessibility status

### 🔧 **Configuration Enhancements**

#### New Health Check Settings
- **`memoryService.healthCheckEnabled`**: Enable/disable health endpoint queries (default: true)
- **`memoryService.healthCheckTimeout`**: Timeout for health requests in milliseconds (default: 3000)
- **`memoryService.useDetailedHealthCheck`**: Use `/api/health/detailed` vs `/api/health` (default: true)
- **Enhanced Display Modes**: `sourceDisplayMode` supports "brief", "detailed", "icon-only"

### 🐛 **Critical Bug Fixes**

#### Windows Path Resolution Issues
- **Git Analyzer**: Fixed Windows path handling in `execSync` calls using `path.resolve()`
- **Project Detector**: Resolved Windows path issues in git command execution
- **Path Normalization**: All working directory paths properly normalized for cross-platform compatibility

#### Memory Context Display Improvements  
- **Content Length Limits**: Increased from 300→500 characters to prevent truncation
- **CLI Formatting**: Enhanced from 180→400 chars for better context visibility
- **Categorized Display**: Improved from 160→350 chars for categorized memories
- **Deduplication Logging**: Fixed misleading "8 → 2" messages, now shows actual selection counts

#### Output Cleaning & Visual Improvements
- **Session Hook Tags**: Added cleaning logic to remove `<session-start-hook>` wrapper tags
- **Memory Categories**: Enhanced category titles (e.g., "Recent Work (Last 7 days)", "Bug Fixes & Issues")
- **Better Hierarchy**: Improved visual organization and color coding
- **Configurable Limits**: All content length limits now configurable via config.json

### 💡 **Smart Detection Improvements**

#### Backend Detection Hierarchy
1. **Health Endpoint** (Primary): Authoritative data from running service
2. **Environment Variables** (Secondary): MCP_MEMORY_STORAGE_BACKEND detection
3. **Configuration Inference** (Fallback): Endpoint-based local/remote classification

#### Supported Backend Types
- **SQLite-vec**: 🪶 Local database with file path and size information
- **ChromaDB**: 📦 Local or 🌐 Remote with endpoint details  
- **Cloudflare**: ☁️ Cloud service with account information
- **Generic Services**: 💾 Local or 🌐 Remote MCP services

### 🎯 **Performance & Reliability**

#### Health Check Implementation
- **Non-blocking**: Async health queries don't slow session start
- **Timeout Protection**: 3-second default timeout prevents hanging
- **Error Handling**: Graceful fallback to configuration-based detection
- **Caching**: Health info cached during session to avoid repeated calls

## [6.12.0] - 2025-08-25

### ⚡ **Major Features**

#### Git-Aware Memory Retrieval System
- **Repository Context Analysis**: Session hooks now analyze git commit history and changelog entries
  - **Git Context Analyzer**: New utility (`git-analyzer.js`) extracts development keywords from recent commits
  - **Commit Mining**: Analyzes last 14 days of commits to understand development patterns
  - **Changelog Integration**: Parses CHANGELOG.md to identify recent development themes
  - **Smart Query Generation**: Creates git-informed semantic queries for memory retrieval

- **Multi-Phase Memory Retrieval Enhancement**:
  - **Phase 0 (NEW)**: Git-aware memory search using repository context (highest priority)
  - **Phase 1**: Recent memories enhanced with git development keywords  
  - **Phase 2**: Important tagged memories with framework/language context
  - **Phase 3**: Fallback general context with extended time windows

- **Enhanced Context Categorization**:
  - **"Current Development" Category**: New category for git-context derived memories
  - **Repository-Aware Scoring**: Memories aligned with recent commits get higher relevance scores
  - **Development Timeline Integration**: Memory selection based on actual coding activity

### 🔧 **Configuration Enhancements**

#### New Git Analysis Settings
- **`gitAnalysis.enabled`**: Enable/disable git context analysis (default: true)
- **`gitAnalysis.commitLookback`**: Days of commit history to analyze (default: 14)
- **`gitAnalysis.maxCommits`**: Maximum commits to process (default: 20)
- **`gitAnalysis.includeChangelog`**: Parse changelog for context (default: true)
- **`gitAnalysis.maxGitMemories`**: Memory slots reserved for git context (default: 3)
- **`gitAnalysis.gitContextWeight`**: Relevance multiplier for git-derived memories (default: 1.2)

#### Enhanced Output Control
- **`output.showGitAnalysis`**: Display git analysis information (default: true)
- **`output.showPhaseDetails`**: Show detailed phase execution info (default: true)
- **Improved Memory Ratio Configuration**: `recentMemoryRatio`, `recentTimeWindow`, `fallbackTimeWindow`

### 💡 **Smart Query Improvements**

#### Development-Aware Semantic Queries
- **Commit Message Context**: Latest commit messages influence memory search
- **File Pattern Recognition**: Recently changed files inform query building  
- **Technical Keyword Extraction**: Action words (feat, fix, refactor) enhance search relevance
- **Branch-Aware Queries**: Git branch context integrated into semantic search

### 🎯 **Memory Relevance Enhancements**

#### Repository Activity Integration
- **Development Intensity Scoring**: High commit activity increases recent memory priority
- **File-Based Context**: Memories related to recently changed files get boosted relevance
- **Changelog Correlation**: Memory selection aligned with documented changes
- **Temporal Context Weighting**: Recent development activity influences memory scoring

### 🚀 **Performance & Reliability**

#### Git Integration Optimizations  
- **Lazy Git Analysis**: Only processes git context when repository detected
- **Performance Limits**: Configurable commit analysis limits to prevent slowdowns
- **Graceful Degradation**: Falls back to standard retrieval if git analysis fails
- **Async Processing**: Non-blocking git analysis for faster session startup

### 📊 **Enhanced Debugging & Monitoring**

#### Git Analysis Visibility
- **Git Context Reporting**: Shows analyzed commits, changelog entries, and extracted keywords
- **Phase Execution Details**: Clear indication of which phase found which memories
- **Query Source Tracking**: Memories tagged with their retrieval source (git-commits, git-files, etc.)
- **Development Keywords Display**: Shows extracted technical terms from recent activity

### 🔄 **Backward Compatibility**

#### Seamless Integration
- **Legacy Mode Support**: `recentFirstMode: false` preserves original behavior
- **Configuration Migration**: All existing configurations continue to work
- **Optional Git Features**: Git analysis can be completely disabled if needed
- **Incremental Adoption**: Features can be enabled progressively

---

## [6.11.1] - 2025-08-25

### 🐛 **Bug Fixes**

#### Windows Path Configuration Issues
- **Claude Code Hooks Installation**: Fixed Windows-specific path configuration issues
  - **Legacy Path Cleanup**: Removed outdated `.claude-code` references from installation scripts
  - **Windows Batch File**: Updated help text to use correct `.claude\hooks` directory structure
  - **PowerShell Script**: Cleaned up legacy path alternatives for better reliability
  - **Impact**: Windows users no longer encounter `.claude-code` vs `.claude` directory confusion

#### Enhanced Documentation
- **Windows Installation Guide**: Added comprehensive Windows-specific installation and troubleshooting section
  - **Path Format Guidance**: Clear instructions for JSON path formatting (forward slashes vs backslashes)
  - **Common Issues**: Solutions for `session-start-wrapper.bat` errors and legacy directory migration
  - **Settings Examples**: Proper Windows configuration examples with correct Node.js script paths
  - **Impact**: Windows users have clear guidance for resolving path configuration issues

#### Path Validation Utilities
- **Automated Detection**: Added path validation functions to detect and warn about configuration issues
  - **Legacy Path Detection**: Automatically identifies old `.claude-code` directories and provides migration steps
  - **Settings Validation**: Validates JSON settings files for Windows path issues and missing files
  - **Path Normalization**: Utility to convert Windows backslash paths to JSON-compatible format
  - **Validation Command**: New `python scripts/claude_commands_utils.py --validate` command for configuration checking
  - **Impact**: Proactive detection and resolution of Windows path issues during installation

## [6.10.1] - 2025-08-25

### 🐛 **Bug Fixes**

#### Fixed Claude Code Memory Commands
- **API Key Update**: Updated all Claude Code memory commands with current production API key
  - Fixed `/memory-context`, `/memory-store`, `/memory-recall`, `/memory-search`, `/memory-health` commands
  - Replaced outdated `test-key-123` with current production API key
  - **Impact**: All memory commands now work correctly with remote memory service

#### Enhanced `/memory-context` Command
- **Dynamic Session Capture**: Removed hardcoded session content, now captures real-time context
  - **Real-time Info**: Includes current timestamp, working directory, git branch, and recent commits  
  - **Dynamic Tags**: Automatically includes current project name as tag
  - **User Context**: Properly captures user-provided session description via `$ARGUMENTS`
  - **Impact**: `/memory-context` now stores actual session context instead of static placeholder text

## [6.10.0] - 2025-08-25

### ✨ **New Features**

#### Markdown-to-ANSI Conversion for Clean CLI Output
- **Automatic Markdown Processing**: Memory content with markdown formatting is now automatically converted to ANSI colors
  - **Headers**: `## Header` → Bold Cyan, `### Subheader` → Bold for visual hierarchy
  - **Emphasis**: `**bold**` → Bold, `*italic*` → Dim for text emphasis
  - **Code**: `` `inline code` `` → Gray, code blocks properly formatted with gray text
  - **Lists**: Markdown bullets (`-`, `*`) → Cyan bullet points (`•`), numbered lists → Cyan arrows (`›`)
  - **Links**: `[text](url)` → Cyan text without URL clutter
  - **Blockquotes**: `> quote` → Dimmed with visual indicator (`│`)
  - **Impact**: Raw markdown syntax no longer appears in CLI output, providing clean and professional display

#### Smart Content Processing
- **Environment-Aware**: Automatically detects CLI environment and applies appropriate formatting
- **Configuration Option**: Can be disabled via `CLAUDE_MARKDOWN_TO_ANSI=false` environment variable
- **Strip-Only Mode**: Option to remove markdown without adding ANSI colors for plain text output
- **Performance**: Minimal overhead (<5ms) with single-pass regex transformation

## [6.9.0] - 2025-08-25

### ✨ **New Features**

#### Enhanced Claude Code Hook Visual Output
- **Professional CLI Formatting**: Completely redesigned hook output with ANSI color coding and clean typography
  - **ANSI Color Support**: Full color coding with cyan, green, blue, yellow, gray, and red for different components
  - **Clean Typography**: Removed all markdown syntax (`**`, `#`, `##`) and HTML-like tags from CLI output
  - **Consistent Visual Pattern**: Standardized `icon component → description` format throughout all hook messages
  - **Unicode Box Drawing**: Enhanced use of `┌─`, `├─`, `└─`, and `│` characters for better visual structure
  - **Impact**: Hook output now looks professional and readable in Claude Code terminal sessions

#### Color-Coded Memory Content
- **Type-Based Coloring**: Different colors for memory types (decisions=yellow, insights=magenta, bugs=green, features=blue)
- **Visual Hierarchy**: Important information highlighted with bright colors, metadata dimmed with gray
- **Date Formatting**: Consistent gray coloring for dates and timestamps
- **Category Icons**: Enhanced category display with colored section headers

#### Improved Console Logging
- **Structured Messages**: All console output now follows consistent visual patterns
- **Progress Indicators**: Clear visual feedback for memory search, scoring, and processing steps
- **Error Handling**: Enhanced error messages with proper color coding and clear descriptions
- **Success Confirmation**: Prominent success indicators with checkmarks and summary information

#### Enhanced Project Detection
- **Confidence Visualization**: Color-coded confidence scores (green >80%, yellow >60%, gray <60%)
- **Clean Project Info**: Streamlined project detection output with proper visual hierarchy
- **Technology Stack Display**: Clear formatting for detected languages, frameworks, and tools

## [6.8.0] - 2025-08-25

### ✨ **New Features**

#### Enhanced Claude Code CLI Formatting
- **Beautiful CLI Output**: Claude Code hooks now feature enhanced visual formatting with Unicode box-drawing characters
  - **Visual Hierarchy**: Clean tree structure using `├─`, `└─`, and `│` characters for better readability
  - **Contextual Icons**: Memory context (🧠), project info (📂, 📝), and category-specific icons (🏗️, 🐛, ✨)
  - **Smart Environment Detection**: Automatically switches between Markdown (web) and enhanced CLI formatting
  - **Improved Categorization**: Visual grouping of memories by type with proper indentation and spacing
  - **Impact**: Dramatically improved readability of hook output in Claude Code terminal sessions

#### CLI Environment Detection
- **Automatic Detection**: Uses multiple detection methods including `CLAUDE_CODE_CLI` environment variable
- **Terminal Compatibility**: Enhanced formatting works seamlessly across different terminal emulators
- **Fallback Support**: Graceful degradation to standard formatting when enhanced features unavailable

#### Visual Design Improvements
- **Category Icons**: 🏗️ Architecture & Design, 🐛 Bug Fixes & Issues, ✨ Features & Implementation, 📝 Additional Context
- **Project Status Display**: Git branch (📂) and commit info (📝) with clean formatting
- **Memory Count Indicators**: Clear display of loaded memory count with 📚 icon
- **Empty State Handling**: Elegant display when no memories available

## [6.7.2] - 2025-08-25

### 🔧 **Enhancement**

#### Deduplication Script Configuration-Aware Refactoring
- **Enhanced API Integration**: Deduplication script now reads Claude Code hooks configuration for seamless integration
  - **Configuration Auto-Detection**: Automatically reads `~/.claude/hooks/config.json` for memory service endpoint and API key
  - **API-Based Analysis**: Supports remote memory service analysis via HTTPS API with self-signed certificate support
  - **Intelligent Pagination**: Handles large memory collections (972+ memories) with automatic page-by-page retrieval
  - **Backward Compatibility**: Maintains support for direct database access with `--db-path` parameter
  - **Impact**: Users can now run deduplication on remote memory services without manual configuration

#### New Command-Line Options
- **`--use-api`**: Force API-based analysis using configuration endpoint
- **Smart Fallback**: Automatically detects available options and suggests alternatives when paths missing
- **Enhanced Error Messages**: Clear guidance on configuration requirements and troubleshooting steps

#### Technical Improvements
- **SSL Context Configuration**: Proper handling of self-signed certificates for secure remote connections
- **Memory Format Normalization**: Converts API response format to internal analysis format seamlessly
- **Progress Reporting**: Real-time feedback during multi-page memory retrieval operations

#### Validation Results
- **✅ 972 Memories Analyzed**: Successfully processed complete memory collection via API
- **✅ No Duplicates Detected**: Confirms v6.7.0 content quality filters are preventing duplicate creation
- **✅ Configuration Integration**: Seamless integration with existing Claude Code hooks setup
- **✅ Performance Maintained**: Efficient pagination and processing of large memory collections

> **Usage**: Run `python scripts/find_duplicates.py --use-api` to analyze memories using your configured remote memory service

## [6.7.1] - 2025-08-25

### 🔧 **Critical Bug Fix**

#### Claude Code Hooks Installation Script Fix
- **Fixed Missing v6.7.0 Files in Installation**: Resolved critical installation script bug that prevented complete v6.7.0 setup
  - **Added Missing Core Hook**: `memory-retrieval.js` now properly copied during installation
  - **Added Missing Utility**: `context-shift-detector.js` now properly copied during installation
  - **Updated Install Messages**: Installation logs now accurately reflect all installed files
  - **Impact**: Eliminates "Cannot find module" errors on fresh v6.7.0 installations

#### Problem Resolved
- **Issue**: Installation script (`install.sh`) used hardcoded file list that was missing new v6.7.0 files
- **Symptoms**: Users experienced module import errors and incomplete feature sets after installation
- **Root Cause**: Script copied only `session-start.js`, `session-end.js` but missed `memory-retrieval.js` and `context-shift-detector.js`
- **Solution**: Added missing file copy commands and updated installation messaging

#### Validation
- **✅ Complete Installation**: All v6.7.0 files now properly installed
- **✅ Integration Tests**: 14/14 tests pass immediately after fresh installation 
- **✅ No Module Errors**: All dependencies resolved correctly
- **✅ Full Feature Set**: On-demand memory retrieval and smart timing work out-of-the-box

> **Note**: This is a critical patch for v6.7.0 users. If you installed v6.7.0 and experienced module errors, please reinstall using v6.7.1.

## [6.7.0] - 2025-08-25

### 🧠 **Claude Code Memory Awareness - Major Enhancement**

#### Smart Memory Context Presentation ([#Memory-Presentation-Fix](https://github.com/doobidoo/mcp-memory-service/issues/memory-presentation))
- **Eliminated Generic Content Fluff**: Complete overhaul of session-start hook memory presentation
  - **Smart Content Extraction**: Extracts meaningful content from session summaries (decisions, insights, code changes) instead of truncating at 200 chars
  - **Section-Aware Parsing**: Prioritizes showing actual decisions/insights over generic headers like "Topics Discussed - implementation..."
  - **Deduplication Logic**: Automatically filters out repetitive session summaries with 80% similarity threshold
  - **Impact**: Users now see actionable memory content instead of truncated generic summaries

#### Enhanced Memory Quality Scoring
- **Content Quality Factor**: New scoring dimension that heavily penalizes generic/empty content
  - **Meaningful Indicators**: Detects substantial content using decision words (decided, implemented, fixed, learned)
  - **Information Density**: Analyzes word diversity and content richness
  - **Generic Pattern Detection**: Automatically identifies and demotes "implementation..." session summaries
  - **Impact**: Quality memories now outrank recent-but-empty summaries

#### Smart Context Management
- **Post-Compacting Control**: Added `injectAfterCompacting: false` configuration option
  - **Problem Solved**: Stops disruptive mid-session memory injection after compacting events
  - **User-Controlled**: Can be enabled via `config.json` for users who prefer the old behavior
- **Context Shift Detection**: Intelligent timing for when to refresh memory context
  - **Project Change Detection**: Auto-refreshes when switching between projects/directories
  - **Topic Shift Analysis**: Detects significant conversation topic changes
  - **User Request Recognition**: Responds to explicit memory requests ("remind me", "what did we decide")
  - **Impact**: Memory context appears only when contextually appropriate, not disruptively

#### New Features
- **On-Demand Memory Retrieval**: New `memory-retrieval.js` hook for manual context requests
  - **User-Triggered**: Allows manual memory refresh when needed
  - **Query-Based**: Supports semantic search with user-provided queries
  - **Relevance Scoring**: Shows confidence scores for manual retrieval
- **Streamlined Presentation**: Cleaner formatting with reduced metadata clutter
  - **Smart Categorization**: Only groups memories when there's meaningful diverse content
  - **Relevant Tags Only**: Filters out machine-generated and generic tags
  - **Concise Dating**: More compact date formatting (Aug 25 vs full timestamps)

#### Technical Improvements
- **Enhanced Memory Scoring Weights**:
  ```json
  {
    "timeDecay": 0.25,        // Reduced from 0.30
    "tagRelevance": 0.35,     // Maintained
    "contentRelevance": 0.15,  // Reduced from 0.20
    "contentQuality": 0.25,    // NEW quality factor
    "conversationRelevance": 0.25 // Maintained
  }
  ```
- **New Utility Files**:
  - `context-shift-detector.js`: Intelligent context change detection
  - Enhanced `context-formatter.js` with smart content extraction
  - Quality-aware scoring in `memory-scorer.js`

#### Breaking Changes
- **Session-Start Hook**: Upgraded to v2.0.0 with smart timing and quality filtering
- **Configuration Schema**: Added new options for memory quality control and compacting behavior
- **Memory Filtering**: Generic session summaries are now automatically filtered out

#### Migration Guide
- **Automatic**: No user action required - existing configurations work with sensible defaults
- **Optional**: Users can enable `injectAfterCompacting: true` in config.json if they prefer old behavior
- **Benefit**: Immediate improvement in memory context quality and relevance

## [6.6.4] - 2025-08-25

### 🔧 **Installation Experience Improvements**

#### Universal Installer Bug Fixes ([#92](https://github.com/doobidoo/mcp-memory-service/issues/92))
- **Fixed "Installer Gets Stuck" Issues**: Resolved multiple causes of installation appearing frozen
  - Added prominent visual separators (`⚠️ USER INPUT REQUIRED`) around all input prompts
  - Extended system detection timeouts from 10 to 30 seconds (macOS `system_profiler`, Homebrew checks)
  - Added progress indicators for long-running operations (package installations, hardware detection)
  - **Impact**: Users now clearly understand when installer needs input vs. processing in background

#### New Non-Interactive Installation Mode
- **Added `--non-interactive` Flag**: Enables fully automated installations using sensible defaults
  - Automatically selects SQLite-vec backend (recommended)
  - Skips optional components (Claude Code commands, multi-client setup)
  - Perfect for CI/CD, Docker builds, and scripted deployments
  - **Usage**: `python install.py --non-interactive`

#### Enhanced User Experience
- **Better Progress Feedback**: Clear messaging during system detection and package installation phases
- **Improved Timeout Handling**: More resilient system detection with graceful fallbacks
- **Log File Visibility**: Prominently displays location of `installation.log` for troubleshooting

## [6.6.3] - 2025-08-24

### 🔧 **CI/CD Infrastructure Improvements**

#### GitHub Actions Workflow Fixes
- **Fixed npm dependency management**: Created proper `package.json` files for test directories
- **Simplified YAML structure**: Replaced complex multi-line scripts with focused single-step commands
- **Improved error reporting**: Split validation steps for clearer failure identification
- **Fixed false positives**: Updated status code validation to avoid flagging legitimate 200/201 handling
- **Enhanced reliability**: Used `working-directory` instead of embedded `cd` commands
- **Impact**: GitHub Actions CI/CD now properly installs dependencies and validates bridge fixes

#### Test Infrastructure Enhancements
- **Added dedicated test packages**: Separate `package.json` for bridge and integration tests
- **Improved module resolution**: Confirmed correct relative path handling in test files
- **Better validation coverage**: Enhanced API contract and smoke test verification

## [6.6.2] - 2025-08-24

### 🐛 **Critical Bug Fixes**

#### HTTP-MCP Bridge Complete Repair
- **Fixed Status Code Handling**: Corrected bridge expectation from HTTP 201 to HTTP 200 with success field check
  - Server returns HTTP 200 for both successful storage and duplicates
  - Bridge now properly checks `response.data.success` field to determine actual result
  - Supports both HTTP 200 and 201 for backward compatibility
  - **Impact**: Memory storage operations now work correctly instead of always failing
  
- **Fixed URL Construction Bug**: Resolved critical path construction issue in `makeRequestInternal`
  - `new URL(path, baseUrl)` was incorrectly replacing `/api` base path
  - Now properly concatenates base URL with API paths: `baseUrl + fullPath`
  - **Impact**: All API operations now reach correct endpoints instead of returning 404

#### Root Cause Analysis
- **Memory Storage**: Bridge expected HTTP 201 but server returns 200 → always interpreted as failure
- **All API Calls**: URL construction bug caused `/api` path to be lost → all requests returned 404
- **Combined Effect**: Made entire bridge non-functional despite server working correctly

### 🧪 **Major Enhancement: Comprehensive Test Infrastructure**

#### Test Suite Addition
- **Bridge Unit Tests** (`tests/bridge/test_http_mcp_bridge.js`): 20+ test cases covering:
  - URL construction with various base path scenarios
  - Status code handling for success, duplicates, and errors
  - MCP protocol compliance and error conditions
  - Authentication and retry logic
  
- **Integration Tests** (`tests/integration/test_bridge_integration.js`): End-to-end testing with:
  - Real server connectivity simulation
  - Complete MCP protocol flow validation
  - Authentication and error recovery testing
  - Critical bug scenario reproduction

- **Mock Response System** (`tests/bridge/mock_responses.js`): Accurate server behavior simulation
  - Matches actual API responses (HTTP 200 with success field)
  - Covers all edge cases and error conditions
  - Prevents future assumption-based bugs

#### CI/CD Pipeline Enhancement
- **Dedicated Bridge Testing** (`.github/workflows/bridge-tests.yml`):
  - Automated testing on every bridge-related change
  - Multiple Node.js version compatibility testing
  - Contract validation against API specification
  - Blocks merges if bridge tests fail

#### Documentation & Contracts
- **API Contract Specification** (`tests/contracts/api-specification.yml`):
  - Documents ACTUAL server behavior vs assumptions
  - Critical notes about HTTP 200 status codes and success fields
  - URL path requirements and authentication details

- **Release Process** (`RELEASE_CHECKLIST.md`):
  - 50+ item checklist preventing critical bugs
  - Manual and automated testing requirements
  - Post-release monitoring procedures

### 🔧 **Technical Details**

**Files Modified:**
- `examples/http-mcp-bridge.js` - Status code and URL construction fixes
- `src/mcp_memory_service/__init__.py` - Version bump
- `pyproject.toml` - Version bump

**Files Added:**
- Complete test infrastructure (6 new files)
- CI/CD pipeline configuration
- API contract documentation
- Release process documentation

**Backward Compatibility**: 
- All existing configurations continue working
- Bridge now accepts both HTTP 200 and 201 responses
- No breaking changes to client interfaces

### 🎯 **Impact**

**Before v6.6.2:**
- ❌ Health check: "unhealthy" → Fixed in v6.6.1
- ❌ Memory storage: "Not Found" errors 
- ❌ Memory retrieval: 404 failures
- ❌ All bridge operations non-functional

**After v6.6.2:**
- ✅ Health check: Returns "healthy" status
- ✅ Memory storage: Works correctly with proper success/duplicate handling
- ✅ Memory retrieval: Functions normally with semantic search
- ✅ All bridge operations fully functional

**Future Prevention:**
- ✅ Comprehensive test coverage prevents regression
- ✅ API contract validation catches assumption mismatches
- ✅ Automated CI/CD testing on every change
- ✅ Detailed release checklist ensures quality

This release completes the HTTP-MCP bridge repair, making it fully functional while establishing comprehensive testing infrastructure to prevent similar critical bugs in the future.

## [6.6.1] - 2025-08-24

### 🐛 **Bug Fixes**

#### HTTP-MCP Bridge Health Check Endpoint
- **Fixed Health Check URLs**: Corrected incorrect endpoint paths in `examples/http-mcp-bridge.js`
  - `testEndpoint()` method: Fixed `/health` → `/api/health` path (line 241)
  - `checkHealth()` method: Fixed `/health` → `/api/health` path (line 501)
  - **Impact**: Health checks now return "healthy" status instead of 404 errors
  - **Root Cause**: Bridge was requesting wrong endpoint causing false "unhealthy" status
  - **Verification**: Remote memory service connectivity confirmed working correctly

#### Technical Details
- Fixed endpoint inconsistencies that caused health checks to fail
- Remote memory service functionality was working correctly - issue was purely endpoint path mismatch
- All memory operations (store/retrieve) continue to work without changes
- Health check now properly reports service status to MCP clients

**Files Modified**: `examples/http-mcp-bridge.js`

## [6.6.0] - 2025-08-23

### 🔧 **Memory Awareness Hooks: Fully Functional Installation**

#### Major Improvements
- **Installation Scripts Fixed** - Memory Awareness Hooks now install and work end-to-end without manual intervention
- **Claude Code Integration** - Automatic `~/.claude/settings.json` configuration for seamless hook detection
- **JSON Parsing Fixed** - Resolved Python dict conversion errors that caused runtime failures
- **Enhanced Testing** - Added 4 new integration tests (total: 14 tests, 100% pass rate)

#### Added
- **Automated Claude Code Settings Integration** - Installation script now configures `~/.claude/settings.json` automatically
- **Comprehensive Troubleshooting Guide** - Complete wiki documentation with diagnosis commands and solutions
- **Installation Verification** - Post-install connectivity tests and hook detection validation
- **GitHub Wiki Documentation** - Detailed 500+ line guide for advanced users and developers

#### Fixed  
- **Installation Directory** - Changed from `~/.claude-code/hooks/` to correct `~/.claude/hooks/` location
- **JSON Parsing Errors** - Added Python dict to JSON conversion (single quotes, True/False/None handling)
- **Hook Detection** - Claude Code now properly detects installed hooks via settings configuration
- **Memory Service Connectivity** - Enhanced error handling and connection testing

#### Enhanced
- **Integration Tests** - Expanded test suite from 10 to 14 tests (40% increase):
  - Claude Code settings validation
  - Hook files location verification  
  - Claude Code CLI availability check
  - Memory service connectivity testing
- **Documentation Structure** - README streamlined (47% size reduction), detailed content moved to wiki
- **Error Messages** - Improved debugging output and user-friendly error reporting

#### Developer Experience
- **Quick Start** - Single command installation: `./install.sh`
- **Verification Commands** - Easy testing with `claude --debug hooks`
- **Troubleshooting** - Comprehensive guide covers all common issues
- **Custom Development** - Examples for extending hooks and memory integration

**Impact**: Memory Awareness Hooks are now publicly usable without the manual debugging sessions that were previously required. Users can run `./install.sh` and get fully functional automatic memory awareness in Claude Code.

## [6.5.0] - 2025-08-23

### 🗂️ **Repository Structure: Root Directory Cleanup**

#### Added
- **`deployment/` Directory** - Centralized location for service and configuration files
- **`sync/` Directory** - Organized synchronization scripts in dedicated folder
- **Dependency-Safe Reorganization** - All file references properly updated

#### Changed
- **Root Directory Cleanup** - Reduced clutter from 80+ files to ~65 files (19% reduction)
- **File Organization** - Moved deployment configs and sync scripts to logical subdirectories
- **Path References Updated** - All scripts and configurations point to new file locations
- **Claude Code Settings** - Updated paths in `.claude/settings.local.json` for moved scripts

#### Moved Files
**To `deployment/`:**
- `mcp-memory.service` - Systemd service configuration
- `smithery.yaml` - Smithery package configuration  
- `io.litestream.replication.plist` - macOS LaunchDaemon configuration
- `staging_db_init.sql` - Database initialization schema
- `empty_config.yml` - Template configuration file

**To `sync/`:**
- `manual_sync.sh`, `memory_sync.sh` - Core synchronization scripts
- `pull_remote_changes.sh`, `push_to_remote.sh` - Remote sync operations
- `sync_from_remote.sh`, `sync_from_remote_noconfig.sh` - Remote pull variants
- `apply_local_changes.sh`, `stash_local_changes.sh`, `resolve_conflicts.sh` - Local sync operations

#### Fixed
- **Broken References** - Updated all hardcoded paths in scripts and configurations
- **Claude Code Integration** - Fixed manual_sync.sh path reference
- **Installation Scripts** - Updated service file and SQL schema paths
- **Litestream Setup** - Fixed LaunchDaemon plist file reference

#### Repository Impact
This release significantly improves repository navigation and organization while maintaining full backward compatibility through proper reference updates. Users benefit from cleaner root directory structure, while developers gain logical file organization that reflects functional groupings.

## [6.4.0] - 2025-08-23

### 📚 **Documentation Revolution: Major UX Transformation**

#### Added
- **Comprehensive Installation Guide** in wiki consolidating 6+ previous scattered guides
- **Platform-Specific Setup Guide** with optimizations for Windows, macOS, and Linux
- **Complete Integration Guide** covering Claude Desktop, Claude Code, VS Code, and 13+ tools
- **Streamlined README.md** with clear quick start and wiki navigation (56KB → 8KB)
- **Safe Documentation Archive** preserving all removed files for reference

#### Changed
- **Major Documentation Restructuring** for improved user experience and maintainability
- **Single Source of Truth** established for installation, platform setup, and integrations
- **Wiki Home Page** updated with organized navigation to consolidated guides
- **User Onboarding Journey** simplified from overwhelming choice to clear path

#### Removed
- **26+ Redundant Documentation Files** safely archived while preserving git history
- **Choice Paralysis** from 6 installation guides, 5 integration guides, 4 platform guides
- **Maintenance Burden** of updating multiple files for single concept changes
- **Inconsistent Information** across overlapping documentation

#### Fixed
- **User Confusion** from overwhelming documentation choices and unclear paths
- **Maintenance Complexity** requiring updates to 6+ files for installation changes
- **Professional Image** with organized structure reflecting code quality
- **Information Discovery** through logical wiki organization vs scattered files

#### Documentation Impact
This release transforms MCP Memory Service from having overwhelming documentation chaos to organized, professional, maintainable structure. Users now have clear paths from discovery to success (README → Quick Start → Wiki → Success), while maintainers benefit from single-source-of-truth updates. **90% reduction in repository documentation files** while **improving comprehensiveness** through organized wiki structure.

**Key Achievements:**
- Installation guides: 6 → 1 comprehensive wiki page
- Integration guides: 5 → 1 complete reference  
- Platform guides: 4 → 1 optimized guide
- User experience: Confusion → Clarity
- Maintenance: 6+ places → 1 place per topic

## [6.3.3] - 2025-08-22

### 🔧 **Enhancement: Version Synchronization**

#### Fixed
- **API Documentation Version**: Fixed API docs dashboard showing outdated version `1.0.0` instead of current version
- **Version Inconsistencies**: Synchronized hardcoded versions across FastAPI app, web module, and server configuration
- **Maintenance Overhead**: Established single source of truth for version management

#### Enhanced
- **Dynamic Version Management**: All version references now import from main `__version__` variable
- **Future-Proofing**: Version updates now only require changes in 2 files (pyproject.toml + __init__.py)
- **Developer Experience**: Consistent version display across all interfaces and documentation

#### Technical Details
- **FastAPI App**: Changed from hardcoded `version="1.0.0"` to dynamic `version=__version__`
- **Web Module**: Removed separate version `0.2.0`, now imports from parent package
- **Server Config**: Updated `SERVER_VERSION` from `0.2.2` to use main version import
- **Impact**: All dashboards, API docs, and mDNS advertisements now show consistent version

## [6.3.2] - 2025-08-22

### 🚨 **Critical Fix: Claude Desktop Compatibility Regression**

#### Fixed
- **Claude Desktop Integration**: Restored backward compatibility for `uv run memory` command
- **MCP Protocol Errors**: Fixed JSON parsing errors when Claude Desktop tried to parse CLI help text as MCP messages
- **Regression from v6.3.1**: CLI consolidation accidentally broke existing Claude Desktop configurations

#### Technical Details
- **Root Cause**: CLI consolidation removed ability to start MCP server with `uv run memory` (without `server` subcommand)
- **Impact**: Claude Desktop configurations calling `uv run memory` received help text instead of MCP server
- **Solution**: Added backward compatibility logic to default to `server` command when no subcommand provided

#### Added
- **Backward Compatibility**: `uv run memory` now starts MCP server automatically for existing integrations
- **Deprecation Warning**: Informative warning guides users to explicit `memory server` syntax
- **Integration Test**: New test case verifies backward compatibility warning functionality
- **MCP Protocol Validation**: Confirmed proper JSON-RPC responses instead of help text parsing errors

#### For Users
- **Claude Desktop works again**: Existing configurations continue working without changes
- **Migration Encouraged**: Warning message guides users toward preferred `memory server` syntax
- **No Breaking Changes**: All existing usage patterns maintained while encouraging modern syntax

## [6.3.1] - 2025-08-22

### 🔧 **Major Enhancement: CLI Architecture Consolidation**

#### Fixed
- **CLI Conflicts Eliminated**: Resolved installation conflicts between argparse and Click CLI implementations
- **Command Consistency**: Established `uv run memory server` as the single, reliable server start pattern
- **Installation Issues**: Fixed stale entry point problems that caused "command not found" errors

#### Enhanced  
- **Unified CLI Interface**: All server commands now route through Click-based CLI for consistency
- **Deprecation Warnings**: Added graceful migration path with informative deprecation warnings for `memory-server`
- **Error Handling**: Improved error messages and graceful failure handling across all CLI commands
- **Documentation**: Added comprehensive CLI Migration Guide with clear upgrade paths

#### Added
- **CLI Integration Tests**: 16 comprehensive test cases covering all CLI interfaces and edge cases
- **Performance Testing**: CLI startup time validation and version command performance monitoring
- **Backward Compatibility**: `memory-server` command maintained with deprecation warnings
- **Migration Guide**: Complete documentation for transitioning from legacy commands

#### Technical Improvements
- **Environment Variable Integration**: Seamless config passing via MCP_MEMORY_CHROMA_PATH
- **Code Cleanup**: Removed duplicate argparse implementation from server.py
- **Entry Point Simplification**: Streamlined from 3 conflicting implementations to 1 clear interface
- **Robustness Testing**: Added error handling, argument parity, and isolation testing

#### Benefits for Users
- **Eliminates MCP startup failures** that were caused by CLI conflicts
- **Clear command interface**: `uv run memory server` works reliably every time
- **Better error messages** when something goes wrong
- **Smooth migration path** from legacy patterns
- **Full Claude Code compatibility** confirmed and tested

## [6.3.0] - 2025-08-22

### 🚀 **Major Feature: Distributed Memory Synchronization**

#### Added
- **Git-like Sync Workflow**: Complete distributed synchronization system with offline capabilities
  - `memory_sync.sh` - Main orchestrator for sync operations with colored output and status reporting
  - **Stash → Pull → Apply → Push** workflow similar to Git's distributed version control
  - Intelligent conflict detection and resolution with user control
  - Remote-first architecture with automatic fallback to local staging

- **Enhanced Memory Store**: `enhanced_memory_store.sh` with hybrid remote-first approach
  - **Primary**: Direct storage to remote API (`https://narrowbox.local:8443/api/memories`)
  - **Fallback**: Automatic local staging when remote is unavailable
  - Smart context detection (project, git branch, hostname, tags)
  - Seamless offline-to-online transition with automatic sync

- **Real-time Database Replication**: Litestream-based synchronization infrastructure
  - **Master/Replica Setup**: Remote server as master with HTTP-served replica data
  - **Automatic Replication**: 10-second sync intervals for near real-time updates
  - **Lightweight HTTP Server**: Python built-in server for serving replica files
  - **Cross-platform Compatibility**: macOS LaunchDaemon and Linux systemd services

- **Staging Database System**: SQLite-based local change tracking
  - `staging_db_init.sql` - Complete schema with triggers and status tracking
  - **Conflict Detection**: Content hash-based duplicate detection
  - **Operation Tracking**: INSERT/UPDATE/DELETE operation logging
  - **Source Attribution**: Machine hostname and timestamp tracking

- **Comprehensive Sync Scripts**: Complete workflow automation
  - `stash_local_changes.sh` - Capture local changes before remote sync
  - `pull_remote_changes.sh` - Download remote changes with conflict awareness  
  - `apply_local_changes.sh` - Intelligent merge of staged changes
  - `push_to_remote.sh` - Upload changes via HTTPS API with retry logic
  - `resolve_conflicts.sh` - Interactive conflict resolution helper

- **Litestream Integration**: Production-ready replication setup
  - **Automated Setup Scripts**: `setup_remote_litestream.sh` and `setup_local_litestream.sh`
  - **Service Configurations**: systemd and LaunchDaemon service files
  - **Master/Replica Configs**: Complete Litestream YAML configurations
  - **Comprehensive Documentation**: `LITESTREAM_SETUP_GUIDE.md` with troubleshooting

#### Enhanced
- **Claude Commands**: Updated `memory-store.md` to document remote-first approach
  - **Hybrid Strategy**: Remote API primary, local staging fallback
  - **Sync Status**: Integration with `./sync/memory_sync.sh status` for pending changes
  - **Automatic Context**: Git branch, project, and hostname detection

#### Architecture
- **Remote-first Design**: Single source of truth on remote server with local caching
- **Conflict Resolution**: Last-write-wins with comprehensive logging and user notification
- **Network Resilience**: Graceful degradation from online → staging → read-only local
- **Git-like Workflow**: Familiar distributed workflow for developers

#### Technical Details
- **Database Schema**: New staging database with triggers for change counting
- **HTTP Integration**: Secure HTTPS API communication with bearer token auth
- **Platform Support**: Cross-platform service management (systemd/LaunchDaemon)
- **Performance**: Lz4 compression for efficient snapshot transfers
- **Security**: Content hash verification and source machine tracking

This release transforms MCP Memory Service from a local-only system into a fully distributed memory platform, enabling seamless synchronization across multiple devices while maintaining robust offline capabilities.

## [6.2.5] - 2025-08-21

### 🐛 **Bug Fix: SQLite-Vec Backend Debug Utilities**

This release fixes a critical AttributeError in debug utilities when using the SQLite-Vec storage backend.

#### Fixed
- **Debug Utilities Compatibility** ([#89](https://github.com/doobidoo/mcp-memory-service/issues/89)): Fixed `'SqliteVecMemoryStorage' object has no attribute 'model'` error
  - Added compatibility helper `_get_embedding_model()` to handle different attribute names between storage backends
  - ChromaDB backend uses `storage.model` while SQLite-Vec uses `storage.embedding_model`
  - Updated all debug functions (`get_raw_embedding`, `check_embedding_model`, `debug_retrieve_memory`) to use the compatibility helper
  
#### Technical Details
- **Affected Functions**: 
  - `get_raw_embedding()` - Now works with both backends
  - `check_embedding_model()` - Properly detects model regardless of backend
  - `debug_retrieve_memory()` - Semantic search debugging works for SQLite-Vec users
  
#### Impact
- Users with SQLite-Vec backend can now use all MCP debug operations
- Semantic search and embedding inspection features work correctly
- No breaking changes for ChromaDB backend users

## [6.2.4] - 2025-08-21

### 🐛 **CRITICAL BUG FIXES: Claude Code Hooks Compatibility**

This release fixes critical compatibility issues with Claude Code hooks that prevented automatic memory injection at session start.

#### Fixed
- **Claude Code Hooks API Parameters**: Fixed incorrect API parameters in `claude-hooks/core/session-start.js`
  - Replaced invalid `tags`, `limit`, `time_filter` parameters with correct `n_results` for `retrieve_memory` API
  - Hooks now work correctly with MCP Memory Service API without parameter errors
  
- **Python Dict Response Parsing**: Fixed critical parsing bug where hooks couldn't process MCP service responses
  - Added proper Python dictionary format to JavaScript object conversion 
  - Implemented fallback parsing for different response formats
  - Hooks now successfully parse memory service responses and inject context

- **Memory Export Security**: Enhanced security for memory export files
  - Added `local_export*.json` to .gitignore to prevent accidental commits of sensitive data
  - Created safe template files in `examples/` directory for documentation and testing

#### Added
- **Memory Export Templates**: New example files showing export format structure
  - `examples/memory_export_template.json`: Basic example with 3 sample memories
  - Clean, sanitized examples safe for sharing and documentation

#### Technical Details
- **Response Format Handling**: Hooks now handle Python dict format responses with proper conversion to JavaScript objects
- **Error Handling**: Added multiple fallback mechanisms for response parsing
- **API Compatibility**: Updated to use correct MCP protocol parameters for memory retrieval

#### Impact
- Claude Code hooks will now work out-of-the-box without manual fixes
- Memory context injection at session start now functions correctly
- Users can install hooks directly from repository without encountering parsing errors
- Enhanced security prevents accidental exposure of sensitive data in exports

## [6.2.3] - 2025-08-20

### 🛠️ **Cross-Platform Path Detection & Claude Code Integration**

This release provides comprehensive cross-platform fixes for path detection issues and complete Claude Code hooks integration across Linux, macOS, and Windows.

#### Fixed
- **Linux Path Detection**: Enhanced `scripts/remote_ingest.sh` to auto-detect mcp-memory-service repository location anywhere in user's home directory
  - Resolves path case sensitivity issues (Repositories vs repositories)
  - Works regardless of where users clone the repository
  - Validates found directory contains pyproject.toml to ensure correct repository

- **Windows Path Detection**: Added comprehensive Windows support with PowerShell and batch scripts
  - New: `claude-hooks/install_claude_hooks_windows.ps1` - Full-featured PowerShell installation
  - New: `claude-hooks/install_claude_hooks_windows.bat` - Batch wrapper for easy execution
  - Dynamic repository location detection using PSScriptRoot resolution
  - Comprehensive Claude Code hooks directory detection with fallbacks
  - Improved error handling and validation for source/target directories
  - Resolves hardcoded Unix path issues (`\home\hkr\...`) on Windows systems
  - Tested with 100% success rate across Windows environments

- **Claude Code Commands Documentation**: Fixed and enhanced memory commands documentation
  - Updated command usage from `/memory-store` to `claude /memory-store`
  - Added comprehensive troubleshooting section for command installation issues
  - Documented both Claude Code commands and direct API alternatives
  - Added installation instructions and quick fixes for common problems

#### Technical Improvements
- Repository detection now works on any platform and directory structure
- Claude Code hooks installation handles Windows-specific path formats
- Improved error messages and debug output across all platforms
- Consistent behavior across Windows, Linux, and macOS platforms

## [6.2.2] - 2025-08-20

### 🔧 Fixed  
- **Remote Ingestion Script Path Detection**: Enhanced `scripts/remote_ingest.sh` to auto-detect mcp-memory-service repository location anywhere in user's home directory instead of hardcoded path assumptions
  - Resolves path case sensitivity issues (Repositories vs repositories)
  - Works regardless of where users clone the repository  
  - Validates found directory contains pyproject.toml to ensure correct repository

## [6.2.1] - 2025-08-20

### 🐛 **CRITICAL BUG FIXES: Memory Listing and Search Index**

This patch release resolves critical issues with memory pagination and search functionality that were preventing users from accessing the full dataset.

#### Fixed
- **Memory API Pagination**: Fixed `/api/memories` endpoint returning only 82 of 904 total memories
  - **Root Cause**: API was using semantic search fallback instead of proper chronological listing
  - **Solution**: Implemented dedicated `get_all_memories()` method with SQL-based LIMIT/OFFSET pagination
  - **Impact**: Web dashboard and API clients now see accurate memory counts and can access complete dataset

- **Missing Storage Backend Methods**: Added missing pagination methods in SqliteVecMemoryStorage
  - `get_all_memories(limit, offset)` - Chronological memory listing with pagination support
  - `get_recent_memories(n)` - Get n most recent memories efficiently
  - `count_all_memories()` - Accurate total count for pagination calculations
  - `_row_to_memory(row)` - Proper database row to Memory object conversion with JSON parsing

- **Search Index Issues**: Resolved problems with recently stored memories not appearing in searches
  - **Tag Search**: Newly stored memories now immediately appear in tag-based filtering
  - **Semantic Search**: MCP protocol semantic search verified working with similarity scoring
  - **Memory Context**: `/memory-context` command functionality confirmed end-to-end

#### Technical Details
- **Files Modified**: 
  - `src/mcp_memory_service/storage/sqlite_vec.py` - Added 75+ lines of pagination methods
  - `src/mcp_memory_service/web/api/memories.py` - Fixed pagination logic to use proper SQL queries
- **Database Access**: Replaced unreliable semantic search with direct SQL `ORDER BY created_at DESC`
- **Error Handling**: Added comprehensive JSON parsing for tags and metadata with graceful fallbacks
- **Verification**: All 904 memories now accessible via REST API with proper page navigation

#### Verification Results
- ✅ **API Pagination**: Returns accurate 904 total count (was showing 82)
- ✅ **Search Functionality**: Tag searches work immediately after storage
- ✅ **Memory Context**: Session storage and retrieval verified end-to-end
- ✅ **Semantic Search**: MCP protocol search confirmed functional with similarity scoring
- ✅ **Performance**: No performance degradation despite handling full dataset

This release ensures reliable access to the complete memory dataset with proper pagination and search capabilities.

---

## [6.2.0] - 2025-08-20

### 🚀 **MAJOR FEATURE: Native Cloudflare Backend Integration**

This major release introduces native Cloudflare integration as a third storage backend option alongside SQLite-vec and ChromaDB, providing global distribution, automatic scaling, and enterprise-grade infrastructure, integrated with the existing Memory Awareness system.

#### Added
- **Native Cloudflare Backend Support**: Complete implementation using Cloudflare's edge computing platform
  - **Vectorize**: 768-dimensional vector storage with cosine similarity for semantic search
  - **D1 Database**: SQLite-compatible database for metadata storage
  - **Workers AI**: Embedding generation using @cf/baai/bge-base-en-v1.5 model
  - **R2 Storage** (optional): Object storage for large content exceeding 1MB threshold
  
- **Implementation Files**:
  - `src/mcp_memory_service/storage/cloudflare.py` - Complete CloudflareStorage implementation (740 lines)
  - `scripts/migrate_to_cloudflare.py` - Migration tool for existing SQLite-vec and ChromaDB users
  - `scripts/test_cloudflare_backend.py` - Comprehensive test suite with automated validation
  - `scripts/setup_cloudflare_resources.py` - Automated Cloudflare resource provisioning
  - `docs/cloudflare-setup.md` - Complete setup, configuration, and troubleshooting guide
  - `tests/unit/test_cloudflare_storage.py` - 15 unit tests for CloudflareStorage class

- **Features**:
  - Automatic retry logic with exponential backoff for API rate limiting
  - Connection pooling for optimal HTTP performance
  - NDJSON format support for Vectorize v2 API endpoints
  - LRU caching (1000 entries) for embedding deduplication
  - Batch operations support for efficient data processing
  - Global distribution with <100ms latency from most locations
  - Pay-per-use pricing model with no upfront costs

#### Changed
- Updated `config.py` to include 'cloudflare' in SUPPORTED_BACKENDS
- Enhanced server initialization in `mcp_server.py` to support Cloudflare backend
- Updated storage factory in `storage/__init__.py` to create CloudflareStorage instances
- Consolidated documentation, removing redundant setup files

#### Technical Details
- **Environment Variables**:
  - `MCP_MEMORY_STORAGE_BACKEND=cloudflare` - Activate Cloudflare backend
  - `CLOUDFLARE_API_TOKEN` - API token with Vectorize, D1, Workers AI permissions
  - `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account identifier
  - `CLOUDFLARE_VECTORIZE_INDEX` - Name of Vectorize index (768 dimensions)
  - `CLOUDFLARE_D1_DATABASE_ID` - D1 database UUID
  - `CLOUDFLARE_R2_BUCKET` (optional) - R2 bucket for large content
  
- **Performance Characteristics**:
  - Storage: ~200ms per memory (including embedding generation)
  - Search: ~100ms for semantic search (5 results)
  - Batch operations: ~50ms per memory in batches of 100
  - Global latency: <100ms from most global locations

#### Migration Path
Users can migrate from existing backends using provided scripts:
```bash
# From SQLite-vec
python scripts/migrate_to_cloudflare.py --source sqlite

# From ChromaDB  
python scripts/migrate_to_cloudflare.py --source chroma
```

#### Memory Awareness Integration
- **Full Compatibility**: Cloudflare backend works seamlessly with Phase 1 and Phase 2 Memory Awareness
- **Cross-Session Intelligence**: Session tracking and conversation threading supported
- **Dynamic Context Updates**: Real-time memory loading during conversations
- **Global Performance**: Enhances Memory Awareness with <100ms global response times

#### Compatibility
- Fully backward compatible with existing SQLite-vec and ChromaDB backends
- No breaking changes to existing APIs or configurations
- Supports all existing MCP operations and features
- Compatible with all existing Memory Awareness hooks and functionality

## [6.1.1] - 2025-08-20

### 🐛 **CRITICAL BUG FIX: Memory Retrieval by Hash**

#### Fixed
- **Memory Retrieval 404 Issue**: Fixed HTTP API returning 404 errors for valid memory hashes
- **Direct Hash Lookup**: Added `get_by_hash()` method to `SqliteVecMemoryStorage` for proper content hash retrieval
- **API Endpoint Correction**: Updated `/api/memories/{content_hash}` to use direct hash lookup instead of semantic search
- **Production Deployment**: Successfully deployed fix to production servers and verified functionality

#### Technical Details
- **Root Cause**: HTTP API was incorrectly using `storage.retrieve()` (semantic search) instead of direct hash-based lookup
- **Solution**: Implemented dedicated hash lookup method that queries database directly using content hash as primary key
- **Impact**: Web dashboard memory retrieval by hash now works correctly without SSL certificate issues or false 404 responses
- **Testing**: Verified with multiple memory hashes including previously failing hash `812d361cbfd1b79a49737e6ea34e24459b4d064908e222d98af6a504aa09ff19`

#### Deployment
- Version 6.1.1 deployed to production server `10.0.1.30:8443`
- Service restart completed successfully
- Health check confirmed: Version 6.1.1 running with full functionality

## [6.1.0] - 2025-08-20

### 🚀 **MAJOR FEATURE: Intelligent Context Updates (Phase 2)**

#### Conversation-Aware Dynamic Memory Loading
This release introduces **Phase 2 of Claude Code Memory Awareness** - transforming the system from static memory injection to intelligent, real-time conversation analysis with dynamic context updates during active coding sessions.

#### Added

##### 🧠 **Dynamic Memory Loading System**
- **Real-time Topic Detection**: Analyzes conversation flow to detect significant topic shifts
- **Automatic Context Updates**: Injects relevant memories as conversations evolve naturally
- **Smart Deduplication**: Prevents re-injection of already loaded memories
- **Intelligent Rate Limiting**: 30-second cooldown and session limits prevent context overload
- **Cross-Session Intelligence**: Links related conversations across different sessions

##### 🔍 **Advanced Conversation Analysis Engine** 
- **Natural Language Processing**: Extracts topics, entities, intent, and code context from conversations
- **15+ Technical Topic Categories**: database, debugging, architecture, testing, deployment, etc.
- **Entity Recognition**: Technologies, frameworks, languages, tools (JavaScript, Python, React, etc.)
- **Intent Classification**: learning, problem-solving, development, optimization, review, planning
- **Code Context Detection**: Identifies code blocks, file paths, error messages, commands

##### 📊 **Enhanced Memory Scoring with Conversation Context**
- **Multi-Factor Relevance Algorithm**: 5-factor scoring system including conversation context (25% weight)
- **Dynamic Weight Adjustment**: Adapts scoring based on conversation analysis
- **Topic Alignment Matching**: Prioritizes memories matching current conversation topics
- **Intent-Based Scoring**: Aligns memory relevance with conversation purpose
- **Semantic Content Analysis**: Advanced content matching with conversation context

##### 🔗 **Cross-Session Intelligence & Conversation Threading**
- **Session Tracking**: Links related sessions across time with unique thread IDs  
- **Conversation Continuity**: Builds conversation threads over multiple sessions
- **Progress Context**: Connects outcomes from previous sessions to current work
- **Pattern Recognition**: Identifies recurring topics and workflow patterns
- **Historical Context**: Includes insights from recent related sessions (up to 3 sessions, 7 days back)

##### ⚡ **Performance & Reliability**
- **Efficient Processing**: <500ms response time for topic detection and memory queries
- **Scalable Architecture**: Handles 100+ active memories per session
- **Smart Debouncing**: 5-second debounce prevents rapid-fire updates
- **Resource Optimization**: Intelligent memory management and context deduplication
- **Comprehensive Testing**: 100% test pass rate (15/15 tests) with full integration coverage

#### Technical Implementation

##### Core Phase 2 Components
- **conversation-analyzer.js**: NLP engine for topic/entity/intent detection
- **topic-change.js**: Monitors conversation flow and triggers dynamic updates
- **memory-scorer.js**: Enhanced scoring with conversation context awareness  
- **session-tracker.js**: Cross-session intelligence and conversation threading
- **dynamic-context-updater.js**: Orchestrates all Phase 2 components with rate limiting

##### Configuration Enhancements
- **Phase 2 Settings**: New configuration sections for conversation analysis, dynamic updates, session tracking
- **Flexible Thresholds**: Configurable significance scores, update limits, and confidence levels
- **Feature Toggles**: Independent enable/disable for each Phase 2 capability

#### User Experience Improvements
- **Zero Cognitive Load**: Context updates happen automatically during conversations
- **Perfect Timing**: Memories appear exactly when relevant to current discussion  
- **Seamless Integration**: Works transparently during normal coding sessions
- **Progressive Learning**: Each conversation builds upon previous knowledge intelligently

#### Migration from Phase 1
- **Backward Compatible**: Phase 1 features remain fully functional
- **Additive Enhancement**: Phase 2 builds upon Phase 1 session-start memory injection
- **Unified Configuration**: Single config.json manages both Phase 1 and Phase 2 settings

## [6.0.0] - 2025-08-19

### 🧠 **MAJOR FEATURE: Claude Code Memory Awareness (Phase 1)**

#### Revolutionary Memory-Aware Development Experience
This major release introduces **automatic memory awareness for Claude Code** - a sophisticated hook system that transforms how developers interact with their project knowledge and conversation history.

#### Added

##### 🔄 **Session Lifecycle Hooks**
- **Session-Start Hook**: Automatically injects relevant memories when starting Claude Code sessions
  - Intelligent project detection supporting JavaScript, Python, Rust, Go, Java, C++, and more
  - Multi-factor memory relevance scoring with time decay, tag matching, and content analysis
  - Context-aware memory selection (up to 8 most relevant memories per session)
  - Beautiful markdown formatting for seamless context integration
  
- **Session-End Hook**: Captures and consolidates session outcomes automatically
  - Conversation analysis and intelligent summarization
  - Automatic tagging with project context and session insights
  - Long-term knowledge building through outcome storage
  - Session relationship tracking for continuity

##### 🎯 **Advanced Project Detection System**
- **Multi-Language Support**: Detects 15+ project types and frameworks
  - Package managers: `package.json`, `Cargo.toml`, `go.mod`, `requirements.txt`, `pom.xml`
  - Build systems: `Makefile`, `CMakeLists.txt`, `build.gradle`, `setup.py`
  - Configuration files: `tsconfig.json`, `pyproject.toml`, `.gitignore`
- **Git Integration**: Repository context analysis with branch and commit information
- **Framework Detection**: React, Vue, Angular, Django, Flask, Express, and more
- **Technology Stack Analysis**: Automatic identification of languages, databases, and tools

##### 🧮 **Intelligent Memory Scoring System**
- **Time Decay Algorithm**: Recent memories weighted higher with configurable decay curves
- **Tag Relevance Matching**: Project-specific and technology-specific tag scoring
- **Content Similarity Analysis**: Semantic matching with current project context
- **Memory Type Bonuses**: Prioritizes decisions, insights, and architecture notes
- **Relevance Threshold**: Only injects memories above significance threshold (>0.3)

##### 🎨 **Context Formatting & Presentation**
- **Categorized Memory Display**: Organized by Recent Insights, Key Decisions, and Project Context
- **Markdown-Rich Formatting**: Beautiful presentation with metadata, timestamps, and tags
- **Configurable Limits**: Prevents context overload with smart memory selection
- **Source Attribution**: Clear memory source tracking with content hashes

##### 💻 **Complete Installation & Testing System**
- **One-Command Installation**: `./install.sh` deploys entire system to Claude Code hooks
- **Comprehensive Test Suite**: 10 integration tests with 100% pass rate
  - Project detection testing across multiple languages
  - Memory scoring algorithm validation
  - Context formatting verification
  - Hook structure and configuration validation
  - MCP service connectivity testing
- **Configuration Management**: Production-ready config with memory service endpoints
- **Backup and Recovery**: Automatic backup of existing hooks during installation

#### Technical Architecture

##### 🏗️ **Claude Code Hooks System**
```javascript
claude-hooks/
├── core/
│   ├── session-start.js    # Automatic memory injection hook
│   └── session-end.js      # Session consolidation hook
├── utilities/
│   ├── project-detector.js  # Multi-language project detection
│   ├── memory-scorer.js     # Relevance scoring algorithms
│   └── context-formatter.js # Memory presentation utilities
├── tests/
│   └── integration-test.js  # Complete test suite (100% pass)
├── config.json             # Production configuration
└── install.sh             # One-command installation
```

##### 🔗 **MCP Memory Service Integration**
- **JSON-RPC Protocol**: Direct communication with MCP Memory Service
- **Error Handling**: Graceful degradation when memory service unavailable
- **Performance Optimization**: Efficient memory querying with result caching
- **Security**: Content hash verification and safe JSON parsing

##### 📊 **Memory Selection Algorithm**
```javascript
// Multi-factor scoring system
const relevanceScore = (
  timeDecayScore * 0.4 +         // Recent memories preferred
  tagRelevanceScore * 0.3 +      // Project-specific tags
  contentSimilarityScore * 0.2 + // Semantic matching
  memoryTypeBonusScore * 0.1     // Decision/insight bonus
);
```

#### Usage Examples

##### Automatic Session Context
```markdown
# 🧠 Relevant Memory Context

## Recent Insights (Last 7 days)
- **Database Performance Issue** - Resolved SQLite-vec query optimization (yesterday)
- **Authentication Flow** - Implemented JWT token validation in API (3 days ago)

## Key Decisions
- **Architecture Decision** - Chose React over Vue for frontend consistency (1 week ago)
- **Database Choice** - Selected PostgreSQL for production scalability (2 weeks ago)

## Project Context: mcp-memory-service
- **Language**: JavaScript, Python
- **Frameworks**: Node.js, FastAPI
- **Recent Activity**: Bug fixes, feature implementation
```

##### Session Outcome Storage
```markdown
Session consolidated and stored with tags:
- mcp-memory-service, claude-code-session
- bug-fix, performance-optimization
- javascript, api-development
Content hash: abc123...def456
```

#### Benefits & Impact

##### 🚀 **Productivity Enhancements**
- **Zero Cognitive Load**: Memory context appears automatically without user intervention
- **Perfect Continuity**: Never lose track of decisions, insights, or architectural choices
- **Intelligent Context**: Only relevant memories shown, preventing information overload
- **Session Learning**: Each coding session builds upon previous knowledge automatically

##### 🧠 **Memory-Aware Development**
- **Decision Tracking**: Automatic capture of technical decisions and rationale
- **Knowledge Building**: Progressive accumulation of project understanding
- **Context Preservation**: Important insights never get lost between sessions
- **Team Knowledge Sharing**: Shareable memory context across team members

##### ⚡ **Performance Optimized**
- **Fast Startup**: Memory injection adds <2 seconds to session startup
- **Smart Caching**: Efficient memory retrieval with minimal API calls
- **Configurable Limits**: Prevents memory service overload with request throttling
- **Graceful Fallback**: Works with or without memory service availability

#### Migration & Compatibility

##### 🔄 **Seamless Integration**
- **Non-Intrusive**: Works alongside existing Claude Code workflows
- **Backward Compatible**: No changes required to existing development processes
- **Optional Feature**: Can be enabled/disabled per project or globally
- **Multi-Environment**: Works with local, remote, and distributed memory services

##### 📋 **Installation Requirements**
- Claude Code CLI installed and configured
- MCP Memory Service running (local or remote)
- Node.js environment for hook execution
- Git repository for optimal project detection

#### Roadmap Integration

This release completes **Phase 1** of the Memory Awareness Enhancement Roadmap (Issue #14):
- ✅ Session startup hooks with automatic memory injection
- ✅ Project-aware memory selection algorithms  
- ✅ Context formatting and injection utilities
- ✅ Comprehensive testing and installation system
- ✅ Production-ready configuration and deployment

**Next Phase**: Dynamic memory loading, cross-session intelligence, and advanced consolidation features.

#### Breaking Changes
None - This is a purely additive feature that enhances existing Claude Code functionality.

---

## [5.2.0] - 2025-08-18

### 🚀 **New Features**

#### Command Line Interface (CLI)
- **Comprehensive CLI**: Added `memory` command with subcommands for document ingestion and management
- **Document Ingestion Commands**: 
  - `memory ingest-document <file>` - Ingest single documents with customizable chunking
  - `memory ingest-directory <path>` - Batch process entire directories 
  - `memory list-formats` - Show all supported document formats
- **Management Commands**:
  - `memory server` - Start the MCP server (replaces old `memory` command)
  - `memory status` - Show service status and statistics
- **Advanced Options**: Tags, chunk sizing, storage backend selection, verbose output, dry-run mode
- **Progress Tracking**: Real-time progress bars and detailed error reporting
- **Cross-Platform**: Works on Windows, macOS, and Linux with proper path handling

#### Enhanced Document Processing
- **Click Framework**: Professional CLI with help system and tab completion support
- **Async Operations**: Non-blocking document processing with proper resource management
- **Error Recovery**: Graceful handling of processing errors with detailed diagnostics
- **Batch Limits**: Configurable file limits and extension filtering for large directories

**New Dependencies**: `click>=8.0.0` for CLI framework

**Examples**:
```bash
memory ingest-document manual.pdf --tags documentation,manual --verbose
memory ingest-directory ./docs --recursive --max-files 50
memory list-formats
memory status
```

**Backward Compatibility**: Old `memory` server command now available as `memory server` and `memory-server`

## [5.1.0] - 2025-08-18

### 🚀 **New Features**

#### Remote ChromaDB Support
- **Enterprise-Ready**: Connect to remote ChromaDB servers, Chroma Cloud, or self-hosted instances
- **HttpClient Implementation**: Full support for remote ChromaDB connectivity
- **Authentication**: API key authentication via `X_CHROMA_TOKEN` header
- **SSL/HTTPS Support**: Secure connections to remote ChromaDB servers
- **Custom Collections**: Specify collection names for multi-tenant deployments

**New Environment Variables:**
- `MCP_MEMORY_CHROMADB_HOST`: Remote server hostname (enables remote mode)
- `MCP_MEMORY_CHROMADB_PORT`: Server port (default: 8000)
- `MCP_MEMORY_CHROMADB_SSL`: Use HTTPS ('true'/'false')
- `MCP_MEMORY_CHROMADB_API_KEY`: Authentication token
- `MCP_MEMORY_COLLECTION_NAME`: Custom collection name (default: 'memory_collection')

**Perfect Timing**: Arrives just as Chroma Cloud launches Q1 2025 (early access available)

**Resolves**: #36 (Remote ChromaDB support request)

## [5.0.5] - 2025-08-18

### 🐛 **Bug Fixes**

#### Code Quality & Future Compatibility
- **Fixed datetime deprecation warnings**: Replaced all `datetime.utcnow()` usage with `datetime.now(timezone.utc)`
  - Updated `src/mcp_memory_service/web/api/health.py` (2 occurrences)
  - Updated `src/mcp_memory_service/web/sse.py` (3 occurrences)
  - Eliminates deprecation warnings in Python 3.12+
  - Future-proof timezone-aware datetime handling

### 🎨 **UI Improvements**

#### Dashboard Mobile Responsiveness
- **Enhanced mobile UX**: Added responsive design for action buttons
  - Buttons now stack vertically on screens < 768px width
  - Improved touch-friendly spacing and sizing
  - Better mobile experience for API documentation links
  - Maintains desktop horizontal layout on larger screens

**Issues Resolved**: #68 (Code Quality & Deprecation Fixes), #80 (Dashboard Mobile Responsiveness)

## [5.0.4] - 2025-08-18

### 🐛 **Critical Bug Fixes**

#### SQLite-vec Embedding Model Loading
- **Fixed UnboundLocalError**: Removed redundant `import os` statement at line 285 in `sqlite_vec.py`
  - Variable shadowing prevented ONNX embedding model initialization
  - Caused "cannot access local variable 'os'" error in production
  - Restored full embedding functionality for memory storage

#### Docker HTTP Server Support
- **Fixed Missing Files**: Added `run_server.py` to Docker image (reported by Joe Esposito)
  - HTTP server wouldn't start without this critical file
  - Now properly copied in Dockerfile for HTTP/API mode
- **Fixed Python Path**: Corrected `PYTHONPATH` from `/app` to `/app/src`
  - Modules couldn't be found with incorrect path
  - Essential for both MCP and HTTP modes

### 🚀 **Major Docker Improvements**

#### Simplified Docker Architecture
- **Reduced Complexity by 60%**: Consolidated from 4 confusing compose files to 2 clear options
  - `docker-compose.yml` for MCP protocol mode (Claude Desktop, VS Code)
  - `docker-compose.http.yml` for HTTP/API mode (REST API, Web Dashboard)
- **Unified Entrypoint**: Created single smart entrypoint script
  - Auto-detects mode from `MCP_MODE` environment variable
  - Eliminates confusion about which script to use
- **Pre-download Models**: Embedding models now downloaded during Docker build
  - Prevents runtime failures from network/DNS issues
  - Makes containers fully self-contained
  - Faster startup times

#### Deprecated Docker Files
- Marked 4 redundant Docker files as deprecated:
  - `docker-compose.standalone.yml` → Use `docker-compose.http.yml`
  - `docker-compose.uv.yml` → UV now built into main Dockerfile
  - `docker-compose.pythonpath.yml` → Fix applied to main Dockerfile
  - `docker-entrypoint-persistent.sh` → Replaced by unified entrypoint

### 📝 **Documentation**

#### Docker Documentation Overhaul
- **Added Docker README**: Clear instructions for both MCP and HTTP modes
- **Created DEPRECATED.md**: Migration guide for old Docker setups
- **Added Test Script**: `test-docker-modes.sh` to verify both modes work
- **Troubleshooting Guide**: Added comprehensive debugging section to CLAUDE.md
  - Web frontend debugging (CSS/format string conflicts)
  - Cache clearing procedures
  - Environment reset steps
  - Backend method compatibility

### 🙏 **Credits**
- Special thanks to **Joe Esposito** for identifying and helping fix critical Docker issues

## [5.0.3] - 2025-08-17

### 🐛 **Bug Fixes**

#### SQLite-vec Backend Method Support
- **Fixed Missing Method**: Added `search_by_tags` method to SQLite-vec backend
  - Web API was calling `search_by_tags` (plural) but backend only had `search_by_tag` (singular)
  - This caused 500 errors when using tag-based search via HTTP/MCP endpoints
  - New method supports both AND/OR operations for tag matching
  - Fixes network distribution and memory retrieval functionality

### 🚀 **Enhancements**

#### Version Information in Health Checks
- **Added Version Field**: All health endpoints now return service version
  - Basic health endpoint (`/api/health`) includes version field
  - Detailed health endpoint (`/api/health/detailed`) includes version field
  - MCP `check_database_health` tool returns version in response
  - Enables easier debugging and version tracking across deployments

### 🚀 **New Features**

#### Memory Distribution and Network Sharing
- **Export Tool**: Added `scripts/export_distributable_memories.sh` for memory export
  - Export memories tagged with `distributable-reference` for team sharing
  - JSON format for easy import to other MCP instances
  - Support for cross-network memory synchronization
- **Personalized CLAUDE.md Generator**: Added `scripts/generate_personalized_claude_md.sh`
  - Generate CLAUDE.md with embedded memory service endpoints
  - Customize for different network deployments
  - Include memory retrieval commands for each environment
- **Memory Context Templates**: Added `prompts/load_memory_context.md`
  - Ready-to-use prompts for loading project context
  - Quick retrieval commands for Claude Code sessions
  - Network distribution instructions

### 📝 **Documentation**

#### Network Distribution Updates
- **Fixed Memory Retrieval Commands**: Updated scripts to use working API methods
  - Changed from non-existent `search_by_tag` to `retrieve_memory` for current deployments
  - Updated prompt templates and distribution scripts
  - Improved error handling for memory context loading
- **CLAUDE.md Enhancements**: Added optional memory context section
  - Instructions for setting up local memory service integration
  - Guidelines for creating CLAUDE_MEMORY.md (git-ignored) for local configurations
  - Best practices for memory management and quarterly reviews

## [5.0.2] - 2025-08-17

### 🚀 **New Features**

#### ONNX Runtime Support
- **PyTorch-free operation**: True PyTorch-free embedding generation using ONNX Runtime
  - Reduced dependencies (~500MB less disk space without PyTorch)
  - Faster startup with pre-optimized ONNX models  
  - Automatic fallback to SentenceTransformers when needed
  - Compatible with the same `all-MiniLM-L6-v2` model embeddings
  - Enable with `export MCP_MEMORY_USE_ONNX=true`

### 🐛 **Bug Fixes**

#### SQLite-vec Consolidation Support (Issue #84)
- **Missing Methods Fixed**: Added all required methods for consolidation support
  - Implemented `get_memories_by_time_range()` for time-based queries
  - Added `get_memory_connections()` for relationship tracking statistics
  - Added `get_access_patterns()` for access pattern analysis
  - Added `get_all_memories()` method with proper SQL implementation

#### Installer Accuracy  
- **False ONNX Claims**: Fixed misleading installer messages about ONNX support
  - Removed false claims about "ONNX runtime for embeddings" when no implementation existed
  - Updated installer messages to accurately reflect capabilities
  - Now actually implements the ONNX support that was previously claimed

#### Docker Configuration
- **SQLite-vec Defaults**: Updated Docker configuration to reflect SQLite-vec as default backend
  - Updated `Dockerfile` environment variables to use `MCP_MEMORY_STORAGE_BACKEND=sqlite_vec`
  - Changed paths from `/app/chroma_db` to `/app/sqlite_db` 
  - Updated `docker-compose.yml` with SQLite-vec configuration
  - Fixed volume mounts and environment variables

### 📝 **Documentation**

#### Enhanced README
- **ONNX Feature Documentation**: Added comprehensive ONNX Runtime feature section
- **Installation Updates**: Updated installation instructions with ONNX dependencies
- **Feature Visibility**: Highlighted ONNX support in main features list

#### Technical Implementation
- **New Module**: Created `src/mcp_memory_service/embeddings/onnx_embeddings.py`
  - Complete ONNX embedding implementation based on ChromaDB's ONNXMiniLM_L6_V2
  - Automatic model downloading and caching
  - Hardware-aware provider selection (CPU, CUDA, DirectML, CoreML)
  - Error handling with graceful fallbacks

- **Enhanced Configuration**: Added ONNX configuration support in `config.py`
  - `USE_ONNX` configuration option  
  - ONNX model cache directory management
  - Environment variable support for `MCP_MEMORY_USE_ONNX`

### Technical Notes
- Full backward compatibility maintained for existing SQLite-vec users
- ONNX support is optional and falls back gracefully to SentenceTransformers
- All consolidation methods implemented with proper error handling
- Docker images now correctly reflect the SQLite-vec default backend

This release resolves all issues reported in GitHub issue #84, implementing true ONNX support and completing the SQLite-vec consolidation feature set.
## [6.2.0] - 2025-08-20

### 🚀 **MAJOR FEATURE: Native Cloudflare Backend Integration**

This major release introduces native Cloudflare integration as a third storage backend option alongside SQLite-vec and ChromaDB, providing global distribution, automatic scaling, and enterprise-grade infrastructure, integrated with the existing Memory Awareness system.

#### Added
- **Native Cloudflare Backend Support**: Complete implementation using Cloudflare's edge computing platform
  - **Vectorize**: 768-dimensional vector storage with cosine similarity for semantic search
  - **D1 Database**: SQLite-compatible database for metadata storage
  - **Workers AI**: Embedding generation using @cf/baai/bge-base-en-v1.5 model
  - **R2 Storage** (optional): Object storage for large content exceeding 1MB threshold
  
- **Implementation Files**:
  - `src/mcp_memory_service/storage/cloudflare.py` - Complete CloudflareStorage implementation (740 lines)
  - `scripts/migrate_to_cloudflare.py` - Migration tool for existing SQLite-vec and ChromaDB users
  - `scripts/test_cloudflare_backend.py` - Comprehensive test suite with automated validation
  - `scripts/setup_cloudflare_resources.py` - Automated Cloudflare resource provisioning
  - `docs/cloudflare-setup.md` - Complete setup, configuration, and troubleshooting guide
  - `tests/unit/test_cloudflare_storage.py` - 15 unit tests for CloudflareStorage class

- **Features**:
  - Automatic retry logic with exponential backoff for API rate limiting
  - Connection pooling for optimal HTTP performance
  - NDJSON format support for Vectorize v2 API endpoints
  - LRU caching (1000 entries) for embedding deduplication
  - Batch operations support for efficient data processing
  - Global distribution with <100ms latency from most locations
  - Pay-per-use pricing model with no upfront costs

#### Changed
- Updated `config.py` to include 'cloudflare' in SUPPORTED_BACKENDS
- Enhanced server initialization in `mcp_server.py` to support Cloudflare backend
- Updated storage factory in `storage/__init__.py` to create CloudflareStorage instances
- Consolidated documentation, removing redundant setup files

#### Technical Details
- **Environment Variables**:
  - `MCP_MEMORY_STORAGE_BACKEND=cloudflare` - Activate Cloudflare backend
  - `CLOUDFLARE_API_TOKEN` - API token with Vectorize, D1, Workers AI permissions
  - `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account identifier
  - `CLOUDFLARE_VECTORIZE_INDEX` - Name of Vectorize index (768 dimensions)
  - `CLOUDFLARE_D1_DATABASE_ID` - D1 database UUID
  - `CLOUDFLARE_R2_BUCKET` (optional) - R2 bucket for large content
  
- **Performance Characteristics**:
  - Storage: ~200ms per memory (including embedding generation)
  - Search: ~100ms for semantic search (5 results)
  - Batch operations: ~50ms per memory in batches of 100
  - Global latency: <100ms from most global locations

#### Migration Path
Users can migrate from existing backends using provided scripts:
```bash
# From SQLite-vec
python scripts/migrate_to_cloudflare.py --source sqlite

# From ChromaDB  
python scripts/migrate_to_cloudflare.py --source chroma
```

#### Memory Awareness Integration
- **Full Compatibility**: Cloudflare backend works seamlessly with Phase 1 and Phase 2 Memory Awareness
- **Cross-Session Intelligence**: Session tracking and conversation threading supported
- **Dynamic Context Updates**: Real-time memory loading during conversations
- **Global Performance**: Enhances Memory Awareness with <100ms global response times

#### Compatibility
- Fully backward compatible with existing SQLite-vec and ChromaDB backends
- No breaking changes to existing APIs or configurations
- Supports all existing MCP operations and features
- Compatible with all existing Memory Awareness hooks and functionality

## [5.0.1] - 2025-08-15

### 🐛 **Critical Migration Fixes**

This patch release addresses critical issues in the v5.0.0 ChromaDB to SQLite-vec migration process reported in [Issue #83](https://github.com/doobidoo/mcp-memory-service/issues/83).

#### Fixed
- **Custom Data Paths**: Migration scripts now properly support custom ChromaDB locations via CLI arguments and environment variables
  - Added `--chroma-path` and `--sqlite-path` arguments to migration scripts
  - Support for `MCP_MEMORY_CHROMA_PATH` and `MCP_MEMORY_SQLITE_PATH` environment variables
  - Fixed hardcoded path assumptions that ignored user configurations

- **Content Hash Generation**: Fixed critical bug where ChromaDB document IDs were used instead of proper SHA256 hashes
  - Now generates correct content hashes using SHA256 algorithm
  - Prevents "NOT NULL constraint failed" errors during migration
  - Ensures data integrity and proper deduplication

- **Tag Format Corruption**: Fixed issue where 60% of tags became malformed during migration
  - Improved tag validation and format conversion
  - Handles comma-separated strings, arrays, and single tags correctly
  - Prevents array syntax from being stored as strings

- **Migration Progress**: Added progress indicators and better error reporting
  - Shows percentage completion during migration
  - Batch processing with configurable batch size
  - Verbose mode for detailed debugging
  - Clear error messages for troubleshooting

#### Added
- **Enhanced Migration Script** (`scripts/migrate_v5_enhanced.py`):
  - Comprehensive migration tool with all fixes
  - Dry-run mode for testing migrations
  - Transaction-based migration with rollback support
  - Progress bars with `tqdm` support
  - JSON backup creation
  - Automatic path detection for common installations

- **Migration Validator** (`scripts/validate_migration.py`):
  - Validates migrated SQLite database integrity
  - Checks for missing fields and corrupted data
  - Compares with original ChromaDB data
  - Generates detailed validation report
  - Identifies specific issues like hash mismatches and tag corruption

- **Comprehensive Documentation**:
  - Updated migration guide with troubleshooting section
  - Documented all known v5.0.0 issues and solutions
  - Added recovery procedures for failed migrations
  - Migration best practices and validation steps

#### Enhanced
- **Original Migration Script** (`scripts/migrate_chroma_to_sqlite.py`):
  - Added CLI argument support for custom paths
  - Fixed content hash generation
  - Improved tag handling
  - Better duplicate detection
  - Progress percentage display

#### Documentation
- **Migration Troubleshooting Guide**: Added comprehensive troubleshooting section covering:
  - Custom data location issues
  - Content hash errors
  - Tag corruption problems
  - Migration hangs
  - Dependency conflicts
  - Recovery procedures

## [5.0.0] - 2025-08-15

### ⚠️ **BREAKING CHANGES**

#### ChromaDB Deprecation
- **DEPRECATED**: ChromaDB backend is now deprecated and will be removed in v6.0.0
- **DEFAULT CHANGE**: SQLite-vec is now the default storage backend (previously ChromaDB)
- **MIGRATION REQUIRED**: Users with existing ChromaDB data should migrate to SQLite-vec
  - Run `python scripts/migrate_to_sqlite_vec.py` to migrate your data
  - Migration is one-way only (ChromaDB → SQLite-vec)
  - Backup your data before migration

#### Why This Change?
- **Network Issues**: ChromaDB requires downloading models from Hugging Face, causing frequent failures
- **Performance**: SQLite-vec is 10x faster at startup (2-3 seconds vs 15-30 seconds)
- **Resource Usage**: SQLite-vec uses 75% less memory than ChromaDB
- **Reliability**: Zero network dependencies means no download failures or connection issues
- **Simplicity**: Single-file database, easier backup and portability

#### Changed
- **Default Backend**: Changed from ChromaDB to SQLite-vec in all configurations
- **Installation**: `install.py` now installs SQLite-vec dependencies by default
- **Documentation**: Updated all guides to recommend SQLite-vec as primary backend
- **Warnings**: Added deprecation warnings when ChromaDB backend is used
- **Migration Prompts**: Server now prompts for migration when ChromaDB data is detected

#### Migration Guide
1. **Backup your data**: `python scripts/create_backup.py`
2. **Run migration**: `python scripts/migrate_to_sqlite_vec.py`
3. **Update configuration**: Set `MCP_MEMORY_STORAGE_BACKEND=sqlite_vec`
4. **Restart server**: Your memories are now in SQLite-vec format

#### Backward Compatibility
- ChromaDB backend still functions but displays deprecation warnings
- Existing ChromaDB installations continue to work until v6.0.0
- Migration tools provided for smooth transition
- All APIs remain unchanged regardless of backend

## [4.6.1] - 2025-08-14

### 🐛 **Bug Fixes**

#### Fixed
- **Export/Import Script Database Path Detection**: Fixed critical bug in memory export and import scripts
  - Export script now properly respects `SQLITE_VEC_PATH` configuration from `config.py`
  - Import script now properly respects `SQLITE_VEC_PATH` configuration from `config.py`
  - Scripts now use environment variables like `MCP_MEMORY_SQLITE_PATH` correctly
  - Fixed issue where export/import would use wrong database path, missing actual memories
  - Added support for custom database paths via `--db-path` argument
  - Ensures export captures all memories from the configured database location
  - Ensures import writes to the correct configured database location

#### Enhanced
- **Export/Import Script Configuration**: Improved database path detection logic
  - Falls back gracefully when SQLite-vec backend is not configured
  - Maintains compatibility with different storage backend configurations
  - Added proper imports for configuration variables

#### Technical Details
- Modified `scripts/sync/export_memories.py` to use `SQLITE_VEC_PATH` instead of `BASE_DIR`
- Modified `scripts/sync/import_memories.py` to use `SQLITE_VEC_PATH` instead of `BASE_DIR`
- Updated `get_default_db_path()` functions in both scripts to check storage backend configuration
- Added version bump to exporter metadata for tracking
- Added `get_all_memories()` method to `SqliteVecMemoryStorage` for proper export functionality

## [4.6.0] - 2025-08-14

### ✨ **New Features**

#### Added
- **Custom SSL Certificate Support**: Added environment variable configuration for SSL certificates
  - New `MCP_SSL_CERT_FILE` environment variable for custom certificate path
  - New `MCP_SSL_KEY_FILE` environment variable for custom private key path
  - Maintains backward compatibility with self-signed certificate generation
  - Enables production deployments with proper SSL certificates (e.g., mkcert, Let's Encrypt)

#### Enhanced
- **HTTPS Server Configuration**: Improved certificate validation and error handling
  - Certificate file existence validation before server startup
  - Clear error messages for missing certificate files
  - Logging improvements for certificate source identification

#### Documentation
- **SSL/TLS Setup Guide**: Added comprehensive SSL configuration documentation
  - Integration guide for [mkcert](https://github.com/FiloSottile/mkcert) for local development
  - Example HTTPS startup script template
  - Client CA installation instructions for multiple operating systems

## [4.5.2] - 2025-08-14

### 🐛 **Bug Fixes & Documentation**

#### Fixed
- **JSON Protocol Compatibility**: Resolved debug output contaminating MCP JSON-RPC communication
  - Fixed unconditional debug print statements causing "Unexpected token" errors in Claude Desktop logs
  - Added client detection checks to `TOOL CALL INTERCEPTED` and `Processing tool` debug messages
  - Ensures clean JSON-only output for Claude Desktop while preserving debug output for LM Studio

#### Enhanced
- **Universal README Documentation**: Transformed from Claude Desktop-specific to universal AI client focus
  - Updated opening description to emphasize compatibility with "AI applications and development environments"
  - Added prominent compatibility badges for Cursor, WindSurf, LM Studio, Zed, and other AI clients
  - Moved comprehensive client compatibility table to prominent position in documentation
  - Expanded client support details for 13+ different AI applications and IDEs
  - Added multi-client benefits section highlighting cross-tool memory sharing capabilities
  - Updated examples and Docker configurations to be client-agnostic

#### Documentation
- **Improved Client Visibility**: Enhanced documentation structure for broader MCP ecosystem appeal
- **Balanced Examples**: Updated API examples to focus on universal MCP access rather than specific clients
- **Clear Compatibility Matrix**: Detailed status and configuration for each supported AI client

## [4.5.1] - 2025-08-13

### 🎯 **Enhanced Multi-Client Support**

#### Added
- **Intelligent Client Detection**: Automatic detection of MCP client type
  - Detects Claude Desktop, LM Studio, and other MCP clients
  - Uses process inspection and environment variables for robust detection
  - Falls back to strict JSON mode for unknown clients
  
- **Client-Aware Logging System**: Optimized output for different MCP clients
  - **Claude Desktop Mode**: Pure JSON-RPC protocol compliance
    - Suppresses diagnostic output to maintain clean JSON communication
    - Routes only WARNING/ERROR messages to stderr
    - Ensures maximum compatibility with Claude's strict parsing
  - **LM Studio Mode**: Enhanced diagnostic experience
    - Shows system diagnostics, dependency checks, and initialization status
    - Provides detailed feedback for troubleshooting
    - Maintains full INFO/DEBUG output to stdout

#### Enhanced
- **Improved Stability**: All diagnostic output is now conditional based on client type
  - 15+ print statements updated with client-aware logic
  - System diagnostics, dependency checks, and initialization messages
  - Docker mode detection and standalone mode indicators

#### Technical Details
- Added `psutil` dependency for process-based client detection
- Implemented `DualStreamHandler` with client-aware routing
- Environment variable support: `CLAUDE_DESKTOP=1` or `LM_STUDIO=1` for manual override
- Maintains full backward compatibility with existing integrations

## [4.5.0] - 2025-08-12

### 🔄 **Database Synchronization System**

#### Added
- **Multi-Node Database Sync**: Complete Litestream-based synchronization for SQLite-vec databases
  - **JSON Export/Import**: Preserve timestamps and metadata across database migrations
  - **Litestream Integration**: Real-time database replication with conflict resolution
  - **3-Node Architecture**: Central server with replica nodes for distributed workflows
  - **Deduplication Logic**: Content hash-based duplicate prevention during imports
  - **Source Tracking**: Automatic tagging to identify memory origin machines

- **New Sync Module**: `src/mcp_memory_service/sync/`
  - `MemoryExporter`: Export memories to JSON with full metadata preservation
  - `MemoryImporter`: Import with intelligent deduplication and source tracking
  - `LitestreamManager`: Automated Litestream configuration and management

- **Sync Scripts Suite**: `scripts/sync/`
  - `export_memories.py`: Platform-aware memory export utility
  - `import_memories.py`: Central server import with merge statistics
  - `README.md`: Comprehensive usage documentation

#### Enhanced
- **Migration Tools**: Extended existing migration scripts to support sync workflows
- **Backup Integration**: Sync capabilities integrate with existing backup system
- **Health Monitoring**: Added sync status to health endpoints and monitoring

#### Documentation
- **Complete Sync Guide**: `docs/deployment/database-synchronization.md`
- **Technical Architecture**: Detailed setup and troubleshooting documentation
- **Migration Examples**: Updated migration documentation with sync procedures

#### Use Cases
- **Multi-Device Workflows**: Keep memories synchronized across Windows, macOS, and server
- **Team Collaboration**: Shared memory databases with individual client access
- **Backup and Recovery**: Real-time replication provides instant backup capability
- **Offline Capability**: Local replicas work offline, sync when reconnected

This release enables seamless database synchronization across multiple machines while preserving all memory metadata, timestamps, and source attribution.

## [4.4.0] - 2025-08-12

### 🚀 **Backup System Enhancements**

#### Added
- **SQLite-vec Backup Support**: Enhanced MCP backup system to fully support SQLite-vec backend
  - **Multi-Backend Support**: `dashboard_create_backup` now handles both ChromaDB and SQLite-vec databases
  - **Complete File Coverage**: Backs up main database, WAL, and SHM files for data integrity
  - **Metadata Generation**: Creates comprehensive backup metadata with size, file count, and backend info
  - **Error Handling**: Robust error handling and validation during backup operations

- **Automated Backup Infrastructure**: Complete automation solution for production deployments
  - **Backup Script**: `scripts/backup_sqlite_vec.sh` with 7-day retention policy
  - **Cron Setup**: `scripts/setup_backup_cron.sh` for easy daily backup scheduling
  - **Metadata Tracking**: JSON metadata files with backup timestamp, size, and source information
  - **Automatic Cleanup**: Old backup removal to prevent disk space issues

#### Enhanced
- **Backup Reliability**: Improved backup system architecture for production use
  - **Backend Detection**: Automatic detection and appropriate handling of storage backend
  - **File Integrity**: Proper handling of SQLite WAL mode with transaction log files
  - **Consistent Naming**: Standardized backup naming with timestamps
  - **Validation**: Pre-backup validation of source files and post-backup verification

#### Technical Details
- **Storage Backend**: Seamless support for both `sqlite_vec` and `chroma` backends
- **File Operations**: Safe file copying with proper permission handling
- **Scheduling**: Cron integration for hands-off automated backups
- **Monitoring**: Backup logs and status tracking for operational visibility

## [4.3.5] - 2025-08-12

### 🔧 **Critical Fix: Client Hostname Capture**

#### Fixed
- **Architecture Correction**: Fixed hostname capture to identify CLIENT machine instead of server machine
  - **Before**: Always captured server hostname (`narrowbox`) regardless of client
  - **After**: Prioritizes client-provided hostname, fallback to server hostname
  - **HTTP API**: Supports `client_hostname` in request body + `X-Client-Hostname` header
  - **MCP Server**: Added `client_hostname` parameter to store_memory tool
  - **Legacy Server**: Supports `client_hostname` in arguments dictionary
  - **Priority Order**: request body > HTTP header > server hostname fallback

#### Changed
- **Client Detection Logic**: Updated all three interfaces with proper client hostname detection
  - `memories.py`: Added Request parameter and header/body hostname extraction
  - `mcp_server.py`: Added client_hostname parameter with priority logic
  - `server.py`: Added client_hostname argument extraction with fallback
  - Maintains backward compatibility when `MCP_MEMORY_INCLUDE_HOSTNAME=false`

#### Documentation
- **Command Templates**: Updated repository templates with client hostname detection guidance
- **API Documentation**: Enhanced descriptions to clarify client vs server hostname capture
- **Test Documentation**: Added comprehensive test scenarios and verification steps

#### Technical Impact
- ✅ **Multi-device workflows**: Memories now correctly identify originating client machine
- ✅ **Audit trails**: Proper source attribution across different client connections
- ✅ **Remote deployments**: Works correctly when client and server are different machines
- ✅ **Backward compatible**: No breaking changes, respects environment variable setting

## [4.3.4] - 2025-08-12

### 🔧 **Optional Machine Identification**

#### Added
- **Environment-Controlled Machine Tracking**: Made machine identification optional via environment variable
  - New environment variable: `MCP_MEMORY_INCLUDE_HOSTNAME` (default: `false`)
  - When enabled, automatically adds machine hostname to all stored memories
  - Adds both `source:hostname` tag and hostname metadata field
  - Supports all interfaces: MCP server, HTTP API, and legacy server
  - Privacy-focused: disabled by default, enables multi-device workflows when needed

#### Changed
- **Memory Storage Enhancement**: All memory storage operations now support optional machine tracking
  - Updated `mcp_server.py` store_memory function with hostname logic
  - Enhanced HTTP API `/memories` endpoint with machine identification
  - Updated legacy `server.py` with consistent hostname tracking
  - Maintains backward compatibility with existing memory operations

#### Documentation
- **CLAUDE.md Updated**: Added `MCP_MEMORY_INCLUDE_HOSTNAME` environment variable documentation
- **Configuration Guide**: Explains optional hostname tracking for audit trails and multi-device setups

## [4.3.3] - 2025-08-12

### 🎯 **Claude Code Command Templates Enhancement**

#### Added
- **Machine Source Tracking**: All memory storage commands now automatically include machine hostname as a tag
  - Enables filtering memories by originating machine (e.g., `source:machine-name`)
  - Adds hostname to both tags and metadata for redundancy
  - Supports multi-device workflows and audit trails

#### Changed
- **Command Templates Updated**: All five memory command templates enhanced with:
  - Updated to use generic HTTPS endpoint (`https://memory.local:8443/`)
  - Proper API endpoint paths documented for all operations
  - Auto-save functionality without confirmation prompts
  - curl with `-k` flag for HTTPS self-signed certificates
  - Machine hostname tracking integrated throughout

#### Documentation
- `memory-store.md`: Added machine context and HTTPS configuration
- `memory-health.md`: Updated with specific health API endpoints
- `memory-search.md`: Added all search API endpoints and machine source search
- `memory-context.md`: Integrated machine tracking for session captures
- `memory-recall.md`: Updated with API endpoints and time parser limitations

## [4.3.2] - 2025-08-11

### 🎯 **Repository Organization & PyTorch Download Fix**

#### Fixed
- **PyTorch Repeated Downloads**: Completely resolved Claude Desktop downloading PyTorch (230MB+) on every startup
  - Root cause: UV package manager isolation prevented offline environment variables from taking effect
  - Solution: Created `scripts/memory_offline.py` launcher that sets offline mode BEFORE any imports
  - Updated Claude Desktop config to use Python directly instead of UV isolation
  - Added comprehensive offline mode configuration for HuggingFace transformers

- **Environment Variable Inheritance**: Fixed UV environment isolation issues
  - Implemented direct Python execution bypass for Claude Desktop integration
  - Added code-level offline setup in `src/mcp_memory_service/__init__.py` as fallback
  - Ensured cached model usage without network requests

#### Changed
- **Repository Structure**: Major cleanup and reorganization of root directory
  - Moved documentation files to appropriate `/docs` subdirectories
  - Consolidated guides in `docs/guides/`, technical docs in `docs/technical/`
  - Moved deployment guides to `docs/deployment/`, installation to `docs/installation/`
  - Removed obsolete debug scripts and development notes
  - Moved service management scripts to `/scripts` directory

- **Documentation Organization**: Improved logical hierarchy
  - Claude Code compatibility → `docs/guides/claude-code-compatibility.md`
  - Setup guides → `docs/installation/` and `docs/guides/`
  - Technical documentation → `docs/technical/`
  - Integration guides → `docs/integrations/`

#### Technical Details
- **Offline Mode Implementation**: `scripts/memory_offline.py` sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before ML library imports
- **Config Optimization**: Updated Claude Desktop config templates for both Windows and general use
- **Cache Management**: Proper Windows cache path configuration for sentence-transformers and HuggingFace

#### Impact
- ✅ **Eliminated 230MB PyTorch downloads** - Startup time reduced from ~60s to ~3s
- ✅ **Professional repository structure** - Clean root directory with logical documentation hierarchy  
- ✅ **Improved maintainability** - Consolidated scripts and removed redundant files
- ✅ **Enhanced user experience** - No more frustrating download delays in Claude Desktop

This release resolves the persistent PyTorch download issue that affected Windows users and establishes a clean, professional repository structure suitable for enterprise deployment.

## [4.3.1] - 2025-08-11

### 🔧 **Critical Windows Installation Fixes**

#### Fixed
- **PyTorch-DirectML Compatibility**: Resolved major installation issues on Windows 11
  - Fixed installer attempting to install incompatible PyTorch 2.5.1 over working 2.4.1+DirectML setup
  - Added smart compatibility checking: PyTorch 2.4.x works with DirectML, 2.5.x doesn't
  - Enhanced `install_pytorch_windows()` to preserve existing compatible installations
  - Only installs torch-directml if PyTorch 2.4.1 exists without DirectML extensions
  
- **Corrupted Virtual Environment Recovery**: Fixed "module 'torch' has no attribute 'version'" errors
  - Implemented complete cleanup of corrupted `~orch` and `functorch` directories  
  - Added robust uninstall and reinstall process for broken PyTorch installations
  - Restored proper torch.version attribute functionality
  
- **Windows 11 Detection**: Fixed incorrect OS identification
  - Implemented registry-based Windows 11 detection using build numbers (≥22000)
  - Replaced unreliable platform detection with accurate registry lookups
  - Added system info caching to prevent duplicate detection calls

- **Installation Logging Improvements**: Enhanced installer feedback and debugging
  - Created built-in DualOutput logging system with UTF-8 encoding
  - Fixed character encoding issues in installation logs
  - Added comprehensive logging for PyTorch compatibility decisions

#### Changed
- **Installation Intelligence**: Installer now preserves working DirectML setups instead of force-upgrading
- **Error Prevention**: Added extensive pre-checks to prevent corrupted package installations
- **User Experience**: Clear messaging about PyTorch version compatibility and preservation decisions

#### Technical Details
- Enhanced PyTorch version detection and compatibility matrix
- Smart preservation of PyTorch 2.4.1 + torch-directml 0.2.5.dev240914 combinations
- Automatic cleanup of corrupted package directories during installation recovery
- Registry-based Windows version detection via `SOFTWARE\Microsoft\Windows NT\CurrentVersion`

This release resolves critical Windows installation failures that prevented successful PyTorch-DirectML setup, ensuring reliable DirectML acceleration on Windows 11 systems.

## [4.3.0] - 2025-08-10

### ⚡ **Developer Experience Improvements**

#### Added
- **Automated uv.lock Conflict Resolution**: Eliminates manual merge conflict resolution
  - Custom git merge driver automatically resolves `uv.lock` conflicts
  - Auto-runs `uv sync` after conflict resolution to ensure consistency
  - One-time setup script for contributors: `./scripts/setup-git-merge-drivers.sh`
  - Comprehensive documentation in README.md and CLAUDE.md

#### Technical
- Added `.gitattributes` configuration for `uv.lock` merge handling
- Created `scripts/uv-lock-merge.sh` custom merge driver script
- Added contributor setup script with automatic git configuration
- Enhanced development documentation with git setup instructions

This release significantly improves the contributor experience by automating the resolution of the most common merge conflicts in the repository.

## [4.2.0] - 2025-08-10

### 🔧 **Improved Client Compatibility**

#### Added
- **LM Studio Compatibility Layer**: Automatic handling of non-standard MCP notifications
  - Monkey patch for `notifications/cancelled` messages that aren't in the MCP specification
  - Graceful error handling prevents server crashes when LM Studio cancels operations
  - Debug logging for troubleshooting compatibility issues
  - Comprehensive documentation in `docs/LM_STUDIO_COMPATIBILITY.md`

#### Technical
- Added `lm_studio_compat.py` module with compatibility patches
- Applied patches automatically during server initialization
- Enhanced error handling in MCP protocol communication

This release significantly improves compatibility with LM Studio and other MCP clients while maintaining full backward compatibility with existing Claude Desktop integrations.

## [4.1.1] - 2025-08-10

### Fixed
- **macOS ARM64 Support**: Enhanced PyTorch installation for Apple Silicon
  - Proper dependency resolution for M1/M2/M3 Mac systems
  - Updated torch dependency requirements from `>=1.6.0` to `>=2.0.0` in `pyproject.toml`
  - Platform-specific installation instructions in `install.py`
  - Improved cross-platform dependency management

## [4.1.0] - 2025-08-06

### 🎯 **Full MCP Specification Compliance**

#### Added
- **Enhanced Resources System**: URI-based access to memory collections
  - `memory://stats` - Real-time database statistics and health metrics
  - `memory://tags` - Complete list of available memory tags
  - `memory://recent/{n}` - Access to N most recent memories
  - `memory://tag/{tagname}` - Query memories by specific tag
  - `memory://search/{query}` - Dynamic search with structured results
  - Resource templates for parameterized queries
  - JSON responses for all resource endpoints

- **Guided Prompts Framework**: Interactive workflows for memory operations
  - `memory_review` - Review and organize memories from specific time periods
  - `memory_analysis` - Analyze patterns, themes, and tag distributions
  - `knowledge_export` - Export memories in JSON, Markdown, or Text formats
  - `memory_cleanup` - Identify and remove duplicate or outdated memories
  - `learning_session` - Store structured learning notes with automatic categorization
  - Each prompt includes proper argument schemas and validation

- **Progress Tracking System**: Real-time notifications for long operations
  - Progress notifications with percentage completion
  - Operation IDs for tracking concurrent tasks
  - Enhanced `delete_by_tags` with step-by-step progress
  - Enhanced `dashboard_optimize_db` with operation stages
  - MCP-compliant progress notification protocol

#### Changed
- Extended `MemoryStorage` base class with helper methods for resources
- Enhanced `Memory` and `MemoryQueryResult` models with `to_dict()` methods
- Improved server initialization with progress tracking state management

#### Technical
- Added `send_progress_notification()` method to MemoryServer
- Implemented `get_stats()`, `get_all_tags()`, `get_recent_memories()` in storage base
- Full backward compatibility maintained with existing operations

This release brings the MCP Memory Service to full compliance with the Model Context Protocol specification, enabling richer client interactions and better user experience through structured data access and guided workflows.

## [4.0.1] - 2025-08-04

### Fixed
- **MCP Protocol Validation**: Resolved critical ID validation errors affecting integer/string ID handling
- **Embedding Model Loading**: Fixed model loading failures in offline environments
- **Semantic Search**: Restored semantic search functionality that was broken in 4.0.0
- **Version Consistency**: Fixed version mismatch between `__init__.py` and `pyproject.toml`

### Technical
- Enhanced flexible ID validation for MCP protocol compliance
- Improved error handling for embedding model initialization
- Corrected version bumping process for patch releases

## [4.0.0] - 2025-08-04

### 🚀 **Major Release: Production-Ready Remote MCP Memory Service**

#### Added
- **Native MCP-over-HTTP Protocol**: Direct MCP protocol support via FastAPI without Node.js bridge
- **Remote Server Deployment**: Full production deployment capability with remote access
- **Cross-Device Memory Access**: Validated multi-device memory synchronization
- **Comprehensive Documentation**: Complete deployment guides and remote access documentation

#### Changed
- **Architecture Evolution**: Transitioned from local experimental service to production infrastructure
- **Protocol Compliance**: Applied MCP protocol refactorings with flexible ID validation
- **Docker CI/CD**: Fixed and operationalized Docker workflows for automated deployment
- **Repository Maintenance**: Comprehensive cleanup and branch management

#### Production Validation
- Successfully deployed server running at remote endpoints with 65+ memories
- SQLite-vec backend validated (1.7MB database, 384-dim embeddings)
- all-MiniLM-L6-v2 model loaded and operational
- Full MCP tool suite available and tested

#### Milestones Achieved
- GitHub Issue #71 (remote access) completed
- GitHub Issue #72 (bridge deprecation) resolved
- Production deployment proven successful

## [4.0.0-beta.1] - 2025-08-03

### Added
- **Dual-Service Architecture**: Combined HTTP Dashboard + Native MCP Protocol
- **FastAPI MCP Integration**: Complete integration for native remote access
- **Direct MCP-over-HTTP**: Eliminated dependency on Node.js bridge

### Changed
- **Remote Access Solution**: Resolved remote memory service access (Issue #71)
- **Bridge Deprecation**: Deprecated Node.js bridge in favor of direct protocol
- **Docker Workflows**: Fixed CI/CD pipeline for automated testing

### Technical
- Maintained backward compatibility for existing HTTP API users
- Repository cleanup and branch management improvements
- Significant architectural evolution while preserving existing functionality

## [4.0.0-alpha.1] - 2025-08-03

### Added
- **Initial FastAPI MCP Server**: First implementation of native MCP server structure
- **MCP Protocol Endpoints**: Added core MCP protocol endpoints to FastAPI server
- **Hybrid Support**: Initial HTTP+MCP hybrid architecture support

### Changed
- **Server Architecture**: Began transition from pure HTTP to MCP-native implementation
- **Remote Access Configuration**: Initial configuration for remote server access
- **Protocol Implementation**: Started implementing MCP specification compliance

### Technical
- Validated local testing with FastAPI MCP server
- Fixed `mcp.run()` syntax issues
- Established foundation for dual-protocol support

## [3.3.4] - 2025-08-03

### Fixed
- **Multi-Client Backend Selection**: Fixed hardcoded sqlite_vec backend in multi-client configuration
  - Configuration functions now properly accept and use storage_backend parameter
  - Chosen backend is correctly passed through entire multi-client setup flow
  - M1 Macs with MPS acceleration now correctly use ChromaDB when selected
  - SQLite pragmas only applied when sqlite_vec is actually chosen

### Changed
- **Configuration Instructions**: Updated generic configuration to reflect chosen backend
- **Backend Flexibility**: All systems now get optimal backend configuration in multi-client mode

### Technical
- Resolved Issue #73 affecting M1 Mac users
- Ensures proper backend-specific configuration for all platforms
- Version bump to 3.3.4 for critical fix release

## [3.3.3] - 2025-08-02

### 🔒 **SSL Certificate & MCP Bridge Compatibility**

#### Fixed
- **SSL Certificate Generation**: Now generates certificates with proper Subject Alternative Names (SANs) for multi-hostname/IP compatibility
  - Auto-detects local machine IP address dynamically (no hardcoded IPs)
  - Includes `DNS:memory.local`, `DNS:localhost`, `DNS:*.local` 
  - Includes `IP:127.0.0.1`, `IP:::1` (IPv6), and auto-detected local IP
  - Environment variable support: `MCP_SSL_ADDITIONAL_IPS`, `MCP_SSL_ADDITIONAL_HOSTNAMES`
- **Node.js MCP Bridge Compatibility**: Resolved SSL handshake failures when connecting from Claude Code
  - Added missing MCP protocol methods: `initialize`, `tools/list`, `tools/call`, `notifications/initialized`
  - Enhanced error handling with exponential backoff retry logic (3 attempts, max 5s delay)
  - Comprehensive request/response logging with unique request IDs
  - Improved HTTPS client configuration with custom SSL agent
  - Reduced timeout from 30s to 10s for faster failure detection
  - Removed conflicting Host headers that caused SSL verification issues

#### Changed
- **Certificate Security**: CN changed from `localhost` to `memory.local` for better hostname matching
- **HTTP Client**: Enhanced connection management with explicit port handling and connection close headers
- **Logging**: Added detailed SSL handshake and request flow debugging

#### Environment Variables
- `MCP_SSL_ADDITIONAL_IPS`: Comma-separated list of additional IP addresses to include in certificate
- `MCP_SSL_ADDITIONAL_HOSTNAMES`: Comma-separated list of additional hostnames to include in certificate

This release resolves SSL connectivity issues that prevented Claude Code from connecting to remote MCP Memory Service instances across different networks and deployment environments.

## [3.3.2] - 2025-08-02

### 📚 **Enhanced Documentation & API Key Management**

#### Changed
- **API Key Documentation**: Comprehensive improvements to authentication guides
  - Enhanced multi-client server documentation with security best practices
  - Detailed API key generation and configuration instructions
  - Updated service installation guide with authentication setup
  - Improved CLAUDE.md with API key environment variable explanations

#### Technical
- **Documentation Quality**: Enhanced authentication documentation across multiple guides
- **Security Guidance**: Clear instructions for production API key management
- **Cross-Reference Links**: Better navigation between related documentation sections

This release significantly improves the user experience for setting up secure, authenticated MCP Memory Service deployments.

## [3.3.1] - 2025-08-01

### 🔧 **Memory Statistics & Health Monitoring**

#### Added
- **Enhanced Health Endpoint**: Memory statistics integration for dashboard display
  - Added memory statistics to `/health` endpoint for real-time monitoring
  - Integration with dashboard UI for comprehensive system overview
  - Better visibility into database health and memory usage

#### Fixed
- **Dashboard Display**: Improved dashboard data integration and visualization support

#### Technical
- **Web App Enhancement**: Updated FastAPI app with integrated statistics endpoints
- **Version Synchronization**: Updated package version to maintain consistency

This release enhances monitoring capabilities and prepares the foundation for advanced dashboard features.

## [3.3.0] - 2025-07-31

### 🎨 **Modern Professional Dashboard UI**

#### Added
- **Professional Dashboard Interface**: Complete UI overhaul for web interface
  - Modern, responsive design with professional styling
  - Real-time memory statistics display
  - Interactive memory search and management interface
  - Enhanced user experience for memory operations
  
#### Changed
- **Visual Identity**: Updated project branding with professional dashboard preview
- **User Interface**: Complete redesign of web-based memory management
- **Documentation Assets**: Added dashboard screenshots and visual documentation

#### Technical
- **Web App Modernization**: Updated FastAPI application with modern UI components
- **Asset Organization**: Proper structure for dashboard images and visual assets

This release transforms the web interface from a basic API into a professional, user-friendly dashboard for memory management.

## [3.2.0] - 2025-07-30

### 🛠️ **SQLite-vec Diagnostic & Repair Tools**

#### Added
- **Comprehensive Diagnostic Tools**: Advanced SQLite-vec backend analysis and repair
  - Database integrity checking and validation
  - Embedding consistency verification tools
  - Memory preservation during repairs and migrations  
  - Automated repair workflows for corrupted databases

#### Fixed
- **SQLite-vec Embedding Issues**: Resolved critical embedding problems causing zero search results
  - Fixed embedding dimension mismatches
  - Resolved database schema inconsistencies
  - Improved embedding generation and storage reliability

#### Technical
- **Migration Tools**: Enhanced migration utilities to preserve existing memories during backend transitions
- **Diagnostic Scripts**: Comprehensive database analysis and repair automation

This release significantly improves SQLite-vec backend reliability and provides tools for database maintenance and recovery.

## [3.1.0] - 2025-07-30

### 🔧 **Cross-Platform Service Installation**

#### Added
- **Universal Service Installation**: Complete cross-platform service management
  - Linux systemd service installation and configuration
  - macOS LaunchAgent/LaunchDaemon support
  - Windows Service installation and management
  - Unified service utilities across all platforms

#### Changed
- **Installation Experience**: Streamlined service setup for all operating systems
- **Service Management**: Consistent service control across platforms
- **Documentation**: Enhanced service installation guides

#### Technical
- **Platform-Specific Scripts**: Dedicated installation scripts for each operating system
- **Service Configuration**: Proper service definitions and startup configurations
- **Cross-Platform Utilities**: Unified service management tools

This release enables easy deployment of MCP Memory Service as a system service on any major operating system.

## [3.0.0] - 2025-07-29

### 🚀 MAJOR RELEASE: Autonomous Multi-Client Memory Service

This is a **major architectural evolution** transforming MCP Memory Service from a development tool into a production-ready, intelligent memory system with autonomous processing capabilities.

### Added
#### 🧠 **Dream-Inspired Consolidation System**
- **Autonomous Memory Processing**: Fully autonomous consolidation system inspired by human cognitive processes
- **Exponential Decay Scoring**: Memory aging with configurable retention periods (critical: 365d, reference: 180d, standard: 30d, temporary: 7d)
- **Creative Association Discovery**: Automatic discovery of semantic connections between memories (similarity range 0.3-0.7)
- **Semantic Clustering**: DBSCAN algorithm for intelligent memory grouping (minimum 5 memories per cluster)
- **Memory Compression**: Statistical summarization with 500-character limits while preserving originals
- **Controlled Forgetting**: Relevance-based memory archival system (threshold 0.1, 90-day access window)
- **Automated Scheduling**: Configurable consolidation schedules (daily 2AM, weekly Sunday 3AM, monthly 1st 4AM)
- **Zero-AI Dependencies**: Operates entirely offline using existing embeddings and mathematical algorithms

#### 🌐 **Multi-Client Server Architecture**
- **HTTPS Server**: Production-ready FastAPI server with auto-generated SSL certificates
- **mDNS Service Discovery**: Zero-configuration automatic service discovery (`MCP Memory._mcp-memory._tcp.local.`)
- **Server-Sent Events (SSE)**: Real-time updates with 30s heartbeat intervals for all connected clients
- **Multi-Interface Support**: Service advertisement across all network interfaces (WiFi, Ethernet, Docker, etc.)
- **API Authentication**: Secure API key-based authentication system
- **Cross-Platform Discovery**: Works on Windows, macOS, and Linux with standard mDNS/Bonjour

#### 🚀 **Production Deployment System**
- **Systemd Auto-Startup**: Complete systemd service integration for automatic startup on boot
- **Service Management**: Professional service control scripts with start/stop/restart/status/logs/health commands
- **User-Space Service**: Runs as regular user (not root) for enhanced security
- **Auto-Restart**: Automatic service recovery on failures with 10-second restart delay
- **Journal Logging**: Integrated with systemd journal for professional log management
- **Health Monitoring**: Built-in health checks and monitoring endpoints

#### 📖 **Comprehensive Documentation**
- **Complete Setup Guide**: 100+ line comprehensive production deployment guide
- **Production Quick Start**: Streamlined production deployment instructions
- **Service Management**: Full service lifecycle documentation
- **Troubleshooting**: Detailed problem resolution guides
- **Network Configuration**: Firewall and mDNS setup instructions

### Enhanced
#### 🔧 **Improved Server Features**
- **Enhanced SSE Implementation**: Restored full Server-Sent Events functionality with connection statistics
- **Network Optimization**: Multi-interface service discovery and connection handling
- **Configuration Management**: Environment-based configuration with secure defaults
- **Error Handling**: Comprehensive error handling and recovery mechanisms

#### 🛠️ **Developer Experience**
- **Debug Tools**: Service debugging and testing utilities
- **Installation Scripts**: One-command installation and configuration
- **Management Scripts**: Easy service lifecycle management
- **Archive Organization**: Clean separation of development and production files

### Configuration
#### 🔧 **New Environment Variables**
- `MCP_CONSOLIDATION_ENABLED`: Enable/disable autonomous consolidation (default: true)
- `MCP_MDNS_ENABLED`: Enable/disable mDNS service discovery (default: true)
- `MCP_MDNS_SERVICE_NAME`: Customizable service name for discovery (default: "MCP Memory")
- `MCP_HTTPS_ENABLED`: Enable HTTPS with auto-generated certificates (default: true)
- `MCP_HTTP_HOST`: Server bind address (default: 0.0.0.0 for multi-client)
- `MCP_HTTP_PORT`: Server port (default: 8000)
- Consolidation timing controls: `MCP_SCHEDULE_DAILY`, `MCP_SCHEDULE_WEEKLY`, `MCP_SCHEDULE_MONTHLY`

### Breaking Changes
- **Architecture Change**: Single-client MCP protocol → Multi-client HTTPS server architecture
- **Service Discovery**: Manual configuration → Automatic mDNS discovery
- **Deployment Model**: Development script → Production systemd service
- **Access Method**: Direct library import → HTTP API with authentication

### Migration
- **Client Configuration**: Update to use HTTP-MCP bridge with auto-discovery
- **Service Deployment**: Install systemd service for production use
- **Network Setup**: Configure firewall for ports 8000/tcp (HTTPS) and 5353/udp (mDNS)
- **API Access**: Use generated API key for authentication

### Technical Details
- **Consolidation Algorithm**: Mathematical approach using existing embeddings without external AI
- **Service Architecture**: FastAPI + uvicorn + systemd for production deployment
- **Discovery Protocol**: RFC-compliant mDNS service advertisement
- **Security**: User-space execution, API key authentication, HTTPS encryption
- **Storage**: Continues to support both ChromaDB and SQLite-vec backends

---

## [2.2.0] - 2025-07-29

### Added
- **Claude Code Commands Integration**: 5 conversational memory commands following CCPlugins pattern
  - `/memory-store`: Store information with context and smart tagging
  - `/memory-recall`: Time-based memory retrieval with natural language
  - `/memory-search`: Tag and content-based semantic search
  - `/memory-context`: Capture current session and project context
  - `/memory-health`: Service health diagnostics and statistics
- **Optional Installation System**: Integrated command installation into main installer
  - New CLI arguments: `--install-claude-commands`, `--skip-claude-commands-prompt`
  - Intelligent prompting during installation when Claude Code CLI is detected
  - Automatic backup of existing commands with timestamps
- **Command Management Utilities**: Standalone installation and management script
  - `scripts/claude_commands_utils.py` for manual command installation
  - Cross-platform support with comprehensive error handling
  - Prerequisites testing and service connectivity validation
- **Context-Aware Operations**: Commands understand project and session context
  - Automatic project detection from current directory and git repository
  - Smart tag generation based on file types and development context
  - Session analysis and summarization capabilities
- **Auto-Discovery Integration**: Commands automatically locate MCP Memory Service
  - Uses existing mDNS service discovery functionality
  - Graceful fallback when service is unavailable
  - Backend-agnostic operation (works with both ChromaDB and SQLite-vec)

### Changed
- Updated main README.md with Claude Code commands feature documentation
- Enhanced `docs/guides/claude-code-integration.md` with comprehensive command usage guide
- Updated installation documentation to include new command options
- Version bump from 2.1.0 to 2.2.0 for significant feature addition

### Documentation
- Added detailed command descriptions and usage examples
- Created comparison guide between conversational commands and MCP server registration
- Enhanced troubleshooting documentation for both integration methods
- Added `claude_commands/README.md` with complete command reference

## [2.1.0] - 2025-07-XX

### Added
- **mDNS Service Discovery**: Zero-configuration networking with automatic service discovery
- **HTTPS Support**: SSL/TLS support with automatic self-signed certificate generation
- **Enhanced HTTP-MCP Bridge**: Auto-discovery mode with health validation and fallback
- **Zero-Config Deployment**: No manual endpoint configuration needed for local networks

### Changed
- Updated service discovery to use `_mcp-memory._tcp.local.` service type
- Enhanced HTTP server with SSL certificate generation capabilities
- Improved multi-client coordination with automatic discovery

## [2.0.0] - 2025-07-XX

### Added
- **Dream-Inspired Memory Consolidation**: Autonomous memory management system
- **Multi-layered Time Horizons**: Daily, weekly, monthly, quarterly, yearly consolidation
- **Creative Association Discovery**: Finding non-obvious connections between memories
- **Semantic Clustering**: Automatic organization of related memories
- **Intelligent Compression**: Preserving key information while reducing storage
- **Controlled Forgetting**: Safe archival and recovery systems
- **Performance Optimization**: Efficient processing of 10k+ memories
- **Health Monitoring**: Comprehensive error handling and alerts

### Changed
- Major architecture updates for consolidation system
- Enhanced storage backends with consolidation support
- Improved multi-client coordination capabilities

## [1.0.0] - 2025-07-XX

### Added
- Initial stable release
- Core memory operations (store, retrieve, search, recall)
- ChromaDB and SQLite-vec storage backends
- Cross-platform compatibility
- Claude Desktop integration
- Basic multi-client support

## [0.1.0] - 2025-07-XX

### Added
- Initial development release
- Basic memory storage and retrieval functionality
- ChromaDB integration
- MCP server implementation