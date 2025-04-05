from pkg.platform.types import MessageChain
from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
from plugins.ehentai_downloader.utils.message_adapter import FileUploader
from plugins.ehentai_downloader.config import load_config
from plugins.ehentai_downloader.utils.helpers import (
    parse_background_position,
    calculate_rating,
    extract_author_and_title,
    build_search_url,
    get_safe_filename
)
from plugins.ehentai_downloader.scraper.parser import (
    parse_gallery_from_html,
    get_next_page_url,
    extract_image_url_from_page,
    extract_gallery_info,
    extract_subpage_urls
)
from plugins.ehentai_downloader.downloader.async_downloader import AsyncDownloader
from plugins.ehentai_downloader.pdf_generator.generator import PDFGenerator
from plugins.ehentai_downloader.ui.interface import UserInterface
from pathlib import Path
import re


class Helpers:
    """帮助类，包含所有工具函数"""

    @staticmethod
    def parse_background_position(style):
        return parse_background_position(style)

    @staticmethod
    def calculate_rating(x, y):
        return calculate_rating(x, y)

    @staticmethod
    def extract_author_and_title(raw_title):
        return extract_author_and_title(raw_title)

    @staticmethod
    def build_search_url(base_url, params):
        return build_search_url(base_url, params)

    @staticmethod
    def get_safe_filename(title):
        return get_safe_filename(title)


class Parser:
    """解析类，包含所有解析函数"""

    @staticmethod
    def parse_gallery_from_html(html_content, helpers):
        return parse_gallery_from_html(html_content, helpers)

    @staticmethod
    def get_next_page_url(html_content):
        return get_next_page_url(html_content)

    @staticmethod
    def extract_image_url_from_page(html_content):
        return extract_image_url_from_page(html_content)

    @staticmethod
    def extract_gallery_info(html_content):
        return extract_gallery_info(html_content)

    @staticmethod
    def extract_subpage_urls(html_content):
        return extract_subpage_urls(html_content)

# 注册插件
@register(name="test_file_sender", description="测试发送文件", version="1.0", author="drdon1234")
class MyPlugin(BasePlugin):

    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)
        config_path = Path(__file__).parent / "config.yaml"
        self.uploader = FileUploader(config_path)
        self.config = load_config()
        self.helpers = Helpers()
        self.parser = Parser()
        self.downloader = AsyncDownloader(self.config, self.parser, self.helpers)
        self.pdf_generator = PDFGenerator(self.config, self.helpers)
        self.ui = UserInterface()

    # 异步初始化
    async def initialize(self):
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
        else:
            prevent_default = False
        if prevent_default:
            ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass

    @staticmethod
    def parse_command(message: str):
        return [p for p in message.split(' ') if p][1:]

    # 发送本子
    async def search_gallery(self, ctx: EventContext, cleaned_text: str):
        ctx.prevent_default()
        args = self.parse_command(cleaned_text)
        args_num = len(args)
        if args_num == 0:
            await ctx.reply(MessageChain(["搜索参数不正确，请重试..."]))
            ctx.prevent_default()
        elif args_num >= 1:
            tags = re.sub(r'[，,]+', ' ', args[0])
            min_rating = 2
            min_pages = 1
            target_page = 1
            if args_num == 3:
                min_rating = args[1]
                min_pages = args[2]
            elif args_num == 4:
                target_page = args[3]
            search_results = await self.downloader.crawl_ehentai(tags, min_rating, min_pages, target_page)
            results_ui = self.ui.get_search_results(search_results)
            await ctx.reply(MessageChain([results_ui]))

    # 发送本子
    async def download_gallery(self, ctx: EventContext, cleaned_text: str):
        ctx.prevent_default()
        # args = self.parse_command(cleaned_text)
        # await self.uploader.upload_file(ctx, "/app/sharedFolder", "test.pdf")