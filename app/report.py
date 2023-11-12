import traceback
from io import StringIO
from graia.broadcast.builtin.event import ExceptionThrown
from .image import md2img


async def generate_report(event: ExceptionThrown):
    with StringIO() as fp:
        traceback.print_tb(event.exception.__traceback__, file=fp)
        tb = fp.getvalue()
    msg = f'''\
## 异常事件：

`{str(event.event.__repr__())}`

## 异常类型：

`{type(event.exception)}`

## 异常内容：

{str(event.exception)}

## 异常追踪：

```py
{tb}
```
'''
    return await md2img(msg, 1500)
