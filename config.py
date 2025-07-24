from datetime import timezone, timedelta

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=3))

ADMIN_IDS = [5669245603, 551125461, 655805086]
