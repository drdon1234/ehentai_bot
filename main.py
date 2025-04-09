from pkg.platform.types import MessageChain
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived
from plugins.ehentai_bot.utils.config_manager import load_config
from plugins.ehentai_bot.utils.downloader import Downloader
from plugins.ehentai_bot.utils.html_parser import HTMLParser
from plugins.ehentai_bot.utils.message_adapter import MessageAdapter
from pathlib import Path
import os
import re
import aiohttp
import glob
import logging
import json
from typing import List

logger = logging.getLogger(__name__)


@register(name="ehentai_bot", description="适配 LangBot 的 EHentai画廊 转 PDF 插件", version="2.2", author="drdon1234")
class EHentaiBot(BasePlugin):
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.config = load_config()
        self.parser = HTMLParser()
        self.uploader = MessageAdapter(self.config)
        self.downloader = Downloader(self.config, self.uploader, self.parser)

    async def initialize(self):
        pass

    def __del__(self):
        pass

    @handler(PersonNormalMessageReceived)
    @handler(GroupNormalMessageReceived)
    async def message_received(self, ctx: EventContext):
        receive_text = ctx.event.text_message
        cleaned_text = re.sub(r'@\S+\s*', '', receive_text).strip()
        prevent_default = True

        if cleaned_text.startswith('搜eh'):
            await self.search_gallery(ctx, cleaned_text)
        elif cleaned_text.startswith('看eh'):
            await self.download_gallery(ctx, cleaned_text)
        elif cleaned_text.startswith('eh'):
            await self.eh_helper(ctx)
        elif cleaned_text.startswith('重载eh配置'):
            await self.reload_config(ctx)
        else:
            prevent_default = False

        if prevent_default:
            ctx.prevent_default()

    @staticmethod
    def parse_command(message: str) -> List[str]:
        return [p for p in message.split(' ') if p][1:]

    async def search_gallery(self, ctx: EventContext, cleaned_text: str):

        defaults = {
            "min_rating": 2,
            "min_pages": 1,
            "target_page": 1
        }

        try:
            args = self.parse_command(cleaned_text)
            if not args:
                await self.eh_helper(ctx)
                return

            if len(args) > 4:
                await ctx.reply(MessageChain(["参数过多，最多支持4个参数：标签 评分 页数 页码"]))
                return

            tags = re.sub(r'[，,+]+', ' ', args[0])

            params = defaults.copy()
            param_names = ["min_rating", "min_pages", "target_page"]

            for i, (name, value) in enumerate(zip(param_names, args[1:]), 1):
                try:
                    params[name] = int(value)
                except ValueError:
                    await ctx.reply(MessageChain([f"第{i + 1}个参数应为整数: {value}"]))
                    return

            await ctx.reply(MessageChain(["正在搜索，请稍候..."]))

            search_results = await self.downloader.crawl_ehentai(
                tags,
                params["min_rating"],
                params["min_pages"],
                params["target_page"]
            )

            if not search_results:
                await ctx.reply(MessageChain(["未找到符合条件的结果"]))
                return

            cache_data = {}
            for idx, result in enumerate(search_results, 1):
                cache_data[str(idx)] = result['gallery_url']

            search_cache_folder = Path(self.config['output']['search_cache_folder'])
            search_cache_folder.mkdir(exist_ok=True, parents=True)

            cache_file = search_cache_folder / f"{ctx.event.sender_id}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            output = "搜索结果:\n"
            output += "=" * 50 + "\n"
            for idx, result in enumerate(search_results, 1):
                output += f"[{idx}] {result['title']}\n"
                output += (
                    f" 作者: {result['author']} | 分类: {result['category']} | 页数: {result['pages']} | "
                    f"评分: {result['rating']} | 上传时间: {result['timestamp']}\n"
                )
                output += f" 封面: {result['cover_url']}\n"
                output += f" 画廊链接: {result['gallery_url']}\n"
                output += "-" * 80 + "\n"

            await ctx.reply(MessageChain([output]))

        except ValueError as e:
            logger.exception("参数解析失败")
            await ctx.reply(MessageChain([f"参数错误：{str(e)}"]))

        except Exception as e:
            logger.exception("搜索失败")
            await ctx.reply(MessageChain([f"搜索失败：{str(e)}"]))

    async def download_gallery(self, ctx: EventContext, cleaned_text: str):
        image_folder = Path(self.config['output']['image_folder'])
        image_folder.mkdir(exist_ok=True, parents=True)
        pdf_folder = Path(self.config['output']['pdf_folder'])
        pdf_folder.mkdir(exist_ok=True, parents=True)
        search_cache_folder = Path(self.config['output']['search_cache_folder'])
        search_cache_folder.mkdir(exist_ok=True, parents=True)

        for f in glob.glob(str(Path(self.config['output']['image_folder']) / "*.*")):
            os.remove(f)

        try:
            args = self.parse_command(cleaned_text)
            if len(args) != 1:
                await self.eh_helper(ctx)
                return

            url = args[0]
            pattern = re.compile(r'^https://(e-hentai|exhentai)\.org/g/\d{7}/[a-f0-9]{10}/$')

            if not pattern.match(url):
                if url.isdigit() and int(url) > 0:
                    cache_file = search_cache_folder / f"{ctx.event.sender_id}.json"
                    if cache_file.exists():
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)

                        if url in cache_data:
                            url = cache_data[url]
                            await ctx.reply(MessageChain([f"正在获取画廊链接: {url}"]))
                        else:
                            await ctx.reply(MessageChain([f"未找到索引为 {url} 的画廊"]))
                            return
                    else:
                        await ctx.reply(MessageChain([f"未找到搜索记录，请先使用'搜eh'命令"]))
                        return
                else:
                    await ctx.reply(MessageChain([f"画廊链接异常，请重试..."]))
                    return

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                is_pdf_exist = await self.downloader.process_pagination(ctx, session, url)

                if not is_pdf_exist:
                    title = self.downloader.gallery_title
                    await self.downloader.merge_images_to_pdf(ctx, title)
                    await self.uploader.upload_file(ctx, self.config['output']['pdf_folder'], title)

        except Exception as e:
            logger.exception("下载失败")
            await ctx.reply(MessageChain([f"下载失败：{str(e)}"]))

    async def eh_helper(self, ctx: EventContext):
        help_text = """eh指令帮助：
[1] 搜索画廊: 搜eh [关键词] [最低评分（2-5，默认2）] [最少页数（默认1）] [获取第几页的画廊列表（默认1）]
[2] 下载画廊: 看eh [画廊链接/搜索结果序号]
[3] 获取指令帮助: eh
[4] 热重载config相关参数: 重载eh配置

可用的搜索方式:
[1] 搜eh [关键词]
[2] 搜eh [关键词] [最低评分]
[3] 搜eh [关键词] [最低评分] [最少页数]
[4] 搜eh [关键词] [最低评分] [最少页数] [获取第几页的画廊列表]

可用的下载方式：
[1] 看eh [画廊链接]
[2] 看eh [搜索结果序号]（确保你最近至少使用过一次"搜eh"命令）"""
        await ctx.reply(MessageChain([help_text]))

    async def reload_config(self, ctx: EventContext):
        await ctx.reply(MessageChain(["正在重载配置参数"]))
        self.config = load_config()
        self.uploader = MessageAdapter(self.config)
        self.downloader = Downloader(self.config, self.uploader, self.parser)
        await ctx.reply(MessageChain(["已重载配置参数"]))
