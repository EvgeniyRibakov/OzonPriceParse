"""Главный файл для запуска парсера."""
import asyncio
from pathlib import Path

from loguru import logger

from src.agents.browser_agent import BrowserAgent
from src.config.settings import Settings
from src.utils.logger import setup_logger


async def main():
    """Основная функция."""
    # Загружаем настройки
    settings = Settings()

    # Настраиваем логирование
    setup_logger(settings.logs_dir)

    logger.info("=" * 60)
    logger.info("Запуск парсера цен Ozon Seller")
    logger.info("=" * 60)

    # URL для старта (можно передать через переменную окружения или аргумент)
    start_url = (
        "https://seller.ozon.ru/app/products?token="
        "eyJhbGciOiJIUzI1NiIsIm96b25pZCI6Im5vdHNlbnNpdGl2ZSIsInR5cCI6IkpXVCJ9."
        "eyJ1c2VyX2lkIjo4NjYwNzMzNSwiaXNfcmVnaXN0cmF0aW9uIjpmYWxzZSwicmV0dXJuX3VybCI6"
        "Imh0dHBzOi8vc2VsbGVyLm96b24ucnUvYXBwL3Byb2R1Y3RzIiwicGF5bG9hZCI6bnVsbCwiZXhw"
        "IjoxNzY0MzQ3MDIxLCJpYXQiOjE3NjQzNDcwMTEsImlzcyI6Im96b25pZCJ9."
        "xqCyVmJNVURosfFveqEuSIpYxTU-tNDNJeQt7VtzX14"
    )

    agent = BrowserAgent(settings)

    try:
        # Выполняем основной поток
        downloaded_file = await agent.execute_flow(start_url)

        if downloaded_file:
            logger.success(f"Работа завершена успешно. Файл: {downloaded_file}")
        else:
            logger.warning("Работа завершена, но файл не был скачан")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Остановка работы. Проверьте логи для деталей.")
        raise
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
