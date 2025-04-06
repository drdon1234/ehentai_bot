from pkg.platform.types import MessageChain
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived
from plugins.ehentai_bot.utils.config_manager import load_config
from plugins.ehentai_bot.utils.downloader import Downloader
from plugins.ehentai_bot.utils.helpers import Helpers
from plugins.ehentai_bot.utils.html_parser import HTMLParser
from plugins.ehentai_bot.utils.message_adapter import MessageAdapter
from plugins.ehentai_bot.utils.pdf_generator import PDFGenerator
from pathlib import Path
import os
import re
import aiohttp
import glob
import logging
from typing import List

logger = logging.getLogger(__name__)


@register(name="ehentai_bot", description="适配 LangBot 的 EHentai画廊 转 PDF 插件", version="1.2", author="drdon1234")
class EHentaiBot(BasePlugin):
    def __init__(self, host: APIHost):
        super().__init__(host)
        config_path = Path(__file__).parent / "config.yaml"
        self.uploader = MessageAdapter(config_path)
        self.config = load_config()
        self.helpers = Helpers()
        self.parser = HTMLParser()
        self.downloader = Downloader(self.config, self.parser, self.helpers)
        self.pdf_generator = PDFGenerator(self.config, self.helpers)

    async def initialize(self):
        """异步初始化"""
        pass

    def __del__(self):
        """插件卸载时触发"""
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
        else:
            prevent_default = False

        if prevent_default:
            ctx.prevent_default()

    @staticmethod
    def parse_command(message: str) -> List[str]:
        return [p for p in message.split(' ') if p][1:]

    async def search_gallery(self, ctx: EventContext, cleaned_text: str):
        try:
            args = self.parse_command(cleaned_text)
            if len(args) < 1 or len(args) > 4:
                await self.eh_helper(ctx)
                return

            tags = re.sub(r'[，,+]+', ' ', args[0])
            min_rating = 2
            min_pages = 1
            target_page = 1

            if len(args) >= 2:
                min_rating = int(args[1])
            if len(args) >= 3:
                min_pages = int(args[2])
            if len(args) == 4:
                target_page = int(args[3])

            search_results = await self.downloader.crawl_ehentai(tags, min_rating, min_pages, target_page)
            results_ui = self.helpers.get_search_results(search_results)

            await ctx.reply(MessageChain([results_ui]))
        except Exception as e:
            logger.exception("搜索失败")
            await ctx.reply(MessageChain([f"搜索失败：{str(e)}"]))

    async def download_gallery(self, ctx: EventContext, cleaned_text: str):
        # 初始化并清理临时文件夹
        image_folder = Path(self.config['output']['image_folder'])
        pdf_folder = Path(self.config['output']['pdf_folder'])

        if not image_folder.exists():
            image_folder.mkdir(parents=True)
        if not pdf_folder.exists():
            pdf_folder.mkdir(parents=True)

        # 清理临时图片文件
        for f in glob.glob(str(Path(self.config['output']['image_folder']) / "*.*")):
            os.remove(f)

        try:
            args = self.parse_command(cleaned_text)
            if len(args) != 1:
                await self.eh_helper(ctx)
                return

            # 验证画廊链接格式
            pattern = re.compile(r'^https://[e-hentai|exhentai]\.org/g/\d{7}/[a-f0-9]{10}/$')
            if not pattern.match(args[0]):
                await ctx.reply(MessageChain([f"画廊链接异常，请重试..."]))
                return

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                is_pdf_exist = await self.downloader.process_pagination(ctx, session, args[0])

                if not is_pdf_exist:
                    title = self.downloader.gallery_title
                    await self.pdf_generator.merge_images_to_pdf(ctx, title)
                    await self.uploader.upload_file(ctx, self.config['output']['pdf_folder'], title)
        except Exception as e:
            logger.exception("下载失败")
            await ctx.reply(MessageChain([f"下载失败：{str(e)}"]))

    async def eh_helper(self, ctx: EventContext):
        help_text = """eh指令帮助：

[1] 搜索画廊: 搜eh [关键词] [最低评分（2-5，默认2）] [最少页数（默认1）] [获取第几页的画廊列表（默认1）]
[2] 下载画廊: 看eh [画廊链接]
[3] 获取指令帮助: eh

可用的搜索方式:
[1] 搜eh [关键词]
[2] 搜eh [关键词] [最低评分] [最少页数]
[3] 搜eh [关键词] [最低评分] [最少页数] [获取第几页的画廊列表]

PS:
ehentai的分页目录仅能通过迭代生成，不建议获取较大页数的画廊列表"""

        await ctx.reply(MessageChain([help_text]))
