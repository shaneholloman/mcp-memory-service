# Changelog

All notable changes to the MCP Memory Service project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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