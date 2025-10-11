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
Sync management endpoints for hybrid backend.

Provides status monitoring and manual sync triggering for hybrid storage mode.
"""

from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...storage.base import MemoryStorage
from ..dependencies import get_storage
from ...config import OAUTH_ENABLED

# OAuth authentication imports (conditional)
if OAUTH_ENABLED or TYPE_CHECKING:
    from ..oauth.middleware import require_read_access, require_write_access, AuthenticationResult
else:
    # Provide type stubs when OAuth is disabled
    AuthenticationResult = None
    require_read_access = None
    require_write_access = None

router = APIRouter()


class SyncStatusResponse(BaseModel):
    """Sync status response model."""
    is_hybrid: bool
    is_running: bool
    last_sync_time: float
    operations_pending: int
    operations_processed: int
    operations_failed: int
    sync_interval_seconds: int
    time_since_last_sync_seconds: float
    next_sync_eta_seconds: float
    status: str  # 'synced', 'syncing', 'pending', 'error'


class SyncForceResponse(BaseModel):
    """Force sync response model."""
    success: bool
    message: str
    operations_synced: int
    time_taken_seconds: float
    timestamp: str


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_read_access) if OAUTH_ENABLED else None
):
    """
    Get current sync status for hybrid backend.

    Returns sync state, pending operations, last sync time, and health metrics.
    Only available when using hybrid storage backend.
    """
    # Check if storage supports sync (hybrid mode only)
    if not hasattr(storage, 'get_sync_status'):
        return SyncStatusResponse(
            is_hybrid=False,
            is_running=False,
            last_sync_time=0,
            operations_pending=0,
            operations_processed=0,
            operations_failed=0,
            sync_interval_seconds=0,
            time_since_last_sync_seconds=0,
            next_sync_eta_seconds=0,
            status='not_hybrid'
        )

    try:
        # Get sync status from hybrid backend
        sync_status = await storage.get_sync_status()

        # Calculate time since last sync
        import time
        current_time = time.time()
        last_sync = sync_status.get('last_sync_time', 0)
        time_since_sync = current_time - last_sync if last_sync > 0 else 0

        # Calculate ETA for next sync
        sync_interval = sync_status.get('sync_interval', 300)
        next_sync_eta = max(0, sync_interval - time_since_sync)

        # Determine status
        is_running = sync_status.get('is_running', False)
        pending_ops = sync_status.get('pending_operations', 0)
        actively_syncing = sync_status.get('actively_syncing', False)  # True only during active sync

        if actively_syncing:
            status = 'syncing'
        elif pending_ops > 0:
            status = 'pending'
        elif sync_status.get('operations_failed', 0) > 0:
            status = 'error'
        else:
            status = 'synced'

        return SyncStatusResponse(
            is_hybrid=True,
            is_running=is_running,
            last_sync_time=last_sync,
            operations_pending=pending_ops,
            operations_processed=sync_status.get('operations_processed', 0),
            operations_failed=sync_status.get('operations_failed', 0),
            sync_interval_seconds=sync_interval,
            time_since_last_sync_seconds=time_since_sync,
            next_sync_eta_seconds=next_sync_eta,
            status=status
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.post("/sync/force", response_model=SyncForceResponse)
async def force_sync(
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_write_access) if OAUTH_ENABLED else None
):
    """
    Manually trigger immediate sync to Cloudflare.

    Forces all pending operations to sync immediately instead of waiting
    for the next scheduled sync interval.
    Only available when using hybrid storage backend.
    """
    # Check if storage supports force sync (hybrid mode only)
    if not hasattr(storage, 'force_sync'):
        raise HTTPException(
            status_code=404,
            detail="Manual sync only available in hybrid mode"
        )

    try:
        import time
        start_time = time.time()

        # Trigger force sync
        sync_result = await storage.force_sync()

        time_taken = time.time() - start_time

        return SyncForceResponse(
            success=sync_result.get('success', False),
            message=sync_result.get('message', 'Sync completed'),
            operations_synced=sync_result.get('operations_synced', 0),
            time_taken_seconds=round(time_taken, 3),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to force sync: {str(e)}"
        )
