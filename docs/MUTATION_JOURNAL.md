# Mutation Journal Architecture

## Overview

The Mutation Journal provides **optimistic updates** and **restore capabilities** for email mutations in the Gmail Secretary Web UI. It bridges the gap between immediate UI feedback and eventual IMAP consistency.

## Key Distinction: Restore vs Undo

| Action Type | Reversible? | Restore Mechanism |
|-------------|-------------|-------------------|
| Move to folder | Yes | Move back to original folder |
| Add/Remove label | Yes | Revert label state |
| Mark read/unread | Yes | Toggle flag back |
| Archive | Yes | Move back to INBOX |
| Delete (to Trash) | Yes | Move back from Trash |
| **Send email** | **NO** | Cannot unsend |
| **Permanent delete** | **NO** | Cannot recover |

**Important**: "Restore" applies the inverse IMAP operation. It is NOT database-level undo.

## Schema

```sql
CREATE TABLE mutation_journal (
    id SERIAL PRIMARY KEY,
    email_uid INTEGER NOT NULL,
    email_folder TEXT NOT NULL,
    action TEXT NOT NULL,           -- 'MOVE', 'LABEL', 'FLAG', 'DELETE'
    params JSONB,                   -- Action-specific parameters
    status TEXT DEFAULT 'PENDING',  -- 'PENDING', 'COMPLETED', 'FAILED'
    pre_state JSONB,                -- State before mutation (for restore)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    error TEXT,                     -- Error message if FAILED
    FOREIGN KEY (email_uid, email_folder) REFERENCES emails(uid, folder)
);
```

## Mutation Lifecycle

```
┌─────────────────┐
│   Web UI        │
│   User Action   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 1. Record       │  mutation_journal: status='PENDING'
│    pre_state    │  pre_state = {folder: "INBOX", is_unread: true, ...}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Optimistic   │  UPDATE emails SET folder='Archive' WHERE uid=123
│    DB Update    │  (UI immediately reflects change)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Engine Call  │  engine_client.move_email(uid, "Archive")
│    (IMAP)       │  
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│SUCCESS│ │FAILED │
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌───────┐ ┌───────────────┐
│COMPLETE│ │Rollback DB    │
│status  │ │from pre_state │
│='DONE' │ │status='FAILED'│
└────────┘ └───────────────┘
```

## Actions and Pre-State

### MOVE Action
```json
{
  "action": "MOVE",
  "params": {"target_folder": "[Gmail]/Archive"},
  "pre_state": {"folder": "INBOX"}
}
```

### LABEL Action
```json
{
  "action": "LABEL",
  "params": {"add": ["Important"], "remove": ["Unread"]},
  "pre_state": {"labels": ["Unread", "INBOX"]}
}
```

### FLAG Action (read/unread, starred)
```json
{
  "action": "FLAG",
  "params": {"is_unread": false},
  "pre_state": {"is_unread": true}
}
```

### DELETE Action
```json
{
  "action": "DELETE",
  "params": {"permanent": false},
  "pre_state": {"folder": "INBOX"}
}
```

## Restore Flow

When user clicks "Undo" within the grace period:

1. Fetch mutation from journal by ID
2. Verify `status = 'COMPLETED'` and action is reversible
3. Create **new** mutation with inverse operation
4. Execute inverse on IMAP via Engine
5. Update both mutations to reflect restore

```python
def restore_mutation(mutation_id: int) -> bool:
    mutation = db.get_mutation(mutation_id)
    
    if mutation["action"] == "MOVE":
        original_folder = mutation["pre_state"]["folder"]
        return engine.move_email(
            mutation["email_uid"], 
            original_folder
        )
    
    if mutation["action"] == "FLAG":
        return engine.set_flags(
            mutation["email_uid"],
            mutation["pre_state"]
        )
    
    # ... etc
```

## Sync Engine Integration

The background sync must respect pending mutations to avoid clobbering optimistic updates:

```python
def sync_email(email_data: dict):
    pending = db.get_pending_mutations(email_data["uid"], email_data["folder"])
    
    if pending:
        # Skip this email - mutation in progress
        # It will be synced after mutation completes
        return
    
    # Safe to sync from IMAP
    db.upsert_email(email_data)
```

## API Endpoints

### POST /api/mutations/{id}/restore
Attempt to restore (reverse) a completed mutation.

**Response:**
```json
{
  "status": "success",
  "message": "Email moved back to INBOX",
  "reversible": true
}
```

Or for irreversible:
```json
{
  "status": "error", 
  "message": "Send actions cannot be reversed",
  "reversible": false
}
```

## Grace Period & Cleanup

- Mutations older than 30 days with `status='COMPLETED'` can be purged
- Failed mutations should be reviewed and manually resolved
- Pending mutations older than 1 hour indicate engine issues

## Limitations

1. **No true undo for sends**: Once SMTP delivers, it's gone
2. **Permanent deletes are permanent**: No recovery from "Empty Trash"
3. **UID changes**: If IMAP server reassigns UIDs, restore may fail
4. **Cross-folder moves**: Complex chains of moves may not restore cleanly
5. **Bulk operations**: Large batches may have partial failures

## Future Enhancements

- [ ] Toast notification with "Undo" button (5-second window)
- [ ] Mutation history view in Settings
- [ ] Automatic retry for transient engine failures
- [ ] Batch mutation grouping for bulk actions
