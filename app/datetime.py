from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CHINA_TZ = ZoneInfo("Asia/Shanghai")
MONTHS_IN_YEAR = 12


def get_all_days_of_month(year: int, month: int) -> list[datetime]:
    start_date = datetime(year, month, 1, tzinfo=CHINA_TZ)
    end_date = (
        datetime(year, month + 1, 1, tzinfo=CHINA_TZ)
        if month < MONTHS_IN_YEAR
        else datetime(year + 1, 1, 1, tzinfo=CHINA_TZ)
    )

    return [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]
