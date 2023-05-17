"""从 prts 查询并截图"""
from functools import partial

import playwright.async_api
from typing import Optional
import re

url = "https://prts.wiki/w/%s"
m_url = "https://m.prts.wiki/w/%s"

__all__ = [
    "handle",
    "query",
    "full_page",
    "information",
    "talent",
    "feature",
    "document",
    "upgrade",
    "latent",
    "skills",
    "skill_at",
    "logistics",
    "attributes",
    "attack_range",
    "material",
]


async def full_page(page: playwright.async_api.Page, name: str):
    """全身图"""
    await page.click("html")
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.locator('span[role="button"]:has-text("技能")').first.click()
    await page.wait_for_timeout(2000)
    await page.locator('span[role="button"]:has-text("技能")').first.click()
    await page.locator('span[role="button"]:has-text("精英化材料")').click()
    await page.wait_for_timeout(1000)
    await page.locator('span[role="button"]:has-text("精英化材料")').click()
    await page.locator('span[role="button"]:has-text("相关道具")').click()
    await page.wait_for_timeout(1000)
    await page.locator('span[role="button"]:has-text("相关道具")').click()
    await page.locator('span[role="button"]:has-text("干员档案")').click()
    await page.wait_for_timeout(1000)
    return await page.screenshot(full_page=True)


async def information(page: playwright.async_api.Page, name: str, upgraded: bool = False):
    await page.goto(url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    but = page.locator("text=ELITE2精英二 >> img")
    if (await but.count()) and upgraded:
        await but.first.click()
        await page.locator("text=个人工具 中文（中国大陆）‎创建账号登录 命名空间 页面讨论 变体 查看 阅读查看源代码查看历史 更多 搜索 搜索 前往").click()
    elem = page.locator("#charimg-mask")
    bounding = await elem.bounding_box()
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def feature(page: playwright.async_api.Page, name: str):
    await page.goto(url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("特性")')
    elem = page.locator('table:has-text("分支 描述")')
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding["height"] += bounding1["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def attributes(page: playwright.async_api.Page, name: str):
    await page.goto(url % name, timeout=600000, wait_until="domcontentloaded")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("属性")')
    elem = page.locator("//table[@class='wikitable logo char-extra-attr-table']")
    elem1 = page.locator("//table[@class='wikitable logo char-base-attr-table']")
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding2 = await elem1.bounding_box()
    bounding["height"] += bounding1["height"] + 14
    bounding["height"] += bounding2["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def attack_range(page: playwright.async_api.Page, name: str):
    await page.goto(url % name, timeout=600000, wait_until="domcontentloaded")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("攻击范围")')
    elem = page.locator('table:has-text("精英0 精英1 精英2")').first
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding["height"] += bounding1["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def talent(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="domcontentloaded")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("天赋")')
    block = page.locator("//section[@class='mf-section-6 collapsible-block open-block']")
    elem = block.locator("//table[@class='wikitable logo']").first
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding2 = await block.bounding_box()
    bounding["height"] += bounding2["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def latent(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="domcontentloaded")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("潜能提升")')
    block = page.locator("//section[@id='content-collapsible-block-6']")
    elem = block.locator("//table[@class='wikitable nodesktop logo']").first
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding2 = await block.bounding_box()
    bounding["height"] += bounding2["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def skills(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("技能")').first
    block = page.locator("//section[@id='content-collapsible-block-7']")
    if not (await block.locator("//table[@class='wikitable nodesktop logo']").count()):
        bounding = await title.bounding_box()
        bounding1 = await block.bounding_box()
        bounding["height"] += bounding1["height"] + 14
    else:
        elem = block.locator("//table[@class='wikitable nodesktop logo']").first
        await elem.click()
        await page.wait_for_timeout(100)
        await page.click('[aria-label="用户导航"]')
        bounding = await title.bounding_box()
        bounding1 = await elem.bounding_box()
        bounding2 = await block.bounding_box()
        bounding["height"] += bounding2["height"] + 14
        bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def skill_at(page: playwright.async_api.Page, name: str, index: int = 0):
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    block = page.locator("//section[@id='content-collapsible-block-7']")
    skill = block.locator("//table[@class='wikitable nodesktop logo']")
    count = await skill.count()
    if not count or index > count:
        title = page.locator('h2:has-text("技能")').first
        bounding = await title.bounding_box()
        bounding1 = await block.bounding_box()
        bounding["height"] += bounding1["height"] + 14
        return [await page.screenshot(full_page=True, clip=bounding, scale="device")]
    res = []
    for i in range(count):
        await skill.nth(i).click()
        await page.wait_for_timeout(500)
        await page.click('[aria-label="用户导航"]')
        bounding = await skill.nth(i).bounding_box()
        res.append(await page.screenshot(full_page=True, clip=bounding, scale="device"))
    return res if count < 1 else res[count - 1 : count]


async def logistics(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("后勤技能")').first
    block = page.locator("//section[@id='content-collapsible-block-8']")
    elem = block.locator("//table[@class='wikitable logo']").first
    await elem.click()
    await page.wait_for_timeout(1000)
    await page.click('[aria-label="用户导航"]')
    bounding = await title.bounding_box()
    bounding1 = await elem.bounding_box()
    bounding2 = await block.bounding_box()
    bounding["height"] += bounding2["height"] + 28
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def upgrade(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("精英化材料")').first
    if await page.locator('h2:has-text("召唤物信息")').count():
        block = page.locator("//section[@id='content-collapsible-block-10']")
    else:
        block = page.locator("//section[@id='content-collapsible-block-9']")
    if not (await block.locator("//table[@class='wikitable logo']").count()):
        bounding = await title.bounding_box()
        bounding1 = await block.bounding_box()
        bounding["height"] += bounding1["height"] + 14
    else:
        elem = block.locator("//table[@class='wikitable logo']").first
        await elem.click()
        await page.wait_for_timeout(1000)
        await page.click('[aria-label="用户导航"]')
        bounding = await title.bounding_box()
        bounding1 = await elem.bounding_box()
        bounding2 = await block.bounding_box()
        bounding["height"] += bounding2["height"] + 28
        bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def material(page: playwright.async_api.Page, name: str):
    await page.goto(url % name, timeout=600000, wait_until="load")
    await page.wait_for_timeout(100)
    title = page.locator('h2:has-text("技能升级材料")')
    elem = page.locator('table:has-text("技能升级 1→2")')
    bounding = await title.bounding_box()
    if not (await elem.count()):
        bounding1 = await page.locator("text=该干员没有技能").nth(1).bounding_box()
    else:
        await title.click()
        await page.wait_for_timeout(2000)
        await page.click(f'h1:has-text("{name}")')
        bounding1 = await elem.first.bounding_box()
    bounding["height"] += bounding1["height"] + 14
    bounding["width"] = bounding1["width"]
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


async def document(page: playwright.async_api.Page, name: str):
    await page.goto(m_url % name, timeout=600000, wait_until="load")
    await page.locator('span[role="button"]:has-text("展开")').first.click()
    await page.click('[aria-label="用户导航"]')
    elem = page.locator("//table[@class='wikitable mw-collapsible logo mw-made-collapsible']")
    bounding = await elem.bounding_box()
    return await page.screenshot(full_page=True, clip=bounding, scale="device")


_table = {
    "总览": full_page,
    "((干员)?信息|展示)": information,
    "(模板|职业)?特性": feature,
    "属性": attributes,
    "攻击范围": attack_range,
    "天赋": talent,
    "潜能(提升)?": latent,
    "技能(信息)?": skills,
    "后勤技能": logistics,
    "精二": partial(information, upgraded=True),
    "精英化(材料)?": upgrade,
    "(升级|技能升级材料)": material,
    "(.*?)专(一|二|三|精)(材料)?": material,
    "档案": document
}


def handle(content: Optional[str] = None):
    if not content:
        return full_page
    for pat, func in _table.items():
        if re.fullmatch(pat, content):
            return func
    return full_page


async def query(
    name: str,
    content: Optional[str] = None,
    page: Optional[playwright.async_api.Page] = None,
):
    if not page:
        async with playwright.async_api.async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, channel="msedge")
            context = await browser.new_context(viewport={"width": 1440, "height": 960})
            page = await context.new_page()

            func = handle(content)
            try:
                data = await func(page, name)
            except playwright.async_api.TimeoutError:
                data = await full_page(page, name)
            finally:
                await page.close()
                await context.close()
                await browser.close()
            return data
    func = handle(content)
    try:
        return await func(page, name)
    except playwright.async_api.TimeoutError:
        return await full_page(page, name)


if __name__ == "__main__":
    import asyncio

    async def main():
        data = await query("艾雅法拉", "档案")
        with open("temp.png", "wb+") as f:
            f.write(data)

    asyncio.run(main())
