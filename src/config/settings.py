"""Настройки приложения."""
import os
import sys
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Ozon Seller
    ozon_start_url: str = "https://seller.ozon.ru/app/products"  # Может содержать токен: https://seller.ozon.ru/app/products?token=...
    phone_number: str = ""  # Должен быть указан в .env файле

    # Ozon Statistics API (цены товаров /statistics/v1/price)
    ozon_client_id: str | None = None
    ozon_api_key: str | None = None
    # Базовый URL берём у Seller API, а дальше используем префикс /statistics
    ozon_api_base_url: str = "https://api-seller.ozon.ru"

    # Задержки (в секундах) для имитации человеческого поведения
    delay_before_click: float = 1.5  # Задержка перед кликом
    delay_after_click: float = 2.0  # Задержка после клика
    delay_before_type: float = 0.8  # Задержка перед вводом текста
    delay_after_type: float = 1.2  # Задержка после ввода текста
    delay_between_keys: float = 0.1  # Задержка между нажатиями клавиш
    delay_page_load: float = 3.0  # Задержка после загрузки страницы

    # Пути (относительные пути от корня проекта - универсальные для всех устройств)
    downloads_dir: Path = Path("downloads")
    logs_dir: Path = Path("logs")

    # Браузер
    headless: bool = False  # Всегда видимый браузер
    browser_type: str = "chromium"  # chromium, firefox, webkit
    viewport_width: int = 1920
    viewport_height: int = 1080
    # Профиль Chrome для сохранения авторизации
    chrome_user_data_dir: Path | None = None  # Путь к папке User Data Chrome (автоматически определяется, если не указан)
    chrome_profile_name: str = "Default"  # Имя профиля (Default, Profile 1, и т.д.)
    
    # Google Sheets интеграция
    upload_to_google_sheets: bool = False  # Загружать ли файл в Google Sheets
    google_sheets_url: str | None = None  # URL существующей Google таблицы для загрузки данных
    google_sheets_credentials_path: str | None = None  # Путь к JSON файлу с credentials для Google Sheets API
    google_sheets_spreadsheet_id: str | None = None  # ID Google таблицы (извлекается из URL автоматически)
    
    # Telegram бот
    telegram_bot_token: str | None = None  # Токен бота от @BotFather
    telegram_bot_password: str | None = None  # Пароль для доступа к боту
    
    @field_validator('telegram_bot_password', mode='before')
    @classmethod
    def validate_password(cls, v):
        """Валидация пароля - убираем пробелы и проверяем, что не пустой."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator('upload_to_google_sheets', mode='before')
    @classmethod
    def convert_bool(cls, v):
        """Конвертирует строку в булево значение."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    @field_validator('chrome_user_data_dir', mode='before')
    @classmethod
    def convert_path(cls, v):
        """Конвертирует строку в Path или определяет стандартный путь."""
        if v is None or v == "":
            # Автоматически определяем стандартный путь для текущей ОС
            if os.name == 'nt':  # Windows
                local_appdata = os.getenv('LOCALAPPDATA')
                if local_appdata:
                    return Path(local_appdata) / "Google" / "Chrome" / "User Data"
                # Fallback на стандартный путь
                return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            elif sys.platform == 'darwin':  # macOS
                return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
            else:  # Linux
                return Path.home() / ".config" / "google-chrome"
        
        if isinstance(v, str):
            # Поддержка переменных окружения Windows (%LOCALAPPDATA%)
            if v.startswith('%') and v.endswith('%'):
                env_var = v[1:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    return Path(env_value) / "Google" / "Chrome" / "User Data"
            # Поддержка ~ для домашней директории
            if v.startswith('~'):
                return Path(v).expanduser()
            return Path(os.path.expandvars(v))  # Поддержка переменных окружения
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False




