"""DB에는 UTC로 저장하고, 화면에는 한국 시간(KST)으로 보여 준다."""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def utc_text_to_kst(created_at):
    """'2026-10-25 12:30:00' (UTC) → datetime (KST). 형식이 이상하면 None."""
    try:
        return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone(KST)
    except (TypeError, ValueError):
        return None


def kst_date_text(created_at):
    dt = utc_text_to_kst(created_at)
    return dt.strftime("%Y-%m-%d") if dt else "0000-00-00"


def today_kst_text():
    return datetime.now(KST).strftime("%Y-%m-%d")
