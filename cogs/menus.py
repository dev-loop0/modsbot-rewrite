import asyncio

import discord
from discord.ext import commands

import asyncio
from enum import IntEnum

from cogs.proposals import Status, SortType


class PageType(IntEnum):
    TEXT = 0
    EMBED = 1


class MenuManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_menus = {}
        self.message_map = {}

    # Deletes menus after a certain time.
    async def delete_after(self, timeout: int, menu_id):
        await asyncio.sleep(timeout)
        if menu_id in self.active_menus:
            await self.active_menus[menu_id].remove()
            del self.active_menus[menu_id]

    async def new_menu(
        self,
        ctx: commands.Context,
        pages: list,
        cur_page: int = 0,
        timeout: int = 60,
        page_type: PageType = PageType.EMBED,
    ):
        menu = Menu(ctx, pages, cur_page=cur_page, timeout=timeout, page_type=page_type)
        await menu.open()
        self.active_menus[menu.message.id] = menu
        await self.delete_after(timeout, menu.message.id)

    async def new_filter_sort_menu(
        self,
        ctx: commands.Context,
        entries: list,
        cur_page: int = 0,
        timeout: int = 60,
        page_type: PageType = PageType.EMBED,
    ):
        menu = FilterSortMenu(
            ctx,
            entries,
            cur_page=cur_page,
            timeout=timeout,
            page_type=page_type,
        )
        await menu.open()
        self.active_menus[menu.message.id] = menu
        await self.delete_after(timeout, menu.message.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        cur_menu = self.active_menus[payload.message_id]

        message = cur_menu.message
        user = payload.member

        if payload.message_id in self.active_menus:
            if payload.emoji.name == "◀":
                await cur_menu.previous_page(payload.user_id)
            elif payload.emoji.name == "⏹":
                if cur_menu.owner == payload.user_id:
                    await self.delete_after(0, payload.message_id)
            elif payload.emoji.name == "▶":
                await cur_menu.next_page(payload.user_id)
            elif isinstance(self.active_menus[payload.message_id], FilterSortMenu):
                if payload.emoji.name == "🍋":
                    cur_menu.filter_n |= Status.PENDING
                    await cur_menu.update_sort_and_filter()
                elif payload.emoji.name == "🍏":
                    cur_menu.filter_n |= Status.ACCEPTED
                    await cur_menu.update_sort_and_filter()
                elif payload.emoji.name == "🍎":
                    cur_menu.filter_n |= Status.REJECTED
                    await cur_menu.update_sort_and_filter()
                elif payload.emoji.name == "🔢":
                    cur_menu.sort_n &= ~0x0F
                    cur_menu.sort_n |= SortType.NUMBER
                    await asyncio.gather(
                        cur_menu.update_sort_and_filter(),
                        message.remove_reaction("🔢", user),
                    )
                elif payload.emoji.name == "🔠":
                    cur_menu.sort_n &= ~0x0F
                    cur_menu.sort_n |= SortType.SOURCE
                    await asyncio.gather(
                        cur_menu.update_sort_and_filter(),
                        message.remove_reaction("🔠", user),
                    )
                elif payload.emoji.name == "⤴":
                    cur_menu.sort_n &= ~0x10
                    cur_menu.sort_n |= SortType.ASCENDING
                    await asyncio.gather(
                        cur_menu.update_sort_and_filter(),
                        message.remove_reaction("⤴", user),
                    )
                elif payload.emoji.name == "⤵":
                    cur_menu.sort_n &= ~0x10
                    cur_menu.sort_n |= SortType.DESCENDING
                    await asyncio.gather(
                        cur_menu.update_sort_and_filter(),
                        message.remove_reaction("⤵", user),
                    )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        cur_menu = self.active_menus[payload.message_id]

        if payload.message_id in self.active_menus:
            if payload.emoji.name == "◀":
                await cur_menu.previous_page(payload.user_id)
            elif payload.emoji.name == "⏹":
                if cur_menu.owner == payload.user_id:
                    await self.delete_after(0, payload.message_id)
            elif payload.emoji.name == "▶":
                await cur_menu.next_page(payload.user_id)
            if isinstance(cur_menu, FilterSortMenu):
                if payload.emoji.name == "🍋":
                    cur_menu.filter_n &= ~Status.PENDING
                    await cur_menu.update_sort_and_filter()
                elif payload.emoji.name == "🍏":
                    cur_menu.filter_n &= ~Status.ACCEPTED
                    await cur_menu.update_sort_and_filter()
                elif payload.emoji.name == "🍎":
                    cur_menu.filter_n &= ~Status.REJECTED
                    await cur_menu.update_sort_and_filter()


class Menu:
    def __init__(
        self,
        ctx: commands.Context,
        pages: list,
        cur_page: int = 0,
        timeout: int = 60,
        page_type: PageType = PageType.EMBED,
    ):
        assert pages
        self.ctx = ctx
        self.pages = pages
        self.message = None
        self.id = ctx.message.id
        self.cur_page = cur_page
        self.owner = ctx.author.id
        self.page_type = page_type

    async def open(self):
        if self.page_type == PageType.EMBED:
            self.message = await self.ctx.send(embed=self.pages[self.cur_page])
        elif self.page_type == PageType.TEXT:
            self.message = await self.ctx.send(content=self.pages[self.cur_page])
        await self.message.add_reaction("◀")
        await self.message.add_reaction("⏹")
        await self.message.add_reaction("▶")

    async def update(self):
        if self.page_type == PageType.EMBED:
            await self.message.edit(embed=self.pages[self.cur_page])
        elif self.page_type == PageType.TEXT:
            await self.message.edit(content=self.pages[self.cur_page])

    async def first_page(self):
        self.cur_page = 0
        await self.update()

    async def next_page(self, user_id):
        if self.cur_page < len(self.pages) - 1 and user_id == self.owner:
            self.cur_page += 1
            await self.update()

    async def previous_page(self, user_id):
        if self.cur_page > 0 and user_id == self.owner:
            self.cur_page -= 1
            await self.update()

    async def remove(self):
        try:
            await self.message.clear_reactions()
        except discord.Forbidden:
            await self.message.remove_reaction("◀", self.ctx.me)
            await self.message.remove_reaction("⏹", self.ctx.me)
            await self.message.remove_reaction("▶", self.ctx.me)


class FilterSortMenu(Menu):
    def __init__(
        self,
        ctx: commands.Context,
        entries: list,
        cur_page: int = 0,
        timeout: int = 60,
        page_type: PageType = PageType.EMBED,
    ):
        self.entries = entries
        self.filtered_entries = entries.copy()
        self.filter_n = 0
        self.sort_n = 0

        self.process_entries()

        super().__init__(
            ctx, self.pages, cur_page=cur_page, timeout=timeout, page_type=page_type
        )

    def process_entries(self):
        lines = [" · ".join(i.prettify()) for i in self.filtered_entries]
        batches = [lines[i : i + 25] for i in range(0, len(lines), 25)]
        batches = ["```ansi\n" + "\n".join(i) for i in batches]

        length = len(batches)
        if length >= 2:
            for i in range(length):
                batches[i] = (
                    batches[i] + f"\n\x1b[2;30mPage {i + 1}/{length}\x1b[0m\n```"
                )
        else:
            batches[0] = batches[0] + "\n```"

        batches[0] = "# __Your proposals__\n" + batches[0]
        self.pages = batches

    async def open(self):
        await super().open()
        await self.message.add_reaction("🍋")
        await self.message.add_reaction("🍏")
        await self.message.add_reaction("🍎")
        await self.message.add_reaction("🔢")
        await self.message.add_reaction("🔠")
        await self.message.add_reaction("⤴")
        await self.message.add_reaction("⤵")

    async def update_sort_and_filter(self):
        if not self.filter_n:
            self.filtered_entries = self.entries
        else:
            self.filtered_entries = list(
                filter(lambda x: x.status & self.filter_n, self.entries)
            )

        if self.sort_n & 0x0F == SortType.NUMBER:
            self.filtered_entries.sort(key=lambda x: x.number)
        elif self.sort_n & 0x0F == SortType.SOURCE:
            self.filtered_entries.sort(key=lambda x: x.source)
        if self.sort_n & 0x10 == SortType.DESCENDING:
            self.filtered_entries.reverse()

        self.process_entries()
        await super().first_page()


async def setup(bot):
    await bot.add_cog(MenuManager(bot))
