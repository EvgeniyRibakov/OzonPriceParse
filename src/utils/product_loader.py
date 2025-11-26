"""Утилиты для загрузки списка товаров."""

from pathlib import Path
from typing import List
from loguru import logger


def load_product_ids_from_file(file_path: str) -> List[str]:
    """
    Загрузить список ID товаров из текстового файла.
    
    Формат файла: одна строка = один ID товара.
    Пустые строки и строки начинающиеся с # игнорируются.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Список ID товаров
    """
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    product_ids = []
    with open(file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            product_ids.append(line)
    
    logger.info(f"Загружено {len(product_ids)} товаров из файла: {file_path}")
    return product_ids


def load_product_ids_from_csv(file_path: str, column: int = 0) -> List[str]:
    """
    Загрузить список ID товаров из CSV файла.
    
    Args:
        file_path: Путь к CSV файлу
        column: Номер колонки (0 = первая колонка)
        
    Returns:
        Список ID товаров
    """
    import csv
    
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    product_ids = []
    with open(file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        # Пропускаем заголовок если есть
        try:
            next(reader)
        except StopIteration:
            pass
        
        for row in reader:
            if len(row) > column and row[column].strip():
                product_ids.append(row[column].strip())
    
    logger.info(f"Загружено {len(product_ids)} товаров из CSV: {file_path}")
    return product_ids

