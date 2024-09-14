import asyncio

from arclet.alconna.avilla import startswith
from avilla.core import Context, MessageChain, MessageReceived, Picture, RawResource
from graia.saya.builtins.broadcast.shortcut import listen

from app.image import md2img
from app.shortcut import accessable, exclusive, permission


@listen(MessageReceived)
@permission("master")
@startswith("shell", bind="echos")
@exclusive
@accessable
async def shell(ctx: Context, echos: MessageChain):
    process = await asyncio.create_subprocess_shell(
        str(echos),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
    if stdout:
        try:
            res = stdout.decode("utf-8").strip()
        except UnicodeDecodeError:
            res = stdout.decode("gbk").strip()
    elif stderr:
        try:
            res = stderr.decode("utf-8").strip()
        except UnicodeDecodeError:
            res = stderr.decode("gbk").strip()
    else:
        res = "No output"
    md = f"""\
> exit code: {process.returncode}

```sh
{res}
```
"""
    return await ctx.scene.send_message(
        Picture(RawResource(await md2img(md, max(max(len(i.strip()) for i in md.splitlines()) * 14, 240))))
    )
