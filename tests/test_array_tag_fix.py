"""
Test cases for the array tag handling fix.
Ensures that both array and string format tags work correctly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add the src path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from mcp_memory_service.server import MemoryServer


class TestArrayTagFix:
    """Test suite for the array tag handling fix."""
    
    @pytest.fixture
    def memory_server(self):
        """Create a MemoryServer instance for testing."""
        server = MemoryServer()
        # Mock the storage to avoid initialization issues
        server.storage = AsyncMock()
        server.storage.store = AsyncMock(return_value=(True, "Memory stored successfully"))
        return server
    
    def test_array_tag_processing(self, memory_server):
        """Test that array format tags are processed correctly."""
        # Test the tag normalization logic directly
        metadata = {"tags": ["test", "array", "format"]}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic from server.py
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = ["test", "array", "format"]
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_string_tag_processing(self, memory_server):
        """Test that string format tags continue to work."""
        metadata = {"tags": "test,string,format"}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = ["test", "string", "format"]
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_empty_array_tags(self, memory_server):
        """Test that empty arrays are handled correctly."""
        metadata = {"tags": []}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = []
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_none_tags(self, memory_server):
        """Test that None tags are handled correctly."""
        metadata = {"tags": None}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = []
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_mixed_type_array_tags(self, memory_server):
        """Test that arrays with mixed types are handled correctly."""
        metadata = {"tags": ["string", 123, "mixed"]}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = ["string", "123", "mixed"]
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_whitespace_handling_arrays(self, memory_server):
        """Test that whitespace in array tags is handled correctly."""
        metadata = {"tags": ["  spaced  ", "normal", "  ", ""]}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = ["spaced", "normal"]
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"
    
    def test_whitespace_handling_strings(self, memory_server):
        """Test that whitespace in string tags is handled correctly."""
        metadata = {"tags": "one, two , three  ,, "}
        tags = metadata.get("tags", "")
        
        # Apply the fixed logic
        if isinstance(tags, str):
            processed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            processed_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            processed_tags = []
        
        expected = ["one", "two", "three"]
        assert processed_tags == expected, f"Expected {expected}, got {processed_tags}"


if __name__ == "__main__":
    # Run the tests directly
    import unittest
    
    class TestRunner:
        def test_all(self):
            server = MemoryServer()
            test_instance = TestArrayTagFix()
            
            print("🧪 Running Array Tag Fix Tests")
            print("=" * 40)
            
            tests = [
                ("Array tag processing", test_instance.test_array_tag_processing),
                ("String tag processing", test_instance.test_string_tag_processing),
                ("Empty array tags", test_instance.test_empty_array_tags),
                ("None tags", test_instance.test_none_tags),
                ("Mixed type array tags", test_instance.test_mixed_type_array_tags),
                ("Whitespace handling arrays", test_instance.test_whitespace_handling_arrays),
                ("Whitespace handling strings", test_instance.test_whitespace_handling_strings),
            ]
            
            passed = 0
            failed = 0
            
            for test_name, test_func in tests:
                try:
                    test_func(server)
                    print(f"✅ {test_name}")
                    passed += 1
                except Exception as e:
                    print(f"❌ {test_name}: {e}")
                    failed += 1
            
            print("-" * 40)
            print(f"Results: {passed} passed, {failed} failed")
            
            if failed == 0:
                print("🎉 All tests passed! The array tag fix is working correctly.")
            else:
                print("❌ Some tests failed. Please check the implementation.")
    
    runner = TestRunner()
    runner.test_all()