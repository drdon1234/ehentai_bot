import re
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

def parse_background_position(style):
    """解析background-position的坐标值"""
    match = re.search(r'background-position:\s*(-?\d+)px\s+(-?\d+)px', style)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)

def calculate_rating(x, y):
    """根据坐标计算评分"""
    full_stars = 5 - abs(x) // 16
    half_star = 0.5 if y == -21 else 0
    return full_stars - half_star

def extract_author_and_title(raw_title):
    """从标题中分离作者和作品名称"""
    match = re.match(r'^\[(.*?)\]\s*(.*)', raw_title)
    return (match.groups() if match else (None, raw_title))

def build_search_url(base_url, params):
    """构建包含高级搜索参数的URL"""
    parsed_url = urlparse(base_url)
    query = parse_qs(parsed_url.query)
    query.update(params)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query))

def get_safe_filename(title):
    """将标题转换为安全的文件名"""
    return re.sub(r'[^\w\-_. ]', '_', title)
