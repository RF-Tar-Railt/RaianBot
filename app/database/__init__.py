from __future__ import annotations

from .service import DatabaseService
from .model import Base, User, Group

def get_engine_url(
    type: str,
    name: str,
    driver: str = "aiosqlite",
    host: str | None = None,
    port: int = 3306,
    username: str | None = None,
    password: str | None = None,
    **kwargs: dict[str, str],
) -> str:
    """
    生成一个数据库链接，仅支持 mysql 或 sqlite

    Args:
        type (str): 数据库类型.
        name (str):
            MySQL/MariaDB 时为数据库名称
            SQLite 时则为数据库名称
        driver (str, optional): 数据库 Driver. 默认为 "aiosqlite".
            可用的 MySQL/MariaDB Driver 列表详见：https://docs.sqlalchemy.org/en/20/dialects/mysql.html#dialect-mysql
            可用的 SQLite Driver 列表详见：https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#dialect-sqlite
        host (str, optional): MySQL/MariaDB 服务器地址.
        port (int): MySQL/MariaDB 服务器端口. 默认为 3306.
        username (str, optional): MySQL/MariaDB 服务器用户名. 默认为 None.
        password (str, optional): MySQL/MariaDB 服务器密码. 默认为 None.
    """
    if type == "mysql":
        if host is None or username is None or password is None:
            raise ValueError("Option `username` or `passwd` or `database_name` must in parameter.")
        url = f"mysql+{driver}://{username}:{password}@{host}:{port}/{name}"
    elif type == "sqlite":
        url = f"sqlite+{driver}://{name}"
    else:
        raise ValueError("Unsupport database type, please creating URL manually.")
    kw = "".join(f"&{key}={value}" for key, value in kwargs.items()).lstrip("&")
    return f'{url}?{kw}' if kw else url
