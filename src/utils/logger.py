"""Настройка логирования."""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(logs_dir: Path) -> None:
    """Настраивает логирование с подробным выводом."""
    # Удаляем стандартный обработчик
    logger.remove()

    # Формат для консоли (краткий)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Формат для файла (подробный)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message} | "
        "{extra}"
    )

    # Добавляем консольный обработчик
    logger.add(
        sys.stdout,
        format=console_format,
        level="INFO",
        colorize=True,
    )

    # Создаем директорию для логов
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Добавляем файловый обработчик
    logger.add(
        logs_dir / "app_{time:YYYY-MM-DD}.log",
        format=file_format,
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info("Логирование настроено", logs_dir=str(logs_dir))





