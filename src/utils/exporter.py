"""Утилиты для экспорта данных в CSV/XLSX."""

import csv
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

try:
    import openpyxl
    from openpyxl import Workbook
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    logger.warning("openpyxl не установлен, экспорт в XLSX недоступен")


def export_to_csv(
    results: Dict[str, Any],
    output_path: str,
    include_errors: bool = True
) -> None:
    """
    Экспортировать результаты в CSV файл.
    
    Args:
        results: Словарь с результатами {product_id: price_data}
        output_path: Путь к выходному файлу
        include_errors: Включать ли товары с ошибками
    """
    if not results:
        logger.warning("Нет данных для экспорта")
        return
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Определяем все возможные поля
    all_fields = set()
    for data in results.values():
        if isinstance(data, dict):
            all_fields.update(data.keys())
    
    # Порядок полей
    field_order = [
        "product_id",
        "offer_id",
        "matched_id",
        "price",
        "old_price",
        "marketing_seller_price",
        "retail_price",
        "premium_price",
        "min_price",
        "vat",
        "currency",
        "available",
        "timestamp",
        "error",
        "error_type"
    ]
    
    # Добавляем остальные поля в конец
    # product_id всегда должен быть первым, даже если его нет в данных
    ordered_fields = ["product_id"] if "product_id" not in all_fields else []
    ordered_fields.extend([f for f in field_order if f in all_fields and f != "product_id"])
    ordered_fields.extend([f for f in sorted(all_fields) if f not in ordered_fields])
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=ordered_fields)
        writer.writeheader()
        
        for product_id, data in results.items():
            if not include_errors and "error" in data:
                continue
            
            row = {"product_id": product_id}
            if isinstance(data, dict):
                row.update(data)
            else:
                row["value"] = str(data)
            
            writer.writerow(row)
    
    logger.info(f"Результаты экспортированы в CSV: {output_file}")


def export_to_xlsx(
    results: Dict[str, Any],
    output_path: str,
    include_errors: bool = True
) -> None:
    """
    Экспортировать результаты в XLSX файл.
    
    Args:
        results: Словарь с результатами {product_id: price_data}
        output_path: Путь к выходному файлу
        include_errors: Включать ли товары с ошибками
    """
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl не установлен. Установите: pip install openpyxl")
    
    if not results:
        logger.warning("Нет данных для экспорта")
        return
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Цены товаров"
    
    # Определяем все возможные поля
    all_fields = set()
    for data in results.values():
        if isinstance(data, dict):
            all_fields.update(data.keys())
    
    # Порядок полей
    field_order = [
        "product_id",
        "offer_id",
        "matched_id",
        "price",
        "old_price",
        "marketing_seller_price",
        "retail_price",
        "premium_price",
        "min_price",
        "vat",
        "currency",
        "available",
        "timestamp",
        "error",
        "error_type"
    ]
    
    # Добавляем остальные поля в конец
    # product_id всегда должен быть первым, даже если его нет в данных
    ordered_fields = ["product_id"] if "product_id" not in all_fields else []
    ordered_fields.extend([f for f in field_order if f in all_fields and f != "product_id"])
    ordered_fields.extend([f for f in sorted(all_fields) if f not in ordered_fields])
    
    # Заголовки
    for col, field in enumerate(ordered_fields, 1):
        ws.cell(row=1, column=col, value=field)
    
    # Данные
    row_num = 2
    for product_id, data in results.items():
        if not include_errors and "error" in data:
            continue
        
        for col, field in enumerate(ordered_fields, 1):
            value = None
            if field == "product_id":
                value = product_id
            elif isinstance(data, dict):
                value = data.get(field)
            else:
                value = str(data) if col == 1 else None
            
            if value is not None:
                ws.cell(row=row_num, column=col, value=value)
        
        row_num += 1
    
    wb.save(output_file)
    logger.info(f"Результаты экспортированы в XLSX: {output_file}")


def export_results(
    results: Dict[str, Any],
    output_path: str,
    format: str = "csv",
    include_errors: bool = True
) -> None:
    """
    Экспортировать результаты в файл.
    
    Args:
        results: Словарь с результатами {product_id: price_data}
        output_path: Путь к выходному файлу
        format: Формат файла ("csv" или "xlsx")
        include_errors: Включать ли товары с ошибками
    """
    if format.lower() == "csv":
        export_to_csv(results, output_path, include_errors)
    elif format.lower() == "xlsx":
        export_to_xlsx(results, output_path, include_errors)
    else:
        raise ValueError(f"Неподдерживаемый формат: {format}")

