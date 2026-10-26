# Multi-Kiosk Support Architecture Design

## Overview

This document outlines the architecture for supporting multiple kiosks sharing a single attendance system installation. This enables schools to have multiple entry/exit points (e.g., main entrance, side doors, gym) all connected to a central database.

## Current Limitations

- Single kiosk mode assumes one camera feed at `/kiosk`
- No device identification or kiosk-specific configuration
- All attendance logs are attributed to a single "kiosk"
- No support for location-based attendance tracking

## Proposed Architecture

### 1. Kiosk Registration and Identification

**Kiosk Table:**
```sql
CREATE TABLE kiosks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL,
    device_id TEXT NOT NULL UNIQUE,  -- Browser/device fingerprint
    camera_device TEXT,  -- Specific camera identifier
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP
);
```

**Kiosk Registration Flow:**
1. When a new kiosk accesses `/kiosk`, check for existing kiosk by device_id
2. If not found, prompt admin to register the kiosk (name, location)
3. Store device_id (fingerprint) for future identification
4. Kiosk-specific settings (camera device, location) stored per kiosk

### 2. Kiosk-Specific Attendance Logging

**Enhanced Attendance Logs:**
```sql
ALTER TABLE attendance_logs ADD COLUMN kiosk_id INTEGER;
ALTER TABLE attendance_logs ADD FOREIGN KEY (kiosk_id) REFERENCES kiosks(id);
```

**Logging Changes:**
- Each attendance record includes which kiosk recorded it
- Enables location-based attendance reporting
- Supports troubleshooting which kiosk had issues

### 3. Kiosk Configuration Management

**Kiosk Settings Table:**
```sql
CREATE TABLE kiosk_settings (
    kiosk_id INTEGER PRIMARY KEY,
    camera_device TEXT,
    camera_resolution TEXT DEFAULT '640x480',
    camera_fps INTEGER DEFAULT 30,
    audio_enabled INTEGER DEFAULT 0,
    welcome_message TEXT,
    FOREIGN KEY (kiosk_id) REFERENCES kiosks(id) ON DELETE CASCADE
);
```

**Per-Kiosk Settings:**
- Camera device selection (which camera to use)
- Resolution and FPS preferences
- Audio feedback toggle
- Custom welcome messages
- Location-specific announcements

### 4. Kiosk Monitoring and Status

**Kiosk Status Table:**
```sql
CREATE TABLE kiosk_status (
    kiosk_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,  -- online, offline, error
    last_heartbeat TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (kiosk_id) REFERENCES kiosks(id) ON DELETE CASCADE
);
```

**Heartbeat Mechanism:**
- Kiosks send heartbeat every 30 seconds via WebSocket
- Dashboard shows kiosk status (online/offline/error)
- Alerts when kiosk goes offline unexpectedly
- Last activity tracking per kiosk

### 5. Database Schema Changes

**Migration Script:**
```python
def migrate_to_multi_kiosk():
    with get_db() as conn:
        # Add kiosks table
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS kiosks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT NOT NULL,
                device_id TEXT NOT NULL UNIQUE,
                camera_device TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS kiosk_settings (
                kiosk_id INTEGER PRIMARY KEY,
                camera_device TEXT,
                camera_resolution TEXT DEFAULT '640x480',
                camera_fps INTEGER DEFAULT 30,
                audio_enabled INTEGER DEFAULT 0,
                welcome_message TEXT,
                FOREIGN KEY (kiosk_id) REFERENCES kiosks(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS kiosk_status (
                kiosk_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                last_heartbeat TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (kiosk_id) REFERENCES kiosks(id) ON DELETE CASCADE
            );
        """)
        
        # Add kiosk_id to attendance_logs
        if "kiosk_id" not in get_table_columns("attendance_logs"):
            conn.execute("ALTER TABLE attendance_logs ADD COLUMN kiosk_id INTEGER")
            conn.execute("ALTER TABLE attendance_logs ADD FOREIGN KEY (kiosk_id) REFERENCES kiosks(id)")
```

### 6. API Changes

**New Endpoints:**

```python
# Kiosk registration
@app.post("/api/kiosks/register")
async def register_kiosk(kiosk_data: KioskRegistration):
    """Register a new kiosk device."""
    pass

# Kiosk status
@app.get("/api/kiosks/{kiosk_id}/status")
async def get_kiosk_status(kiosk_id: int):
    """Get kiosk status information."""
    pass

@app.post("/api/kiosks/{kiosk_id}/heartbeat")
async def kiosk_heartbeat(kiosk_id: int):
    """Update kiosk heartbeat timestamp."""
    pass

# Kiosk settings
@app.get("/api/kiosks/{kiosk_id}/settings")
async def get_kiosk_settings(kiosk_id: int):
    """Get kiosk-specific settings."""
    pass

@app.patch("/api/kiosks/{kiosk_id}/settings")
async def update_kiosk_settings(kiosk_id: int, settings: KioskSettings):
    """Update kiosk-specific settings."""
    pass

# Kiosk management (admin)
@app.get("/api/kiosks")
async def list_kiosks():
    """List all registered kiosks."""
    pass

@app.patch("/api/kiosks/{kiosk_id}")
async def update_kiosk(kiosk_id: int, kiosk_data: KioskUpdate):
    """Update kiosk information."""
    pass

@app.delete("/api/kiosks/{kiosk_id}")
async def delete_kiosk(kiosk_id: int):
    """Deactivate a kiosk."""
    pass
```

**Modified Endpoints:**

```python
# Enhanced attendance logging
@app.post("/api/attendance/log")
async def log_attendance(
    employee_id: str,
    event_type: str,
    status: str,
    kiosk_id: Optional[int] = None  # New parameter
):
    """Log attendance with kiosk identification."""
    pass

# Kiosk-specific WebSocket
@app.websocket("/ws/kiosk/{kiosk_id}")
async def ws_kiosk_specific(websocket: WebSocket, kiosk_id: int):
    """Kiosk-specific WebSocket connection."""
    pass
```

### 7. Frontend Changes

**Kiosk Selection/Registration:**
- On first visit to `/kiosk`, check for registered kiosk
- If not registered, show registration form
- Admin approval required for new kiosks
- Store kiosk_id in session/local storage

**Kiosk Dashboard Enhancements:**
- Show kiosk location name in header
- Display kiosk-specific camera settings
- Show connection status indicator

**Admin Dashboard Changes:**
- New "Kiosks" section
- List all registered kiosks with status
- Real-time status updates via WebSocket
- Kiosk management (edit, deactivate, view settings)
- Attendance logs filterable by kiosk

### 8. Implementation Phases

**Phase 1: Database and Backend (Week 1)**
- Add kiosk tables to database schema
- Implement migration script
- Create kiosk CRUD operations
- Add kiosk_id to attendance logging

**Phase 2: Kiosk Registration (Week 2)**
- Implement device fingerprinting
- Create registration flow
- Add admin approval workflow
- Implement session management for kiosks

**Phase 3: WebSocket and Monitoring (Week 3)**
- Implement heartbeat mechanism
- Add kiosk status tracking
- Create kiosk-specific WebSocket endpoints
- Add real-time status updates to admin dashboard

**Phase 4: Frontend Integration (Week 4)**
- Update kiosk page with registration flow
- Add kiosk selection to admin dashboard
- Implement kiosk settings UI
- Add kiosk-specific camera configuration

**Phase 5: Testing and Validation (Week 5)**
- Test with multiple kiosks
- Validate attendance attribution
- Test offline detection
- Performance testing with concurrent kiosks

### 9. Security Considerations

**Device Identification:**
- Use browser fingerprinting for device_id
- Include user agent, screen resolution, timezone
- Salt and hash fingerprint for privacy
- Allow manual device_id override for testing

**Access Control:**
- Only admins can register/deactivate kiosks
- Kiosk-specific sessions don't have admin privileges
- Kiosk cannot access other kiosks' data
- Rate limiting on registration attempts

**Data Privacy:**
- Device fingerprints should be hashed
- No camera images stored without consent
- Kiosk location data should be optional
- Audit trail for kiosk management actions

### 10. Fallback and Compatibility

**Single-Kiosk Mode:**
- If no kiosks registered, default to kiosk_id = NULL
- Existing single-kiosk deployments continue to work
- Gradual migration path for existing installations

**Backward Compatibility:**
- kiosk_id is nullable in attendance_logs
- Old attendance records have kiosk_id = NULL
- Dashboard handles NULL kiosk_id gracefully
- API supports both kiosk-specific and legacy calls

### 11. Performance Considerations

**Database Indexing:**
```sql
CREATE INDEX idx_attendance_kiosk_id ON attendance_logs(kiosk_id);
CREATE INDEX idx_kiosks_device_id ON kiosks(device_id);
CREATE INDEX idx_kiosk_status ON kiosk_status(status, last_heartbeat);
```

**Caching:**
- Cache kiosk settings in memory
- Cache device fingerprint lookups
- WebSocket connection pooling for heartbeats

**Concurrency:**
- Multiple kiosks can connect simultaneously
- Async I/O for attendance logging
- Connection pooling for database access

### 12. Monitoring and Alerting

**Metrics to Track:**
- Kiosk uptime/availability
- Attendance volume per kiosk
- Camera connection failures per kiosk
- Network latency per kiosk

**Alerts:**
- Kiosk offline for > 5 minutes
- High error rate on specific kiosk
- Camera disconnection on active kiosk
- Unusual attendance patterns

## Conclusion

This multi-kiosk architecture provides:
- Support for unlimited kiosks per installation
- Location-based attendance tracking
- Per-kiosk configuration and monitoring
- Backward compatibility with single-k setups
- Security and privacy protections
- Scalable performance for concurrent kiosks

The phased implementation allows for gradual rollout and testing while maintaining system stability.
