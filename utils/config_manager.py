import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, Union
from urllib.parse import urlparse
import aiohttp

logger = logging.getLogger(__name__)


def parse_proxy_config(proxy_str: str) -> Dict[str, Any]:
    if not proxy_str:
        return {}

    parsed = urlparse(proxy_str)

    if parsed.scheme not in ('http', 'https', 'socks5'):
        raise ValueError("仅支持HTTP/HTTPS/SOCKS5代理协议")

    auth = None
    if parsed.username and parsed.password:
        auth = aiohttp.BasicAuth(parsed.username, parsed.password)

    proxy_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        proxy_url += f":{parsed.port}"

    return {
        'url': proxy_url,
        'auth': auth
    }


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        website = config.setdefault('website', 'e-hentai')
        cookies = config.setdefault('cookies', {
            "ipb_member_id": "",
            "ipb_pass_hash": "",
			"igneous": ""
        })
        
        config_updated = False
        if website == 'exhentai':
            if any(not cookies.get(key, '') for key in ["ipb_member_id", "ipb_pass_hash", "igneous"]):
                config['website'] = 'e-hentai'
                config_updated = True
                logger.warning("网站设置为里站exhentai但cookies不完整，已更换为表站e-hentai")
        
        request_config = config.setdefault('request', {})
        request_config.setdefault('headers', {'User-Agent': 'Mozilla/5.0'})
        request_config.setdefault('concurrency', 5)
        request_config.setdefault('max_retries', 10)
        request_config.setdefault('timeout', 30)

        proxy_str = request_config.get('proxies', '')
        proxy_config = parse_proxy_config(proxy_str)
        request_config['proxy'] = proxy_config

        output_config = config.setdefault('output', {})
        output_config.setdefault('image_folder', './tempImages')
        output_config.setdefault('pdf_folder', './pdfs')
	output_config.setdefault('search_cache_folder', './searchCache')
        output_config.setdefault('jpeg_quality', 85)
        output_config.setdefault('max_pages_per_pdf', 200)
        
        if config_updated:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        return config
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"配置文件格式错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"配置文件加载失败: {str(e)}")
        raise
