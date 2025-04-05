import glob
import math
import img2pdf
from pathlib import Path
from natsort import natsorted


class PDFGenerator:
    def __init__(self, config, helpers):
        self.config = config
        self.helpers = helpers

    async def merge_images_to_pdf(self, gallery_title):
        """合并图片为PDF文件"""
        image_files = natsorted(glob.glob(str(Path(self.config['output']['image_folder']) / "*.jpg")))

        if not image_files:
            print("没有可用的图片文件")
            return

        safe_title = self.helpers.get_safe_filename(gallery_title)
        pdf_dir = Path(self.config['output']['pdf_folder'])
        max_pages = self.config['output']['max_pages_per_pdf']

        if max_pages > 0 and len(image_files) > max_pages:
            total = math.ceil(len(image_files) / max_pages)

            for i in range(total):
                batch = image_files[i * max_pages: (i + 1) * max_pages]
                output_path = pdf_dir / f"{safe_title}_part{i + 1}.pdf"

                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert(batch))

                print(f"生成PDF: {output_path.name}")
        else:
            output_path = pdf_dir / f"{safe_title}.pdf"

            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(image_files))

            print(f"生成PDF: {output_path.name}")
