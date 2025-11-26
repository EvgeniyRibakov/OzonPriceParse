"""Настройка логирования."""

import sys
from loguru import logger
from pathlib import Path
from src.config.settings import settings


def setup_logger() -> None:
    """Настройка логирования."""
    # Удаляем стандартный handler
    logger.remove()
    
    # Добавляем консольный handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # Добавляем файловый handler если указан
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            settings.log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )


# Инициализация при импорте
setup_logger()

