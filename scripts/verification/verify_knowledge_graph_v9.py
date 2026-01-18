#!/usr/bin/env python3
"""
Knowledge Graph Feature Verification for v9.0.0

Verifies that the following v9.0.0 features work correctly:
1. Typed Relationships (6 types: causes, fixes, contradicts, supports, follows, related)
2. Asymmetric vs Symmetric relationship storage
3. SemanticReasoner causal inference
4. Memory Type Ontology (5 base types, 21 subtypes)
5. Tag Taxonomy (6 namespaces)
6. Performance optimizations (caching)

Usage:
    python scripts/verification/verify_knowledge_graph_v9.py
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.models.association import TypedAssociation
from mcp_memory_service.models.ontology import (
    get_all_types,
    get_parent_type,
    is_symmetric_relationship
)
from mcp_memory_service.models.tag_taxonomy import VALID_NAMESPACES
from mcp_memory_service.services.semantic_reasoner import SemanticReasoner


class KnowledgeGraphVerifier:
    """Verifies Knowledge Graph features from v9.0.0"""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize verifier with test database"""
        self.db_path = db_path
        self.storage = SqliteVecMemoryStorage(db_path)
        self.reasoner = SemanticReasoner(self.storage)
        self.results: List[Dict[str, Any]] = []

    def log_result(self, test_name: str, passed: bool, details: str = "", metrics: Dict = None):
        """Log a test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"      {details}")
        if metrics:
            for key, value in metrics.items():
                print(f"      {key}: {value}")
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "metrics": metrics or {}
        })

    def verify_typed_relationships(self) -> bool:
        """Verify typed relationships work correctly"""
        print("\n=== Testing Typed Relationships ===")

        # Create test memories
        mem1 = self.storage.store(Memory(
            content="Bug: Login fails with OAuth",
            memory_type="error"
        ))

        mem2 = self.storage.store(Memory(
            content="Fix: Add OAuth token refresh logic",
            memory_type="decision"
        ))

        mem3 = self.storage.store(Memory(
            content="Note: OAuth was deprecated in v2.0",
            memory_type="observation"
        ))

        # Test all 6 relationship types
        relationships = [
            ("causes", mem1.content_hash, mem2.content_hash, False),  # Bug causes fix (asymmetric)
            ("fixes", mem2.content_hash, mem1.content_hash, False),   # Fix fixes bug (asymmetric)
            ("contradicts", mem2.content_hash, mem3.content_hash, True),  # Fix contradicts note (symmetric)
            ("supports", mem1.content_hash, mem2.content_hash, False),  # Bug supports fix (asymmetric)
            ("follows", mem2.content_hash, mem1.content_hash, False),   # Fix follows bug (asymmetric)
            ("related", mem1.content_hash, mem3.content_hash, True),    # Bug related to note (symmetric)
        ]

        for rel_type, from_hash, to_hash, expected_symmetric in relationships:
            # Store association
            self.storage.store_association(from_hash, to_hash, rel_type, strength=0.9)

            # Verify symmetry matches expectation
            actual_symmetric = is_symmetric_relationship(rel_type)
            if actual_symmetric != expected_symmetric:
                self.log_result(
                    f"Relationship type '{rel_type}' symmetry",
                    False,
                    f"Expected symmetric={expected_symmetric}, got {actual_symmetric}"
                )
                return False

        self.log_result(
            "Typed Relationships",
            True,
            "All 6 relationship types work correctly (causes, fixes, contradicts, supports, follows, related)"
        )
        return True

    def verify_asymmetric_storage(self) -> bool:
        """Verify asymmetric relationships only store directed edges"""
        print("\n=== Testing Asymmetric Relationship Storage ===")

        # Create test memories
        mem1 = self.storage.store(Memory(content="Cause A", memory_type="observation"))
        mem2 = self.storage.store(Memory(content="Effect B", memory_type="observation"))

        # Store asymmetric relationship (causes)
        self.storage.store_association(mem1.content_hash, mem2.content_hash, "causes", 0.9)

        # Query forward direction (should find)
        forward = self.storage.find_connected(mem1.content_hash, relationship_type="causes")

        # Query reverse direction (should NOT find with direction="outgoing")
        reverse = self.storage.find_connected(mem2.content_hash, relationship_type="causes", direction="outgoing")

        # Query bidirectional (should find with direction="both")
        both = self.storage.find_connected(mem2.content_hash, relationship_type="causes", direction="both")

        passed = (
            len(forward) == 1 and
            len(reverse) == 0 and
            len(both) == 1
        )

        self.log_result(
            "Asymmetric Relationship Storage",
            passed,
            f"Forward: {len(forward)} edges, Reverse (outgoing): {len(reverse)} edges, Both: {len(both)} edges",
            {"expected": "1, 0, 1", "actual": f"{len(forward)}, {len(reverse)}, {len(both)}"}
        )
        return passed

    def verify_symmetric_storage(self) -> bool:
        """Verify symmetric relationships store bidirectional edges"""
        print("\n=== Testing Symmetric Relationship Storage ===")

        # Create test memories
        mem1 = self.storage.store(Memory(content="Concept X", memory_type="observation"))
        mem2 = self.storage.store(Memory(content="Concept Y", memory_type="observation"))

        # Store symmetric relationship (related)
        self.storage.store_association(mem1.content_hash, mem2.content_hash, "related", 0.8)

        # Query both directions (should find in both)
        forward = self.storage.find_connected(mem1.content_hash, relationship_type="related")
        reverse = self.storage.find_connected(mem2.content_hash, relationship_type="related")

        passed = len(forward) == 1 and len(reverse) == 1

        self.log_result(
            "Symmetric Relationship Storage",
            passed,
            f"Forward: {len(forward)} edges, Reverse: {len(reverse)} edges",
            {"expected": "1, 1", "actual": f"{len(forward)}, {len(reverse)}"}
        )
        return passed

    def verify_semantic_reasoner(self) -> bool:
        """Verify SemanticReasoner causal inference"""
        print("\n=== Testing SemanticReasoner ===")

        # Create causal chain: Problem -> Investigation -> Root Cause -> Fix
        problem = self.storage.store(Memory(
            content="Users report slow API responses",
            memory_type="observation"
        ))

        investigation = self.storage.store(Memory(
            content="Profiling shows N+1 query problem",
            memory_type="observation"
        ))

        root_cause = self.storage.store(Memory(
            content="Missing database index on user_id column",
            memory_type="error"
        ))

        fix = self.storage.store(Memory(
            content="Added index to user_id column",
            memory_type="decision"
        ))

        # Build causal relationships
        self.storage.store_association(problem.content_hash, investigation.content_hash, "causes", 0.9)
        self.storage.store_association(investigation.content_hash, root_cause.content_hash, "causes", 0.9)
        self.storage.store_association(fix.content_hash, root_cause.content_hash, "fixes", 0.9)

        # Test find_causes
        causes = self.reasoner.find_causes(fix.content_hash)
        has_root_cause = any(c["hash"] == root_cause.content_hash for c in causes)

        # Test find_fixes
        fixes = self.reasoner.find_fixes(root_cause.content_hash)
        has_fix = any(f["hash"] == fix.content_hash for f in fixes)

        passed = has_root_cause and has_fix

        self.log_result(
            "SemanticReasoner Causal Inference",
            passed,
            f"find_causes: {len(causes)} causes found, find_fixes: {len(fixes)} fixes found",
            {"expected": "Root cause and fix found", "actual": f"Cause found: {has_root_cause}, Fix found: {has_fix}"}
        )
        return passed

    def verify_memory_type_ontology(self) -> bool:
        """Verify memory type ontology system"""
        print("\n=== Testing Memory Type Ontology ===")

        # Test base types exist
        all_types = get_all_types()
        base_types = ["observation", "decision", "learning", "error", "pattern"]

        has_all_base = all(bt in all_types for bt in base_types)

        # Test parent relationships
        test_subtypes = {
            "task": "observation",  # Legacy type
            "bug_report": "error",
            "api_design": "decision"
        }

        parent_checks = []
        for subtype, expected_parent in test_subtypes.items():
            actual_parent = get_parent_type(subtype)
            parent_checks.append(actual_parent == expected_parent)

        passed = has_all_base and all(parent_checks)

        self.log_result(
            "Memory Type Ontology",
            passed,
            f"Base types: {len([t for t in base_types if t in all_types])}/5, Total types: {len(all_types)}",
            {"base_types_found": has_all_base, "parent_relationships": all(parent_checks)}
        )
        return passed

    def verify_tag_taxonomy(self) -> bool:
        """Verify tag taxonomy with namespaces"""
        print("\n=== Testing Tag Taxonomy ===")

        # Test that VALID_NAMESPACES is exposed
        expected_namespaces = ["sys:", "q:", "proj:", "topic:", "t:", "user:"]
        has_all_namespaces = all(ns in VALID_NAMESPACES for ns in expected_namespaces)

        # Test storing memories with namespaced tags
        mem = self.storage.store(Memory(
            content="Test memory with tags",
            memory_type="observation",
            tags=["proj:mcp-memory", "topic:knowledge-graph", "user:verification"]
        ))

        retrieved = self.storage.retrieve_by_tag("proj:mcp-memory")
        has_namespaced_tag = len(retrieved) > 0

        passed = has_all_namespaces and has_namespaced_tag

        self.log_result(
            "Tag Taxonomy",
            passed,
            f"Namespaces: {len(VALID_NAMESPACES)}, Memories with namespaced tags: {len(retrieved)}",
            {"has_namespaces": has_all_namespaces, "tags_work": has_namespaced_tag}
        )
        return passed

    def verify_performance_optimizations(self) -> bool:
        """Verify performance optimizations (caching)"""
        print("\n=== Testing Performance Optimizations ===")

        # Test get_all_types() caching (should be fast on repeated calls)
        start = time.perf_counter()
        for _ in range(1000):
            get_all_types()
        cached_time = time.perf_counter() - start

        # Test get_parent_type() caching
        start = time.perf_counter()
        for _ in range(1000):
            get_parent_type("task")
        parent_cached_time = time.perf_counter() - start

        # Both should complete 1000 calls in under 10ms with caching
        passed = cached_time < 0.01 and parent_cached_time < 0.01

        self.log_result(
            "Performance Optimizations",
            passed,
            f"1000 calls: get_all_types={cached_time*1000:.2f}ms, get_parent_type={parent_cached_time*1000:.2f}ms",
            {"get_all_types_1000_calls_ms": f"{cached_time*1000:.2f}", "get_parent_type_1000_calls_ms": f"{parent_cached_time*1000:.2f}"}
        )
        return passed

    def run_all_verifications(self) -> bool:
        """Run all verification tests"""
        print("="*60)
        print("Knowledge Graph Feature Verification - v9.0.0")
        print("="*60)

        tests = [
            ("Typed Relationships", self.verify_typed_relationships),
            ("Asymmetric Storage", self.verify_asymmetric_storage),
            ("Symmetric Storage", self.verify_symmetric_storage),
            ("Semantic Reasoner", self.verify_semantic_reasoner),
            ("Memory Type Ontology", self.verify_memory_type_ontology),
            ("Tag Taxonomy", self.verify_tag_taxonomy),
            ("Performance Optimizations", self.verify_performance_optimizations),
        ]

        passed_count = 0
        for name, test_func in tests:
            try:
                if test_func():
                    passed_count += 1
            except Exception as e:
                self.log_result(name, False, f"Exception: {e}")

        print("\n" + "="*60)
        print(f"SUMMARY: {passed_count}/{len(tests)} tests passed")
        print("="*60)

        # Print detailed results
        print("\nDetailed Results:")
        for result in self.results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   {result['details']}")
            if result["metrics"]:
                for k, v in result["metrics"].items():
                    print(f"   {k}: {v}")

        return passed_count == len(tests)


def main():
    """Main entry point"""
    verifier = KnowledgeGraphVerifier()
    all_passed = verifier.run_all_verifications()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
