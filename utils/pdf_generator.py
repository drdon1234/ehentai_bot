from pkg.platform.types import MessageChain
from pkg.plugin.context import EventContext
import glob
import math
import img2pdf
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from natsort import natsorted

logger = logging.getLogger(__name__)


class PDFGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

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

