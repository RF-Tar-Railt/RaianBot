from datetime import datetime, timedelta

import humanize


def relative_time(time: datetime) -> timedelta:
    return datetime.now().astimezone() - time.astimezone()


def humanize_date(time: datetime) -> str:
    return humanize.naturaldate(time.astimezone())


def humanize_delta(delta: timedelta) -> str:
    return humanize.precisedelta(delta, minimum_unit="minutes")
