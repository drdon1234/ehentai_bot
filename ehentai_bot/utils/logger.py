import logging
import os
from pathlib import Path
from typing import Optional


class LoggerSetup:
    _initialized = False

    @classmethod
    def setup_logger(cls, log_file: Optional[Path] = None, log_level: int = logging.INFO):
        """设置应用程序日志记录器"""
        if cls._initialized:
            return logging.getLogger("ehentai_bot")

        # 创建根日志记录器
        logger = logging.getLogger("ehentai_bot")
        logger.setLevel(log_level)
        logger.propagate = False

        if logger.handlers:  # 清除现有处理程序
            logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 创建控制台处理程序 - 仅在控制台显示ERROR或更高级别的日志
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)  # 只将关键错误发送到控制台
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 如果提供了log_file，则创建文件处理程序
        if log_file:
            os.makedirs(log_file.parent, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)  # 所有日志都写入文件
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        cls._initialized = True
        return logger


def get_logger(name: str = "ehentai_bot"):
    """获取命名的日志记录器实例"""
    return logging.getLogger(name)
