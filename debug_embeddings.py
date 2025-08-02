#!/usr/bin/env python3
"""
Debug script to check actual embedding values in SQLite-vec.
"""

import sqlite3
import sys
import os
import numpy as np

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import sqlite_vec
    from sqlite_vec import serialize_float32
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

def debug_embeddings():
    """Check actual embedding values in the database."""
    print("🔍 Debugging SQLite-vec embedding values...")
    
    db_path = "/home/hkr/.local/share/mcp-memory/sqlite_vec.db"
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    
    # Check some memories and their embeddings
    cursor = conn.execute("""
        SELECT m.id, m.content, m.content_hash
        FROM memories m
        ORDER BY m.created_at DESC
        LIMIT 3
    """)
    
    memories = cursor.fetchall()
    print(f"\nFound {len(memories)} recent memories:")
    
    for memory_id, content, content_hash in memories:
        print(f"\n--- Memory ID: {memory_id} ---")
        print(f"Content: {content[:60]}...")
        print(f"Hash: {content_hash}")
        
        # Get embedding for this memory
        cursor = conn.execute("""
            SELECT content_embedding FROM memory_embeddings WHERE rowid = ?
        """, (memory_id,))
        
        embedding_row = cursor.fetchone()
        if embedding_row:
            # The embedding is stored as blob, need to deserialize
            embedding_blob = embedding_row[0]
            print(f"Embedding blob length: {len(embedding_blob) if embedding_blob else 'None'}")
            
            if embedding_blob and len(embedding_blob) > 0:
                # Check if it looks like it has actual values
                print(f"First few bytes: {embedding_blob[:20]}")
                
                # Try to convert to numpy array to analyze
                try:
                    # SQLite-vec uses float32 format
                    embedding_array = np.frombuffer(embedding_blob, dtype=np.float32)
                    print(f"Embedding dimensions: {len(embedding_array)}")
                    print(f"Embedding stats - Min: {embedding_array.min():.6f}, Max: {embedding_array.max():.6f}, Mean: {embedding_array.mean():.6f}")
                    print(f"Non-zero values: {np.count_nonzero(embedding_array)}/{len(embedding_array)}")
                    
                    # Check if it's all zeros
                    if np.allclose(embedding_array, 0):
                        print("🚨 WARNING: Embedding is all zeros!")
                    elif np.all(embedding_array == embedding_array[0]):
                        print("🚨 WARNING: Embedding has all identical values!")
                    else:
                        print("✅ Embedding has varied values (looks normal)")
                        
                except Exception as e:
                    print(f"Failed to parse embedding: {e}")
            else:
                print("🚨 WARNING: No embedding data found!")
        else:
            print("🚨 WARNING: No embedding found for this memory!")
    
    # Test generating a new embedding to compare
    print(f"\n--- Testing fresh embedding generation ---")
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        test_text = "test embedding generation"
        fresh_embedding = model.encode([test_text], convert_to_numpy=True)[0]
        print(f"Fresh embedding dimensions: {len(fresh_embedding)}")
        print(f"Fresh embedding stats - Min: {fresh_embedding.min():.6f}, Max: {fresh_embedding.max():.6f}, Mean: {fresh_embedding.mean():.6f}")
        print(f"Fresh embedding non-zero: {np.count_nonzero(fresh_embedding)}/{len(fresh_embedding)}")
        
        # Test similarity between fresh embeddings
        test_text2 = "test embedding generation"  # Same text
        fresh_embedding2 = model.encode([test_text2], convert_to_numpy=True)[0]
        similarity = np.dot(fresh_embedding, fresh_embedding2) / (np.linalg.norm(fresh_embedding) * np.linalg.norm(fresh_embedding2))
        print(f"Self-similarity (should be ~1.0): {similarity:.6f}")
        
    except Exception as e:
        print(f"Failed to test fresh embedding: {e}")
    
    conn.close()

if __name__ == "__main__":
    debug_embeddings()