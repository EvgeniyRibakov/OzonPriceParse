"""Простой запуск Selenium-агента для скачивания отчёта из Ozon Seller."""
from pathlib import Path

from loguru import logger

from src.agents.selenium_agent import SeleniumAgent
from src.config.settings import Settings
from src.utils.logger import setup_logger


def main():
    """Основная функция."""
    # Загружаем настройки
    settings = Settings()
    
    # Настраиваем логирование
    setup_logger(settings.logs_dir)
    
    logger.info("=" * 60)
    logger.info("Запуск Selenium-агента для скачивания отчёта Ozon Seller")
    logger.info("=" * 60)
    
    # Проверяем обязательные настройки
    if not settings.phone_number:
        logger.error("PHONE_NUMBER не указан в .env файле!")
        logger.error("Укажите номер телефона в формате: PHONE_NUMBER=+79991234567")
        raise ValueError("PHONE_NUMBER не указан в настройках")
    
    # URL для старта из настроек (.env)
    # Может быть указан с токеном: https://seller.ozon.ru/app/products?token=...
    # Или без токена: https://seller.ozon.ru/app/products (тогда потребуется авторизация)
    start_url = settings.ozon_start_url
    
    if not start_url or start_url == "https://seller.ozon.ru/app/products":
        logger.warning("OZON_START_URL не указан в .env или указан без токена")
        logger.info("Используется базовый URL. Потребуется полная авторизация.")
        start_url = "https://seller.ozon.ru/app/products"
    
    agent = SeleniumAgent(settings)
    
    try:
        # Скачиваем отчёт
        downloaded_file = agent.download_report(start_url)
        
        if downloaded_file:
            logger.success(f"Работа завершена успешно. Файл: {downloaded_file}")
        else:
            logger.warning("Работа завершена, но файл не был скачан")
    
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Остановка работы. Проверьте логи для деталей.")
        raise
    finally:
        agent.close()


if __name__ == "__main__":
    main()




