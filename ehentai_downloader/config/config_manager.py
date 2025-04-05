import yaml
from pathlib import Path
from urllib.parse import urlparse
import aiohttp


def load_config(config_path=None):
    """加载并验证配置文件"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # 请求配置
        request_config = config.setdefault('request', {})
        request_config.setdefault('headers', {'User-Agent': 'Mozilla/5.0'})
        request_config.setdefault('concurrency', 5)
        request_config.setdefault('max_retries', 10)
        request_config.setdefault('timeout', 30)

        # 代理配置解析
        proxy_str = request_config.get('proxies', '')
        proxy_config = {}

        if proxy_str:
            parsed = urlparse(proxy_str)
            if parsed.scheme not in ('http', 'https', 'socks5'):
                raise ValueError("仅支持HTTP/HTTPS/SOCKS5代理协议")

            auth = None
            if parsed.username and parsed.password:
                auth = aiohttp.BasicAuth(parsed.username, parsed.password)

            # 构建代理URL
            proxy_url = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                proxy_url += f":{parsed.port}"

            proxy_config = {
                'url': proxy_url,
                'auth': auth
            }

        request_config['proxy'] = proxy_config

        # 输出配置
        output_config = config.setdefault('output', {})
        output_config.setdefault('image_folder', './images')
        output_config.setdefault('pdf_folder', './pdfs')
        output_config.setdefault('jpeg_quality', 95)
        output_config.setdefault('max_pages_per_pdf', 0)

        return config

    except Exception as e:
        print(f"配置文件加载失败: {str(e)}")
        raise
