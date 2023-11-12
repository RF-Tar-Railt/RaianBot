import re
from datetime import datetime

from graiax.text2img.playwright import (
    HTMLRenderer,
    MarkdownConverter,
    PageOption,
    ScreenshotOption,
    convert_text,
)
from graiax.text2img.playwright.renderer import BuiltinCSS

from playwright.async_api import Request, Route
from yarl import URL
from pathlib import Path

font_path = Path(__file__).parent.parent / "assets" / 'fonts'

font_mime_map = {
    'collection': 'font/collection',
    'otf': 'font/otf',
    'sfnt': 'font/sfnt',
    'ttf': 'font/ttf',
    'woff': 'font/woff',
    'woff2': 'font/woff2',
}


async def fill_font(route: Route, request: Request):
    url = URL(request.url)
    if (font_path / url.name).exists():
        await route.fulfill(
            path=font_path / url.name,
            content_type=font_mime_map.get(url.suffix),
        )
        return
    await route.fallback()


footer = (
    '<style>.footer{box-sizing:border-box;position:absolute;left:0;width:100%;background:#eee;'
    'padding:30px 40px;margin-top:50px;font-size:1rem;color:#6b6b6b;}'
    '.footer p{margin:5px auto;}</style>'
    f'<div class="footer"><p>由 RaianBot 生成</p><p>{datetime.now().strftime("%Y/%m/%d %p %I:%M:%S")}</p></div>'
)

html_render = HTMLRenderer(
    page_option=PageOption(device_scale_factor=1.5),
    screenshot_option=ScreenshotOption(type='jpeg', quality=80, full_page=True, scale='device'),
    css=(
        BuiltinCSS.reset,
        BuiltinCSS.github,
        BuiltinCSS.one_dark,
        BuiltinCSS.container,
        "@font-face{font-family:'harmo';font-weight:300;"
        "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Light.ttf') format('truetype');}"
        "@font-face{font-family:'harmo';font-weight:400;"
        "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Regular.ttf') format('truetype');}"
        "@font-face{font-family:'harmo';font-weight:500;"
        "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Medium.ttf') format('truetype');}"
        "@font-face{font-family:'harmo';font-weight:600;"
        "src:url('http://static.graiax/fonts/HarmonyOS_Sans_SC_Bold.ttf') format('truetype');}"
        "*{font-family:'harmo',sans-serif}",
    ),
    page_modifiers=[
        lambda page: page.route(lambda url: bool(re.match('^http://static.graiax/fonts/(.+)$', url)), fill_font)
    ],
)

md_converter = MarkdownConverter()


async def text2img(text: str, width: int = 800) -> bytes:
    html = convert_text(text)
    html += footer

    return await html_render.render(
        html,
        extra_page_option=PageOption(viewport={'width': width, 'height': 10}),
    )


async def md2img(text: str, width: int = 800) -> bytes:
    html = md_converter.convert(text)
    html += footer

    return await html_render.render(
        html,
        extra_page_option=PageOption(viewport={'width': width, 'height': 10}),
    )
