#!/usr/bin/env python3
"""
Download HuggingFace embedding model with error handling.
Sets SKIP_MODEL_TESTS=true in GITHUB_ENV on failure.
"""
import sys
import os

try:
    print('Downloading embedding model...')
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('✓ Model cached successfully')
except Exception as e:
    print(f'⚠️ Model download failed: {e}', file=sys.stderr)
    print('Setting SKIP_MODEL_TESTS=true')

    # Write to GITHUB_ENV if available
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a') as f:
            f.write('SKIP_MODEL_TESTS=true\n')

    sys.exit(0)  # Exit successfully to continue workflow
