"""Скрипт для запуска приложения из корня проекта."""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Запускаем main
from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())



