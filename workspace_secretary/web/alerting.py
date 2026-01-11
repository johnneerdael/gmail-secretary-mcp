from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from typing import Optional
import logging

from workspace_secretary.config import load_config
from workspace_secretary.smtp_client import SMTPClient

logger = logging.getLogger(__name__)

_last_alert_time: Optional[datetime] = None
_config_cache: Optional[dict] = None


def _get_raw_config() -> dict:
    global _config_cache
    if _config_cache is None:
        import yaml
        from pathlib import Path

        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                _config_cache = yaml.safe_load(f) or {}
        else:
            _config_cache = {}
    return _config_cache or {}


def _get_alerting_config() -> Optional[dict]:
    config = _get_raw_config()
    alerting = config.get("alerting", {})
    if not alerting.get("enabled", False):
        return None
    if not alerting.get("recipient"):
        return None
    return alerting


def _can_send_alert(cooldown_minutes: int) -> bool:
    global _last_alert_time
    if _last_alert_time is None:
        return True
    now = datetime.now(timezone.utc)
    return (now - _last_alert_time) > timedelta(minutes=cooldown_minutes)


def _record_alert_sent():
    global _last_alert_time
    _last_alert_time = datetime.now(timezone.utc)


def send_critical_alert(subject: str, body: str) -> bool:
    alerting = _get_alerting_config()
    if not alerting:
        logger.debug("Alerting not configured or disabled")
        return False

    cooldown = alerting.get("cooldown_minutes", 60)
    if not _can_send_alert(cooldown):
        logger.debug(f"Alert suppressed due to cooldown ({cooldown}m)")
        return False

    recipient = alerting["recipient"]
    raw_config = _get_raw_config()
    sender = raw_config.get("identity", {}).get("email", "secretary@localhost")

    msg = EmailMessage()
    msg["Subject"] = f"[Secretary Alert] {subject}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    try:
        config = load_config()
        smtp_client = SMTPClient(config)
        smtp_client.send_message(msg)
        _record_alert_sent()
        logger.info(f"Critical alert sent to {recipient}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def check_and_alert(mutation_stats: dict, sync_stats: dict) -> list[str]:
    alerts_sent = []

    if mutation_stats.get("stuck", 0) > 0:
        subject = f"{mutation_stats['stuck']} Stuck Mutation(s)"
        body = f"""Critical: {mutation_stats["stuck"]} mutation(s) have been pending for over 1 hour.

This indicates the Engine may be offline or unable to process IMAP commands.

Actions:
- Check Engine service status
- Review mutation journal at /admin
- Verify IMAP connectivity

Pending: {mutation_stats["pending"]}
Failed (24h): {mutation_stats["failed_24h"]}
"""
        if send_critical_alert(subject, body):
            alerts_sent.append("stuck_mutations")

    if sync_stats.get("sync_age_minutes") and sync_stats["sync_age_minutes"] > 30:
        subject = f"Sync Stale ({sync_stats['sync_age_minutes']}m)"
        body = f"""Critical: Last successful sync was {sync_stats["sync_age_minutes"]} minutes ago.

This indicates the sync engine may be offline or experiencing errors.

Actions:
- Check Engine service status
- Review sync errors at /admin
- Verify IMAP connectivity

Last sync folder: {sync_stats.get("last_sync_folder", "Unknown")}
Unresolved errors: {sync_stats.get("unresolved_errors", 0)}
"""
        if send_critical_alert(subject, body):
            alerts_sent.append("sync_stale")

    return alerts_sent
