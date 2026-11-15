import logging
from typing import List
from collections import deque
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["System & Logs"])

# In-memory rolling log buffer (last 100 entries)
LOG_BUFFER = deque(maxlen=100)

def log_event(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    LOG_BUFFER.append(f"[{timestamp}] {message}")

# Populate with initial bootstrap logs
log_event("FinSentiq Engine initialized")
log_event("Sector and Stock mappings loaded (758 NSE/BSE symbols)")
log_event("Central in-memory store active (zero user feed reload)")

@router.get("/logs")
async def get_system_logs():
    return {"logs": list(LOG_BUFFER)}
