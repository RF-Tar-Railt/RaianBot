import re
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Union

from graiax.text2img.playwright import HTMLRenderer, MarkdownConverter, PageOption, ScreenshotOption, convert_text
from graiax.text2img.playwright.renderer import BuiltinCSS
from PIL import Image
from playwright.async_api import Request, Route
from qrcode import QRCode
from qrcode.image.styledpil import StyledPilImage
from yarl import URL

from .datetime import CHINA_TZ

if TYPE_CHECKING:
    from .config import RaianConfig


font_path = Path(__file__).parent.parent / "assets" / "fonts"
image_path = Path(__file__).parent.parent / "assets" / "image"

font_mime_map = {
    "collection": "font/collection",
    "otf": "font/otf",
    "sfnt": "font/sfnt",
    "ttf": "font/ttf",
    "woff": "font/woff",
    "woff2": "font/woff2",
}

guild_b64: Union[str, None] = None
group_b64: Union[str, None] = None


def setup_qrcode(config: "RaianConfig"):
    global guild_b64, group_b64
    for bot in config.bots:
        if bot.type == "qqapi":
            qrcode = QRCode(image_factory=StyledPilImage)
            qrcode.add_data(f"https://qun.qq.com/qunpro/robot/share?robot_appid={bot.account}")
            invite_guild: Image.Image = (
                qrcode.make_image(fill_color="black", back_color="#fafafac0").get_image().resize((200, 200))
            )
            bio = BytesIO()
            invite_guild.save(bio, format="PNG")
            guild_b64 = b64encode(bio.getvalue()).decode()

            qrcode.clear()
            qrcode.add_data(f"https://qun.qq.com/qunpro/robot/qunshare?robot_appid={bot.account}")
            invite_group: Image.Image = (
                qrcode.make_image(fill_color="black", back_color="#fafafac0").get_image().resize((200, 200))
            )
            bio = BytesIO()
            invite_group.save(bio, format="PNG")
            group_b64 = b64encode(bio.getvalue()).decode()
            break


async def fill_font(route: Route, request: Request):
    url = URL(request.url)
    if (font_path / url.name).exists():
        await route.fulfill(
            path=font_path / url.name,
            content_type=font_mime_map.get(url.suffix),
        )
        return
    await route.fallback()


def footer():
    qr = f"""
                <div class="qrcode-area">
                    <img class="qrcode" src="data:image/png;base64,{group_b64}" />
                    <img class="qrcode" src="data:image/png;base64,{guild_b64}" />
                </div>
                <div class="qrcode-text">
                    <p>扫描二维码将 RaianBot 添加至你的群聊/频道</p>
                </div>
    """
    return f"""
    <style>
        .footer{{
            box-sizing:border-box;
            background:#eee;
            padding:30px 40px;
            margin-top:50px;
            font-size:1rem;
        }}
        .footer p{{margin:5px auto;}}
    </style>
    <div style="position:absolute;left:0;width:100%;color:#6b6b6b;">
        <div class="footer">
            <section class="left">
                <div class="footer-text">
                    <p style="font-weight: bold">该图片由 RaianBot 生成</p>
                    <p style="font-size: 14px">{datetime.now(CHINA_TZ).strftime("%Y/%m/%d %p %I:%M:%S")}</p>
                </div>
            </section>
            <section class="right">{qr if guild_b64 and group_b64 else ""}
            </section>
        </div>
        <section class="powered">Powered by Avilla</section>
    </div>
    """


html_render = HTMLRenderer(
    page_option=PageOption(device_scale_factor=1.5),
    screenshot_option=ScreenshotOption(type="jpeg", quality=80, full_page=True, scale="device"),
    css=(
        BuiltinCSS.reset,
        BuiltinCSS.github,
        BuiltinCSS.one_dark,
        BuiltinCSS.container,
        # "@font-face{font-family:'harmo';font-weight:300;"
        # "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Light.ttf') format('truetype');}"
        # "@font-face{font-family:'harmo';font-weight:400;"
        # "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Regular.ttf') format('truetype');}"
        # "@font-face{font-family:'harmo';font-weight:500;"
        # "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Medium.ttf') format('truetype');}"
        # "@font-face{font-family:'harmo';font-weight:600;"
        # "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Bold.ttf') format('truetype');}"
        # "*{font-family:'harmo',sans-serif}",
        # "body{background-color:#fafafac0;}",
        "@media(prefers-color-scheme:light){.markdown-body{--color-canvas-default:#fafafac0;}}",
    ),
    page_modifiers=[
        lambda page: page.route(lambda url: bool(re.match("^http://static.graiax/fonts/(.+)$", url)), fill_font)
    ],
)

md_converter = MarkdownConverter()


async def text2img(text: str, width: int = 800) -> bytes:
    html = convert_text(text)
    html += footer()

    return await html_render.render(
        html,
        extra_page_option=PageOption(viewport={"width": width, "height": 10}),
    )


async def md2img(text: str, width: int = 800) -> bytes:
    html = md_converter.convert(text)
    html += footer()

    return await html_render.render(
        html,
        extra_page_option=PageOption(viewport={"width": width, "height": 10}),
    )
