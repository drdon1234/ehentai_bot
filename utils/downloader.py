from pkg.platform.types import MessageChain
from pkg.plugin.context import EventContext
from typing import List, Dict, Any, Optional, Tuple
import os
import re
import asyncio
import aiohttp
import aiofiles
import random
import glob
import math
import img2pdf
import logging
from pathlib import Path
from natsort import natsorted
from PIL import Image
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self, config: Dict[str, Any], uploader: Any, parser: Any):
        self.config = config
        self.uploader = uploader
        self.parser = parser
        self.semaphore = asyncio.Semaphore(self.config['request']['concurrency'])
        self.gallery_title = "output"
        Path(self.config['output']['image_folder']).mkdir(parents=True, exist_ok=True)
        Path(self.config['output']['pdf_folder']).mkdir(parents=True, exist_ok=True)

    async def fetch_with_retry(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        proxy_conf = self.config['request'].get('proxy', {})
        cookies = self.config['request']['cookies'] if self.config['request']['website'] == 'exhentai' else None

        for attempt in range(self.config['request']['max_retries']):
            try:
                async with self.semaphore:
                    async with session.get(
                            url,
                            headers=self.config['request']['headers'],
                            proxy=proxy_conf.get('url'),
                            proxy_auth=proxy_conf.get('auth'),
                            timeout=aiohttp.ClientTimeout(total=self.config['request']['timeout']),
                            ssl=False,
                            cookies=cookies
                    ) as response:
                        response.raise_for_status()
                        return await response.text()
            except asyncio.TimeoutError:
                logger.warning(f"请求超时，尝试 {attempt + 1}/{self.config['request']['max_retries']}: {url}")
            except aiohttp.ClientResponseError as e:
                logger.warning(f"HTTP错误 {e.status}，尝试 {attempt + 1}/{self.config['request']['max_retries']}: {url}")
            except Exception as e:
                logger.warning(f"尝试 {attempt + 1}/{self.config['request']['max_retries']} 失败: {url} - {str(e)}")

            await asyncio.sleep(2 ** attempt)

        logger.error(f"请求失败，放弃: {url}")
        return None

    async def download_image_with_fixed_number(self, session: aiohttp.ClientSession, img_url: str,
                                               image_number: int) -> bool:
        proxy_conf = self.config['request'].get('proxy', {})
        cookies = self.config['request']['cookies'] if self.config['request']['website'] == 'exhentai' else None

        for attempt in range(self.config['request']['max_retries']):
            try:
                async with self.semaphore:
                    async with session.get(
                            img_url,
                            headers=self.config['request']['headers'],
                            proxy=proxy_conf.get('url'),
                            proxy_auth=proxy_conf.get('auth'),
                            timeout=aiohttp.ClientTimeout(total=self.config['request']['timeout']),
                            ssl=False,
                            cookies=cookies
                    ) as response:
                        response.raise_for_status()
                        content = await response.read()

                        if len(content) < 1024:
                            raise ValueError("无效的图片内容")

                        image_path = Path(self.config['output']['image_folder']) / f"{image_number}.jpg"

                        async with aiofiles.open(image_path, "wb") as file:
                            await file.write(content)

                        with Image.open(image_path) as img:
                            if img.format != 'JPEG':
                                if img.mode in ('RGBA', 'LA'):
                                    background = Image.new('RGB', img.size, (255, 255, 255))
                                    background.paste(img, mask=img.split()[-1])
                                    background.save(image_path, 'JPEG', quality=self.config['output']['jpeg_quality'])
                                else:
                                    img = img.convert('RGB')
                                    img.save(image_path, 'JPEG', quality=self.config['output']['jpeg_quality'])

                        return True
            except Exception as e:
                logger.warning(f"图片 {image_number} 下载尝试 {attempt + 1} 失败: {img_url} - {str(e)}")
                await asyncio.sleep(2 ** attempt)

        return False

    async def _process_subpage_with_tracking(self, session: aiohttp.ClientSession, item: dict) -> dict:
        try:
            html_content = await self.fetch_with_retry(session, item["url"])
            if not html_content:
                return {"success": False, "error": "获取页面失败", "item": item}

            img_url = self.parser.extract_image_url_from_page(html_content)
            if not img_url:
                return {"success": False, "error": "未找到图片URL", "item": item}

            success = await self.download_image_with_fixed_number(session, img_url, item["image_number"])

            if success:
                return {"success": True, "item": item}
            else:
                return {"success": False, "error": "图片下载失败", "item": item}
        except Exception as e:
            return {"success": False, "error": str(e), "item": item}

    async def process_pagination(self, ctx: EventContext, session: aiohttp.ClientSession, gallery_url: str) -> bool:
        main_html = await self.fetch_with_retry(session, gallery_url)
        if not main_html:
            raise ValueError("无法获取主页面内容")

        self.gallery_title, last_page_number = self.parser.extract_gallery_info(main_html)

        pdf_folder = self.config['output']['pdf_folder']
        all_files = os.listdir(pdf_folder)
        pattern = re.compile(rf"^{re.escape(self.gallery_title)}(?: part \d+)?\.pdf$")
        matching_files = [
            os.path.join(pdf_folder, f) for f in all_files if pattern.match(f)
        ]

        files = natsorted(matching_files)
        if files:
            await ctx.reply(MessageChain(["已找到本地画廊，发送中..."]))
            await self.uploader.upload_file(ctx, pdf_folder, self.gallery_title)
            return True

        await ctx.reply(MessageChain(["正在下载画廊图片，请稍候..."]))

        page_urls = [f"{gallery_url}?p={page}" for page in range(last_page_number)]
        all_subpage_urls = []

        for page_index, page_url in enumerate(page_urls):
            html_content = await self.fetch_with_retry(session, page_url)
            if html_content:
                subpages = self.parser.extract_subpage_urls(html_content)
                for position, url in enumerate(subpages):
                    all_subpage_urls.append({
                        "url": url,
                        "page": page_index,
                        "position": position,
                        "image_number": len(all_subpage_urls) + 1
                    })

        queue = asyncio.Queue()
        for item in all_subpage_urls:
            await queue.put(item)

        results = []

        async def download_worker():
            while not queue.empty():
                try:
                    item = await queue.get()
                    result = await self._process_subpage_with_tracking(session, item)
                    results.append(result)
                except Exception as e:
                    logger.error(f"工作线程错误: {str(e)}")
                finally:
                    queue.task_done()

        workers = [download_worker() for _ in range(self.config['request']['concurrency'])]
        await asyncio.gather(*workers)

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        if failed:
            await ctx.reply(MessageChain([f"首次下载完成，但有 {len(failed)} 个页面失败，正在重试..."]))
            retry_results = await self.retry_failed_downloads(ctx, session, failed)

            retry_successful = [r for r in retry_results if r.get("success")]
            retry_failed = [r for r in retry_results if not r.get("success")]

            successful.extend(retry_successful)
            failed = retry_failed

        if failed:
            await ctx.reply(MessageChain([f"下载完成，但仍有 {len(failed)} 个页面失败"]))
        else:
            await ctx.reply(MessageChain(["所有页面下载成功"]))

        return False

    async def retry_failed_downloads(self, ctx: EventContext, session: aiohttp.ClientSession,
                                     failed_items: list) -> list:
        if not failed_items:
            return []

        retry_queue = asyncio.Queue()
        for item in failed_items:
            await retry_queue.put(item["item"])

        retry_results = []

        async def retry_worker():
            while not retry_queue.empty():
                try:
                    item = await retry_queue.get()
                    result = await self._process_subpage_with_tracking(session, item)
                    retry_results.append(result)
                except Exception as e:
                    logger.error(f"重试工作线程错误: {str(e)}")
                finally:
                    retry_queue.task_done()

        retry_workers = [retry_worker() for _ in range(max(1, self.config['request']['concurrency'] // 2))]
        await asyncio.gather(*retry_workers)

        return retry_results

    async def merge_images_to_pdf(self, ctx: EventContext, gallery_title: str) -> str:
        await ctx.reply(MessageChain(["正在将图片合并为pdf文件，请稍候..."]))
        image_files = natsorted(glob.glob(str(Path(self.config['output']['image_folder']) / "*.jpg")))
        if not image_files:
            logger.warning("没有可用的图片文件")
        
        pdf_dir = Path(self.config['output']['pdf_folder'])
        max_pages = self.config['output']['max_pages_per_pdf']
        
        if 0 < max_pages < len(image_files):
            total = math.ceil(len(image_files) / max_pages)
            for i in range(total):
                batch = image_files[i * max_pages: (i + 1) * max_pages]
                output_path = pdf_dir / f"{gallery_title} part {i + 1}.pdf"
                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert(batch))
                logger.info(f"生成PDF: {output_path.name}")
        else:
            output_path = pdf_dir / f"{gallery_title}.pdf"
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(image_files))
            logger.info(f"生成PDF: {output_path.name}")
            
    async def crawl_ehentai(self, search_term: str, min_rating: int = 0, min_pages: int = 0, target_page: int = 1) -> \
    List[Dict[str, Any]]:
        base_url = f"https://{self.config['request']['website']}.org/"
        search_params = {'f_search': search_term, 'f_srdd': min_rating, 'f_spf': min_pages, 'range': target_page}
        parsed_url = urlparse(base_url)
        query = parse_qs(parsed_url.query)
        query.update(search_params)
        new_query = urlencode(query, doseq=True)
        search_url = urlunparse(parsed_url._replace(query=new_query))

        results = []

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            html = await self.fetch_with_retry(session, search_url)
            if html:
                results = self.parser.parse_gallery_from_html(html)

        if not results:
            results.append(f"未找到关键词为 {search_term} 的相关画廊")

        return results
