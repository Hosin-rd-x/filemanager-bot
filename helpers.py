import uuid
import hashlib
from datetime import datetime, timedelta


def generate_id(length: int = 8) -> str:
    """Generate a short unique ID."""
    return uuid.uuid4().hex[:length].upper()


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.1f} GB"


def calc_expires_at(expire_seconds: int) -> str:
    """Return ISO datetime string for expiry, or empty string if no expiry."""
    if expire_seconds <= 0:
        return ""
    return (datetime.utcnow() + timedelta(seconds=expire_seconds)).strftime("%Y-%m-%d %H:%M:%S")


def is_expired(expires_at: str) -> bool:
    """Return True if the file/folder has expired."""
    if not expires_at:
        return False
    try:
        exp = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        return datetime.utcnow() > exp
    except Exception:
        return False


def seconds_to_human(seconds: int) -> str:
    """Convert seconds to human-readable duration."""
    if seconds <= 0:
        return "بدون محدودیت"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:    parts.append(f"{days} روز")
    if hours:   parts.append(f"{hours} ساعت")
    if minutes: parts.append(f"{minutes} دقیقه")
    if secs:    parts.append(f"{secs} ثانیه")
    return " و ".join(parts)


def file_type_emoji(file_type: str) -> str:
    """Return emoji for file type."""
    return {
        "document": "📄",
        "video":    "🎬",
        "audio":    "🎵",
        "photo":    "🖼",
        "voice":    "🎤",
        "animation":"🎞",
        "sticker":  "🎭",
    }.get(file_type, "📁")


def parse_expire_input(text: str) -> int:
    """
    Parse user input like '1d', '2h', '30m', '60s', '0' into seconds.
    Returns 0 for no expiry, -1 on error.
    """
    text = text.strip().lower()
    if text in ("0", "no", "none", "هیچ", "-"):
        return 0
    multipliers = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    if text[-1] in multipliers:
        try:
            return int(text[:-1]) * multipliers[text[-1]]
        except ValueError:
            return -1
    try:
        return int(text)
    except ValueError:
        return -1
