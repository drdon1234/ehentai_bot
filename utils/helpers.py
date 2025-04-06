import re
from typing import Tuple, Dict, List, Any
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


class Helpers:
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
    def build_search_url(base_url: str, params: Dict[str, Any]) -> str:
        parsed_url = urlparse(base_url)
        query = parse_qs(parsed_url.query)
        query.update(params)
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed_url._replace(query=new_query))

    @staticmethod
    def get_safe_filename(title: str) -> str:
        return re.sub(r'[^\w\-_. ]', '_', title)

    @staticmethod
    def get_search_results(results: List[Dict[str, Any]]) -> str:
        output = "搜索结果:\n"
        output += "=" * 80 + "\n"

        for idx, result in enumerate(results, 1):
            output += f"[{idx}] {result['title']}\n"
            output += (
                f" 作者: {result['author']} | 分类: {result['category']} | 页数: {result['pages']} | "
                f"评分: {result['rating']} | 时间: {result['timestamp']}\n"
            )
            output += f" 封面: {result['cover_url']}\n"
            output += f" 画廊链接: {result['gallery_url']}\n"
            output += "-" * 80 + "\n"

        return output
