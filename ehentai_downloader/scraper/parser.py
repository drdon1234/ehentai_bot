import re
import time
from bs4 import BeautifulSoup


def parse_timestamp_from_cell(cell):
    """从单元格中提取时间戳"""
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', cell.get_text(strip=True))
    return match.group(1) if match else time.strftime("%Y-%m-%d %H:%M")


def extract_page_count(cell):
    """从单元格中提取页数信息"""
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


def extract_cover_url(cell):
    """提取封面URL"""
    try:
        img_tag = cell.find('img')
        if img_tag:
            url = img_tag.get('data-src') or img_tag.get('src', '')
            return url.replace('/t/', '/i/').split('?')[0]
    except Exception as e:
        print(f"封面解析失败: {e}")
    return ""


def parse_gallery_from_html(html_content, helpers):
    """从HTML内容中解析画廊数据"""
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
                    cover_url = extract_cover_url(cells[1])
                    timestamp = parse_timestamp_from_cell(cells[1])
                    title_element = cells[2].find('a')
                    raw_title = title_element.find('div', class_='glink').get_text(strip=True)
                    author, title = helpers.extract_author_and_title(raw_title)
                    rating_div = cells[1].find('div', class_='ir')
                    rating = 0.0

                    if rating_div:
                        x, y = helpers.parse_background_position(rating_div.get('style', ''))
                        rating = helpers.calculate_rating(x, y)

                    pages = extract_page_count(cells[3])

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
                    print(f"数据解析异常: {e}")

    return results


def get_next_page_url(html_content):
    """获取下一页的URL"""
    soup = BeautifulSoup(html_content, 'html.parser')
    if (next_link := soup.find('a', id='unext')):
        return next_link['href']
    return None


def extract_image_url_from_page(html_content):
    """从子页面中提取图片URL"""
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, "html.parser")
    img_tag = soup.select_one("html > body > div:nth-of-type(1) > div:nth-of-type(2) > a > img")

    if img_tag and (img_url := img_tag.get("src")):
        return img_url
    return None


def extract_gallery_info(html_content):
    """从画廊主页提取信息"""
    if not html_content:
        return None, 0

    soup = BeautifulSoup(html_content, "html.parser")
    title_element = soup.select_one("#gn")
    title = title_element.text.strip() if title_element else "output"

    pagination_row = soup.select_one("table.ptt > tr")
    if not pagination_row:
        return title, 1

    last_page_element = pagination_row.find_all("td")[-2].find("a")
    last_page_number = int(last_page_element.text.strip()) if last_page_element else 1

    return title, last_page_number


def extract_subpage_urls(html_content):
    """从画廊页面中提取子页面的URL"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    if gdt_element := soup.find("div", id="gdt"):
        return [a["href"] for a in gdt_element.find_all("a", href=True)]
    return []
