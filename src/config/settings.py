"""Настройки приложения."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Ozon Seller
    ozon_start_url: str = "https://seller.ozon.ru/app/products"
    phone_number: str = "+79966444210"

    # Задержки (в секундах) для имитации человеческого поведения
    delay_before_click: float = 1.5  # Задержка перед кликом
    delay_after_click: float = 2.0  # Задержка после клика
    delay_before_type: float = 0.8  # Задержка перед вводом текста
    delay_after_type: float = 1.2  # Задержка после ввода текста
    delay_between_keys: float = 0.1  # Задержка между нажатиями клавиш
    delay_page_load: float = 3.0  # Задержка после загрузки страницы

    # Пути
    downloads_dir: Path = Path("downloads")
    logs_dir: Path = Path("logs")

    # Браузер
    headless: bool = False  # Всегда видимый браузер
    browser_type: str = "chromium"  # chromium, firefox, webkit
    viewport_width: int = 1920
    viewport_height: int = 1080

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

