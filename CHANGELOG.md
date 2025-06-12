# CHANGELOG

## v1.1.0 (2025-06-07) - Enhanced Tag Management

### 🎉 Major Features

#### Issue 5 Resolution: Delete Tag Function Ambiguity
- **FIXED**: API inconsistency between `search_by_tag` and `delete_by_tag`
- **ENHANCED**: `delete_by_tag` now supports both single tags and multiple tags
- **BACKWARD COMPATIBLE**: All existing code continues to work unchanged

### ✨ New Features

#### Enhanced Delete Operations
- **Enhanced `delete_by_tag`**: Now accepts both `string` and `List[str]` parameters
- **New `delete_by_tags`**: Explicit multi-tag deletion with OR logic
- **New `delete_by_all_tags`**: Delete memories containing ALL specified tags (AND logic)
- **Improved Error Messages**: More descriptive feedback for all tag operations

#### MCP Server Enhancements
- **New Tool Definitions**: Added `delete_by_tags` and `delete_by_all_tags` tools
- **Enhanced Parameter Handling**: Flexible parameter formats for delete operations
- **Better Type Validation**: Improved input validation and error handling
- **Enhanced Documentation**: Updated tool descriptions with examples

### 🛠️ Technical Improvements

#### API Changes
```python
# Before (still works - backward compatible)
await storage.delete_by_tag("single_tag")

# Enhanced (new functionality)
await storage.delete_by_tag(["tag1", "tag2", "tag3"])        # OR logic
await storage.delete_by_tags(["tag1", "tag2"])               # Explicit OR logic  
await storage.delete_by_all_tags(["urgent", "important"])    # AND logic
```

#### Storage Layer
- **Enhanced ChromaMemoryStorage**: Updated delete methods with flexible parameter handling
- **Improved Tag Matching**: Better logic for tag comparison and matching
- **Enhanced Error Handling**: More descriptive error messages and better validation
- **Performance Optimization**: Efficient batch operations for multiple tag deletion

#### Server Layer
- **New Tool Handlers**: Added handlers for new delete operations
- **Enhanced Parameter Processing**: Flexible handling of both `tag` and `tags` parameters
- **Improved Logging**: Better debugging information for tag operations
- **Enhanced Type Safety**: Better parameter validation and type checking

### 🧪 Testing
- **Comprehensive Test Suite**: New `test_issue_5_fix.py` for enhanced functionality
- **Edge Case Coverage**: Tests for empty inputs, non-existent tags, type validation
- **Backward Compatibility Tests**: Ensures existing code continues to work
- **Integration Tests**: Verification of MCP server tool integration

### 📚 Documentation
- **Updated README**: Enhanced documentation with new API examples
- **API Documentation**: Updated tool descriptions and usage examples
- **Migration Guide**: Though no migration needed due to backward compatibility
- **Enhanced Examples**: Comprehensive usage examples for all delete operations

### 🔧 Infrastructure  
- **Enhanced Code Organization**: Better separation of concerns in delete operations
- **Improved Error Handling**: More robust error handling and user feedback
- **Better Logging**: Enhanced debugging and monitoring capabilities

## v0.1.0 (2024-12-27)

### Chores

- Update gitignore
  ([`97ba25c`](https://github.com/doobidoo/mcp-memory-service/commit/97ba25c83113ed228d6684b8c65bc65774c0b704))

### Features

- Add MCP protocol compliance and fix response formats
  ([`fefd579`](https://github.com/doobidoo/mcp-memory-service/commit/fefd5796b3fb758023bb574b508940a651e48ad5))

---

## Migration Notes

### From v0.1.0 to v1.1.0
**No migration required!** - All changes are backward compatible.

### API Compatibility
- All existing `delete_by_tag("single_tag")` calls continue to work
- Enhanced functionality available immediately  
- No code changes required for existing implementations
- New methods available for enhanced functionality
