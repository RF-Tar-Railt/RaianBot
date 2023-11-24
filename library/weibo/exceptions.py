class WeiboError(Exception):
    """Base class for weibo errors"""

    pass


class RespStatusError(WeiboError):
    """Response status code is not 200"""

    pass


class RespDataError(WeiboError):
    """Response data is not ok"""

    pass


class RespDataErrnoError(WeiboError):
    """Response data errno is not 0"""

    pass
