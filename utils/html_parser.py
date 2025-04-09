import re
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class HTMLParser:
    @staticmethod
    def parse_background_position(style: str) -> Tuple[int, int]:
        match = re.search(r'background-position:\s*(-?\d+)px\s+(-?\d+)px', style)
        return (int(match.group(1)), int(match.group(2))) if match else (0, 0)

    @staticmethod
    def calculate_rating(x: int, y: int) -> float:
        full_stars = 5 - abs(x) // 16
        half_star = 0.5 if y == -21 else 0
        return full_stars - half_star

    @staticmethod
    def extract_author_and_title(raw_title: str) -> Tuple[str, str]:
        match = re.match(r'^\[(.*?)\]\s*(.*)', raw_title)
        return (match.groups() if match else (None, raw_title))

    @staticmethod
    def parse_timestamp_from_cell(cell: Tag) -> str:
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', cell.get_text(strip=True))
        return match.group(1) if match else time.strftime("%Y-%m-%d")

    @staticmethod
    def extract_page_count(cell: Tag) -> int:
        page_div = cell.find('div', string=re.compile(r'(\d+)\s*pages?', re.IGNORECASE))

        if not page_div:
            for div in cell.find_all('div'):
                if re.search(r'(\d+)\s*pages?', div.get_text(), re.I):
                    page_div = div
                    break

        if page_div:
            match = re.search(r'(\d+)\s*pages?', page_div.get_text(), re.I)
            return int(match.group(1)) if match else 0

        return 0

    @staticmethod
    def extract_cover_url(cell: Tag) -> str:
        try:
            img_tag = cell.find('img')
            if img_tag:
                url = img_tag.get('data-src') or img_tag.get('src', '')
                return url.replace('/t/', '/i/').split('?')[0]
        except Exception as e:
            logger.warning(f"封面解析失败: {e}")

        return ""

    @staticmethod
    def get_next_page_url(html_content: str) -> Optional[str]:
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        if (next_link := soup.find('a', id='unext')):
            return next_link['href']

        return None

    @staticmethod
    def extract_image_url_from_page(html_content: str) -> Optional[str]:
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        img_tag = soup.select_one("html > body > div:nth-of-type(1) > div:nth-of-type(2) > a > img")

        if img_tag and (img_url := img_tag.get("src")):
            return img_url

        return None

    @staticmethod
    def extract_gallery_info(html_content: str) -> Tuple[str, int]:
        if not html_content:
            return None, 0

        soup = BeautifulSoup(html_content, "html.parser")

        title_element = soup.select_one("#gn")
        title = title_element.text.strip() if title_element else "output"

        forbidden_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', "'"]
        for char in forbidden_chars:
            title = title.replace(char, '-')

        pagination_row = soup.select_one("table.ptt > tr")
        if not pagination_row:
            return title, 1

        last_page_element = pagination_row.find_all("td")[-2].find("a")
        last_page_number = int(last_page_element.text.strip()) if last_page_element else 1
        
        return title, last_page_number

    @staticmethod
    def extract_subpage_urls(html_content: str) -> List[str]:
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        if gdt_element := soup.find("div", id="gdt"):
            return [a["href"] for a in gdt_element.find_all("a", href=True)]

        return []

    @staticmethod
    def parse_gallery_from_html(html_content: str) -> List[Dict[str, Any]]:
        if not html_content:
            return []

        results = []
        soup = BeautifulSoup(html_content, 'html.parser')

        if (table := soup.find('table', class_='itg')):
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        category = cells[0].get_text(strip=True)
                        gallery_url = cells[2].find('a')['href']
                        cover_url = HTMLParser.extract_cover_url(cells[1])
                        timestamp = HTMLParser.parse_timestamp_from_cell(cells[1])

                        title_element = cells[2].find('a')
                        raw_title = title_element.find('div', class_='glink').get_text(strip=True)
                        author, title = HTMLParser.extract_author_and_title(raw_title)

                        rating_div = cells[1].find('div', class_='ir')
                        rating = 0.0
                        if rating_div:
                            x, y = HTMLParser.parse_background_position(rating_div.get('style', ''))
                            rating = HTMLParser.calculate_rating(x, y)

                        pages = HTMLParser.extract_page_count(cells[3])

                        results.append({
                            "title": title.strip(),
                            "author": author.strip() if author else "Unknown",
                            "category": category,
                            "gallery_url": gallery_url,
                            "cover_url": cover_url,
                            "timestamp": timestamp,
                            "rating": round(rating, 1),
                            "pages": pages
                        })
                    except Exception as e:
                        logger.warning(f"数据解析异常: {e}")

        return results
