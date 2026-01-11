# Backend Gap Analysis: "Secretary" UI Integration

This document outlines the missing backend functionality required to support the new frontend iterations (`settings_1.html`, `mobile_optimized_1.html`, `security_sync_1.html`).

## 1. Settings & Persistence Layer
The current `settings.py` routes are GET-only. We need to implement write capability and a persistence layer for UI-specific preferences.

### Required Endpoints
- **`POST /api/settings/identity`**: Save user name, email, and signature.
- **`POST /api/settings/ai`**: Save LLM provider, model, and prompt templates.
- **`PUT /api/settings/ui`**: Persist `theme` (dark/light/system) and `density` (compact/default/relaxed).
  - *Note*: These should likely be stored in a new `user_preferences` table or the existing `config.yaml` if simple enough.

### Gap in `config.py`
- Implementation of a `save_config()` method in `workspace_secretary/config.py` to write `ServerConfig` changes back to disk.

---

## 2. Security & Phishing Detection
The frontend includes high-visibility security banners, but the backend lacks the detection logic and standard web protections.

### CSRF Protection
- **Middleware**: Implement `fastapi-csrf` or custom middleware in `workspace_secretary/web/__init__.py`.
- **Templates**: Ensure `csrf_token` is injected into all forms and handled by HTMX (`hx-headers`).

### Phishing Detection (Analysis Engine)
- **Engine Logic**: Update `workspace_secretary/engine/api.py` or a specialized service to perform SPF/DKIM/DMARC checks on incoming mail.
- **Signals**: Add a `is_phishing` or `security_score` signal to the `emails` table/API response.
- **Alerting**: The UI expects a `warning_type` (e.g., `sender_mismatch`, `unverified_domain`) to display specific banners.

---

## 3. Sync Status & Activity Log API
The UI now features a pulsing sync indicator and an "Activity Log" modal.

### Sync Polling
- **`GET /api/sync/status`**: A lightweight JSON endpoint that returns:
  ```json
  {
    "is_syncing": true,
    "last_sync": "2026-01-11T10:00:00Z",
    "progress": 85,
    "current_folder": "INBOX"
  }
  ```
- *Implementation Note*: The engine already has `get_sync_stats` in `admin.py`, but it needs to be exposed as a public API.

### Activity Log (Audit)
- **`GET /api/activity/log`**: Expose the `mutation_journal` table from the database.
- **Format**: Return the last 50 actions (UID, Folder, Action, Status, Timestamp) to populate the audit log UI.

---

## 4. Enhanced Action Workflows
Support for mobile swipe gestures and "Smart Archive" logic.

### Archive Route
- **`POST /actions/archive/{folder}/{uid}`**: A dedicated route that moves items to the "Archive" folder (detecting the correct IMAP path like `[Gmail]/All Mail`).
- *Current workaround*: UI uses generic `move`, but a dedicated `archive` endpoint ensures consistent "Smart Archive" logic across all clients.

### Permanent Deletion
- **`DELETE /actions/delete-permanent/{folder}/{uid}`**: For items already in Trash, skip the bin and execute an IMAP `EXPUNGE`.
- **Confirmation**: Implement a `confirmed=true` query parameter for these destructive actions.

---

## 5. Backend Engineering Tasks Summary
| Priority | Task | Target File |
| :--- | :--- | :--- |
| **Critical** | Implement CSRF Middleware | `web/__init__.py` |
| **High** | POST routes for Settings | `web/routes/settings.py` |
| **High** | Sync Status JSON API | `web/routes/notifications.py` |
| **Medium** | Phishing Detection Logic | `engine/analysis.py` |
| **Medium** | Activity Log API | `web/routes/admin.py` |
| **Low** | Config Persistence (`save_config`) | `config.py` |

---

## 6. Immediate Technical Debt (Diagnostics)
During investigation, the following critical bugs were identified via language server diagnostics and must be resolved to ensure the backend is functional:

- **Missing Dependencies**: `auth.py` lacks `argon2` and `bcrypt` in the environment, causing auth failures.
- **Broken References**: `thread.py` references `get_engine_url` which is undefined.
- **Null Pointer Risks**: `database.py` and `admin.py` assume `config.database.postgres` is always present, leading to crashes if config is partial.
- **SQL Safety**: `database.py` uses type-unsafe string templates for queries in several places (`execute(sql, ...)` where `sql` is a dynamic string).

