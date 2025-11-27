"""Точка входа в приложение."""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH для корректных импортов
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.logger import setup_logger
from src.agents.ozon_api_agent import OzonAPIAgent
from src.utils.exporter import export_results
from src.config.settings import settings


async def main():
    """Основная функция приложения."""
    setup_logger()
    logger.info("Запуск приложения OzonPriceParse")
    
    # Проверка конфигурации
    if not settings.ozon_client_id or not settings.ozon_api_key:
        logger.error(
            "Ozon API credentials не настроены. "
            "Установите OZON_CLIENT_ID и OZON_API_KEY в .env файле"
        )
        sys.exit(1)
    
    # Инициализация агента
    agent = OzonAPIAgent(config={
        "client_id": settings.ozon_client_id,
        "api_key": settings.ozon_api_key,
        "batch_size": settings.batch_size,
        "request_delay": settings.request_delay,
        "max_requests_per_minute": settings.max_requests_per_minute,
    })
    
    # Загрузка списка товаров
    # Вариант 1: Из файла (раскомментировать и указать путь)
    # from src.utils.product_loader import load_product_ids_from_file
    # product_ids = load_product_ids_from_file("data/products.txt")
    
    # Вариант 2: Из CSV (раскомментировать и указать путь)
    # from src.utils.product_loader import load_product_ids_from_csv
    # product_ids = load_product_ids_from_csv("data/products.csv", column=0)
    
    # Вариант 3: Прямо в коде (для быстрого теста)
    product_ids = ["12345", "67890"]  # TODO: Заменить на реальные ID товаров
    
    logger.info(f"Начало парсинга {len(product_ids)} товаров")
    
    try:
        results = await agent.run(product_ids)
        
        # Экспорт результатов
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = Path(__file__).stem
        csv_path = output_dir / f"prices_{timestamp}.csv"
        xlsx_path = output_dir / f"prices_{timestamp}.xlsx"
        
        # Экспорт в CSV
        export_results(results, str(csv_path), format="csv", include_errors=True)
        
        # Экспорт в XLSX
        try:
            export_results(results, str(xlsx_path), format="xlsx", include_errors=True)
        except ImportError:
            logger.warning("openpyxl не установлен, пропуск экспорта в XLSX")
        
        # Статистика
        success_count = sum(1 for v in results.values() if "error" not in v)
        error_count = len(results) - success_count
        
        logger.info(
            f"Парсинг завершен: {success_count} успешно, {error_count} ошибок"
        )
        logger.info(f"Результаты сохранены: {csv_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

