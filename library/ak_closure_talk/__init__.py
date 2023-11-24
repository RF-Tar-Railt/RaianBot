# async def render(self) -> bytes:
#     browser = Ariadne.launch_manager.get_interface(PlaywrightBrowser)
#     async with browser.page(
#             viewport={"width": 500, "height": 1},
#             device_scale_factor=1.5,
#     ) as page:
#         logger.info("[ClosureTalk] Setting content...")
#         await page.set_content(self.to_html())
#         logger.info("[ClosureTalk] Getting screenshot...")
#         img = await page.screenshot(
#             type="jpeg", quality=80, full_page=True, scale="device"
#         )
#         logger.success("[ClosureTalk] Done.")
#         return img
from .main import ArknightsClosureStore as ArknightsClosureStore
