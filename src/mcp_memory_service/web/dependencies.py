# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
FastAPI dependencies for the HTTP interface.
"""

from typing import Optional
from fastapi import HTTPException

from ..storage.sqlite_vec import SqliteVecMemoryStorage

# Global storage instance
_storage: Optional[SqliteVecMemoryStorage] = None


def set_storage(storage: SqliteVecMemoryStorage) -> None:
    """Set the global storage instance."""
    global _storage
    _storage = storage


def get_storage() -> SqliteVecMemoryStorage:
    """Get the global storage instance."""
    if _storage is None:
        raise HTTPException(status_code=503, detail="Storage not initialized")
    return _storage