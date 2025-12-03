"""Утилиты для бота."""
from pathlib import Path
from typing import Optional


def format_logs(log_file: Path, lines: int = 50) -> str:
    """Форматирование логов для отправки в Telegram."""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Берём последние N строк
        last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return ''.join(last_lines)
    except Exception as e:
        return f"Ошибка при чтении логов: {e}"


def get_last_log_file() -> Optional[Path]:
    """Получение последнего файла лога."""
    from src.config.settings import Settings
    settings = Settings()
    logs_dir = Path(settings.logs_dir)
    
    if not logs_dir.exists():
        return None
    
    # Ищем файлы логов
    log_files = list(logs_dir.glob("*.log"))
    if not log_files:
        return None
    
    # Сортируем по времени модификации
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return log_files[0]
