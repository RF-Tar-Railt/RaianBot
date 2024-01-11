from dataclasses import dataclass, field
from datetime import datetime

from matplotlib import pyplot as plt
from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base, DatabaseService, Group, User


@dataclass
class Statistic:
    name: str
    group_id: str
    user_id: str
    time: datetime = field(default_factory=datetime.now)


class StatisticTable(Base):
    __tablename__ = "statistic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    """统计名称"""

    group_id: Mapped[str] = mapped_column(ForeignKey(Group.id), nullable=False)
    """群组 ID"""

    user_id: Mapped[str] = mapped_column(ForeignKey(User.id), nullable=False)
    """用户 ID"""

    time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    """统计时间"""


async def commit(db: DatabaseService, statistic: Statistic):
    async with db.get_session() as session:
        session.add(
            StatisticTable(
                name=statistic.name, group_id=statistic.group_id, user_id=statistic.user_id, time=statistic.time
            )
        )
        await session.commit()


# function usage statistics within a period of time
async def usage_statistics(db: DatabaseService, start_time: datetime, end_time: datetime) -> list[str]:
    async with db.get_session() as session:
        query = select(StatisticTable).where(StatisticTable.time >= start_time).where(StatisticTable.time <= end_time)
        return [statistic.name for statistic in await session.scalars(query)]


# function usage statistics about a group within a period of time
async def group_usage_statistics(
    db: DatabaseService, group_id: str, start_time: datetime, end_time: datetime
) -> list[str]:
    async with db.get_session() as session:
        query = (
            select(StatisticTable)
            .where(StatisticTable.group_id == group_id)
            .where(StatisticTable.time >= start_time)
            .where(StatisticTable.time <= end_time)
        )
        return [statistic.name for statistic in await session.scalars(query)]


# function usage statistics about a user within a period of time
async def user_usage_statistics(
    db: DatabaseService, user_id: str, start_time: datetime, end_time: datetime
) -> list[str]:
    async with db.get_session() as session:
        query = (
            select(StatisticTable)
            .where(StatisticTable.user_id == user_id)
            .where(StatisticTable.time >= start_time)
            .where(StatisticTable.time <= end_time)
        )
        return [statistic.name for statistic in await session.scalars(query)]


# draw a bar chart about function usage statistics within a period of time
async def draw_usage_statistics(
    db: DatabaseService, start_time: datetime, end_time: datetime, filename: str = "usage_statistics.png"
):
    names = await usage_statistics(db, start_time, end_time)
    names_set = list(set(names))
    names_count = [names.count(name) for name in names_set]
    plt.bar(names_set, names_count)
    plt.savefig(filename)
    plt.close()


# draw a bar chart about function usage statistics about a group within a period of time
async def draw_group_usage_statistics(
    db: DatabaseService,
    group_id: str,
    start_time: datetime,
    end_time: datetime,
    filename: str = "group_usage_statistics.png",
):
    names = await group_usage_statistics(db, group_id, start_time, end_time)
    names_set = list(set(names))
    names_count = [names.count(name) for name in names_set]
    plt.bar(names_set, names_count)
    plt.savefig(filename)
    plt.close()


# draw a bar chart about function usage statistics about a user within a period of time


async def draw_user_usage_statistics(
    db: DatabaseService,
    user_id: str,
    start_time: datetime,
    end_time: datetime,
    filename: str = "user_usage_statistics.png",
):
    names = await user_usage_statistics(db, user_id, start_time, end_time)
    names_set = list(set(names))
    names_count = [names.count(name) for name in names_set]
    plt.bar(names_set, names_count)
    plt.savefig(filename)
    plt.close()
