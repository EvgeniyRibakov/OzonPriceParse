"""Утилиты для загрузки списка товаров."""

from pathlib import Path
from typing import List
from loguru import logger

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


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


def load_product_ids_from_xlsx(file_path: str, column: int = 0, sheet_name: str = None, skip_header: bool = True) -> List[str]:
    """
    Загрузить список ID товаров (артикулов) из XLSX файла.
    
    Args:
        file_path: Путь к XLSX файлу
        column: Номер колонки (0 = первая колонка, столбец A)
        sheet_name: Имя листа (если None, используется активный лист)
        skip_header: Пропускать ли первую строку (заголовок)
        
    Returns:
        Список ID товаров (артикулов)
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl не установлен. Установите: pip install openpyxl")
    
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    product_ids = []
    
    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
    
    # Выбираем лист
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Лист '{sheet_name}' не найден в файле. Доступные листы: {wb.sheetnames}")
        ws = wb[sheet_name]
    else:
        ws = wb.active
    
    # Читаем данные из указанной колонки
    start_row = 2 if skip_header else 1
    for row in ws.iter_rows(min_row=start_row, min_col=column+1, max_col=column+1, values_only=True):
        value = row[0]
        if value is not None:
            # Преобразуем в строку и убираем пробелы
            value_str = str(value).strip()
            if value_str:  # Пропускаем пустые значения
                product_ids.append(value_str)
    
    wb.close()
    
    logger.info(f"Загружено {len(product_ids)} товаров из XLSX: {file_path} (колонка {column+1}, лист: {ws.title})")
    return product_ids

