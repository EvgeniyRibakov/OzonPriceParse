"""Selenium-агент для скачивания отчёта из Ozon Seller (на основе логики лида).

Изначально лидер использовал undetected_chromedriver, но на Python 3.12
он требует модуль ``distutils``, который удалён из стандартной библиотеки.
Чтобы не городить костыли, здесь используется обычный Selenium Chrome
через ``webdriver-manager`` с настройками, похожими на лидерский скрипт.
"""

import time
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.config.settings import Settings


class SeleniumAgent:
    """Selenium-агент для автоматизации Ozon Seller (на основе логики лида)."""

    def __init__(self, settings: Settings):
        """Инициализация агента."""
        self.settings = settings
        self.driver: Optional[webdriver.Chrome] = None
        self.downloads_dir = settings.downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_file_path: Optional[Path] = None

    def start_browser(self) -> None:
        """Запускает браузер с настройками для обхода детектирования (как у лида)."""
        logger.info("Запуск браузера (Selenium Chrome)...")

        options = webdriver.ChromeOptions()
        
        # OZON может блокировать headless режим - НЕ используем headless
        # options.add_argument("--headless")  # НЕ включаем!
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Настройка скачивания файлов
        prefs = {
            "download.default_directory": str(self.downloads_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        # Запускаем обычный Chrome через webdriver-manager
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)

        logger.success("Браузер запущен")

    def navigate_to_url(self, url: str) -> None:
        """Переход по URL."""
        logger.info(f"Переход по URL: {url}")
        if not self.driver:
            raise RuntimeError("Браузер не запущен. Вызовите start_browser() сначала.")
        
        self.driver.get(url)
        time.sleep(2)  # Даём время на загрузку
        logger.success(f"Переход выполнен: {url}")

    def wait_for_element(self, selector: str, description: str = "", timeout: int = 15) -> bool:
        """Ожидание появления элемента."""
        logger.info(f"Ожидание элемента: {description} ({selector})")
        if not self.driver:
            return False
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            logger.success(f"Элемент найден: {description}")
            return True
        except Exception as e:
            logger.warning(f"Элемент не найден: {description} ({selector}) - {e}")
            return False

    def click_button(self, selector: str, description: str = "") -> None:
        """Клик по кнопке."""
        logger.info(f"Клик по кнопке: {description} ({selector})")
        if not self.driver:
            raise RuntimeError("Браузер не запущен.")
        
        try:
            element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            time.sleep(1)  # Пауза перед кликом (как у лида)
            element.click()
            time.sleep(2)  # Пауза после клика
            logger.success(f"Клик выполнен: {description}")
        except Exception as e:
            logger.error(f"Ошибка при клике: {description} - {e}")
            raise

    def download_report(self, start_url: str) -> Optional[Path]:
        """Скачивает отчёт из Ozon Seller.
        
        Логика:
        1. Открывает страницу Seller
        2. Ждёт авторизации (или авторизуется вручную)
        3. Находит кнопку "Скачать шаблоны"
        4. Кликает и ждёт скачивания XLSX файла
        
        :param start_url: URL страницы с товарами в Seller
        :return: Путь к скачанному файлу или None
        """
        try:
            # Шаг 1: Запуск браузера
            self.start_browser()
            
            # Шаг 2: Переход на страницу
            self.navigate_to_url(start_url)
            
            # Шаг 3: Проверка авторизации (опционально - можно добавить логику с cookies)
            logger.info("Проверка авторизации...")
            time.sleep(3)  # Даём время на загрузку страницы
            
            # Шаг 4: Поиск и клик по кнопке "Скачать шаблоны"
            # Пробуем разные варианты селектора (Selenium не поддерживает :has-text, используем XPath)
            selectors = [
                (By.XPATH, "//span[contains(@class, 'c9r90-a2') and contains(text(), 'Скачать шаблоны')]"),
                (By.XPATH, "//span[contains(text(), 'Скачать шаблоны')]"),
                (By.XPATH, "//button[contains(text(), 'Скачать шаблоны')]"),
                (By.XPATH, "//a[contains(text(), 'Скачать шаблоны')]"),
                (By.CSS_SELECTOR, "span.c9r90-a2"),
            ]
            
            found = False
            for by, selector in selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    # Проверяем, что текст содержит "Скачать шаблоны"
                    if "Скачать шаблоны" in element.text:
                        time.sleep(1)
                        element.click()
                        time.sleep(2)
                        logger.success("Клик выполнен: Скачать шаблоны")
                        found = True
                        break
                except Exception:
                    continue
            
            if not found:
                logger.error("Кнопка 'Скачать шаблоны' не найдена!")
                return None
            
            # Шаг 5: Ожидание скачивания файла
            logger.info("Ожидание скачивания файла...")
            time.sleep(5)  # Даём время на начало скачивания
            
            # Ищем последний скачанный XLSX файл
            downloaded_files = list(self.downloads_dir.glob("*.xlsx"))
            if downloaded_files:
                # Сортируем по времени модификации (новейший первый)
                downloaded_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                latest_file = downloaded_files[0]
                
                # Проверяем, что файл действительно новый (скачался недавно)
                file_age = time.time() - latest_file.stat().st_mtime
                if file_age < 60:  # Файл создан менее минуты назад
                    self.downloaded_file_path = latest_file
                    logger.success(f"Файл скачан: {latest_file}")
                    return latest_file
                else:
                    logger.warning(f"Найден старый файл: {latest_file} (возраст: {file_age:.1f}с)")
            
            logger.warning("XLSX файл не найден в папке downloads")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании отчёта: {e}")
            import traceback
            traceback.print_exc()
            return None

    def close(self) -> None:
        """Закрытие браузера."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Браузер закрыт")
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера: {e}")

