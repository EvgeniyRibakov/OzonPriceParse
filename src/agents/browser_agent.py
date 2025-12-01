"""Агент для автоматизации браузера Ozon Seller (Selenium версия)."""
import os
import sys
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


class BrowserAgent:
    """Агент для автоматизации браузера с пошаговой логикой (Selenium)."""

    def __init__(self, settings: Settings):
        """Инициализация агента."""
        self.settings = settings
        self.driver: Optional[webdriver.Chrome] = None
        self.downloads_dir = settings.downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_file_path: Optional[Path] = None

    def _log_action(self, action: str, details: str = "", element: str = "") -> None:
        """Логирование действия с подробностями."""
        log_msg = f"Действие: {action}"
        if element:
            log_msg += f" | Элемент: {element}"
        if details:
            log_msg += f" | Детали: {details}"
        logger.info(log_msg)

    def start_browser(self) -> None:
        """Запуск браузера."""
        self._log_action("Запуск браузера", f"Тип: Chrome (Selenium)")
        
        options = webdriver.ChromeOptions()
        
        # OZON может блокировать headless режим - НЕ используем headless
        # options.add_argument("--headless=new")  # НЕ включаем!
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--window-size={self.settings.viewport_width},{self.settings.viewport_height}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Убираем признаки автоматизации
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Настройка скачивания файлов
        prefs = {
            "download.default_directory": str(self.downloads_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)
        
        # User-Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Убираем признаки автоматизации через JavaScript
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        self.driver.implicitly_wait(5)
        logger.success("Браузер запущен")

    def navigate_to_url(self, url: str) -> None:
        """Переход по URL."""
        self._log_action("Переход по URL", url)
        if not self.driver:
            raise RuntimeError("Браузер не запущен. Вызовите start_browser() сначала.")
        
        self.driver.get(url)
        time.sleep(self.settings.delay_page_load)
        logger.success(f"Переход выполнен: {url}")

    def wait_for_element(
        self, selector: str, description: str = "", timeout: int = 15, by: By = By.CSS_SELECTOR
    ) -> bool:
        """Ожидание появления элемента."""
        self._log_action("Ожидание элемента", description, selector)
        if not self.driver:
            return False
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.success(f"Элемент найден: {description}")
            return True
        except Exception as e:
            logger.warning(f"Элемент не найден: {description} ({selector}) - {e}")
            return False

    def click_button(
        self, selector: str, description: str = "", by: By = By.CSS_SELECTOR, wait_for_navigation: bool = False
    ) -> None:
        """Клик по кнопке с задержками."""
        self._log_action("Клик по кнопке", description, selector)
        if not self.driver:
            raise RuntimeError("Браузер не запущен.")
        
        time.sleep(self.settings.delay_before_click)
        
        try:
            element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((by, selector))
            )
            element.click()
            time.sleep(self.settings.delay_after_click)
            
            if wait_for_navigation:
                time.sleep(self.settings.delay_page_load)
            
            logger.success(f"Клик выполнен: {description}")
        except Exception as e:
            logger.error(f"Ошибка при клике: {description} - {e}")
            raise

    def fill_input(
        self, selector: str, value: str, description: str = "", by: By = By.CSS_SELECTOR
    ) -> None:
        """Заполнение поля ввода с человеческими задержками."""
        self._log_action("Заполнение поля", description, selector)
        if not self.driver:
            raise RuntimeError("Браузер не запущен.")
        
        time.sleep(self.settings.delay_before_type)
        
        try:
            element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((by, selector))
            )
            element.click()
            time.sleep(0.3)
            
            # Очищаем поле
            element.clear()
            time.sleep(0.2)
            
            # Вводим текст
            element.send_keys(value)
            time.sleep(self.settings.delay_after_type)
            
            logger.success(f"Поле заполнено: {description}")
        except Exception as e:
            logger.error(f"Ошибка при заполнении поля: {description} - {e}")
            raise

    def get_user_input(self, prompt: str) -> str:
        """Запрос ввода от пользователя."""
        logger.warning(f"ТРЕБУЕТСЯ ВВОД ОТ ПОЛЬЗОВАТЕЛЯ: {prompt}")
        print(f"\n{'='*60}")
        print(f"ВНИМАНИЕ: {prompt}")
        print(f"{'='*60}")
        user_input = input("Введите код и нажмите Enter: ").strip()
        logger.info(f"Пользователь ввел: {user_input[:2]}** (скрыто)")
        return user_input

    def open_file(self, filepath: Path) -> None:
        """Открывает файл в системе."""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # macOS/Linux
                os.system(f'open "{filepath}"' if sys.platform == 'darwin' else f'xdg-open "{filepath}"')
            logger.success(f"Файл открыт: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка при открытии файла: {e}")

    def execute_flow(self, start_url: str) -> Optional[Path]:
        """Выполнение основного потока работы (по алгоритму из context_of_project)."""
        try:
            # Шаг 1: Запуск браузера
            self.start_browser()

            # Шаг 2: Переход по начальной ссылке
            self.navigate_to_url(start_url)

            # Шаг 3: Проверка и нажатие кнопки "Войти" (если требуется)
            # Селектор: <span class="c9r90-a2">Войти</span>
            login_button_xpath = "//span[contains(@class, 'c9r90-a2') and contains(text(), 'Войти')]"
            if self.wait_for_element(
                login_button_xpath, "Кнопка 'Войти'", timeout=5, by=By.XPATH
            ):
                self.click_button(
                    login_button_xpath,
                    "Кнопка 'Войти'",
                    by=By.XPATH,
                    wait_for_navigation=True,
                )

            # Шаг 4: Ввод номера телефона
            # Селектор: <input autocomplete="off" type="tel" name="autocomplete" ...>
            phone_input_selector = 'input[type="tel"][name="autocomplete"]'
            self.wait_for_element(phone_input_selector, "Поле ввода телефона")
            self.fill_input(
                phone_input_selector,
                self.settings.phone_number,
                "Номер телефона",
            )

            # Нажимаем кнопку "Войти" после ввода телефона (чтобы отправить код)
            # Селектор: <button type="submit" class="b25_5_1-a0 ..."><div class="b25_5_1-a"></div></button>
            submit_phone_selector = 'button[type="submit"].b25_5_1-a0'
            # Альтернативный селектор через внутренний div: div.b25_5_1-a
            if self.wait_for_element(submit_phone_selector, "Кнопка 'Войти'", timeout=5):
                self.click_button(
                    submit_phone_selector,
                    "Кнопка 'Войти' после ввода телефона",
                    wait_for_navigation=True,
                )
            
            # Ждём, пока появится либо поле для кода, либо страница с QR-кодом
            time.sleep(2.0)

            # Шаг 5: Проверяем, появилась ли страница с QR-кодом (нужно "Войти другим способом")
            # Селектор: <div class="ga5_3_10-a2 tsBodyControl500Medium">Войти другим способом</div>
            different_way_xpath = "//div[contains(@class, 'ga5_3_10-a2') and contains(text(), 'Войти другим способом')]"
            if self.wait_for_element(
                different_way_xpath, "Кнопка 'Войти другим способом'", timeout=5, by=By.XPATH
            ):
                self.click_button(
                    different_way_xpath,
                    "Войти другим способом",
                    by=By.XPATH,
                    wait_for_navigation=True,
                )
                time.sleep(2.0)

            # Шаг 6: Ввод кода из пуш-уведомления
            # Селектор: <input autocomplete="off" inputmode="numeric" type="number" name="otp" ...>
            otp_input_selector = 'input[name="otp"][type="number"]'
            self.wait_for_element(otp_input_selector, "Поле ввода кода OTP")
            
            # Запрашиваем код у пользователя (код уже должен быть отправлен после нажатия "Войти")
            otp_code = self.get_user_input(
                "Введите код из пуш-уведомления (6 цифр)"
            )
            self.fill_input(otp_input_selector, otp_code, "Код из пуш-уведомления")

            # Ожидаем автоматической отправки или ищем кнопку подтверждения
            time.sleep(2.0)

            # Шаг 7: Обработка страницы "Давайте убедимся, что это вы" (если требуется)
            # Проверяем, появилась ли страница проверки с нового устройства
            verify_page_xpath = "//span[contains(text(), 'Давайте убедимся, что это вы')]"
            if self.wait_for_element(
                verify_page_xpath, "Страница проверки 'Давайте убедимся, что это вы'", timeout=5, by=By.XPATH
            ):
                # Нажимаем кнопку "Войти" на странице проверки
                # Селектор: <button type="submit" class="b25_5_1-a0 ..."><div class="b25_5_1-a"></div></button>
                verify_login_selector = 'button[type="submit"].b25_5_1-a0'
                if self.wait_for_element(verify_login_selector, "Кнопка 'Войти' на странице проверки", timeout=5):
                    self.click_button(
                        verify_login_selector,
                        "Кнопка 'Войти' на странице проверки",
                        wait_for_navigation=True,
                    )
                    time.sleep(2.0)

            # Шаг 8: Обработка дополнительной проверки - ввод кода с email (если требуется)
            # Селектор: <input autocomplete="off" inputmode="numeric" type="number" name="extraOtp" ...>
            extra_otp_selector = 'input[name="extraOtp"][type="number"]'
            if self.wait_for_element(
                extra_otp_selector, "Поле дополнительного кода", timeout=5
            ):
                # Ввод кода
                self.wait_for_element(extra_otp_selector, "Поле дополнительного кода")
                extra_otp_code = self.get_user_input(
                    "Введите код, отправленный на email (6 цифр)"
                )
                self.fill_input(
                    extra_otp_selector, extra_otp_code, "Дополнительный код"
                )
                time.sleep(2.0)

            # Шаг 8: Ожидание загрузки страницы товаров
            time.sleep(3.0)

            # Шаг 9: Поиск и нажатие кнопки "Скачать шаблоны"
            # Селектор: <span class="c9r90-a2">Скачать шаблоны</span>
            download_button_xpath = "//span[contains(@class, 'c9r90-a2') and contains(text(), 'Скачать шаблоны')]"
            self.wait_for_element(
                download_button_xpath, "Кнопка 'Скачать шаблоны'", timeout=15, by=By.XPATH
            )
            
            # Сбрасываем путь к файлу перед кликом
            self.downloaded_file_path = None
            
            # Запоминаем время перед кликом (для поиска нового файла)
            time_before_click = time.time()
            
            # Кликаем по кнопке
            self.click_button(
                download_button_xpath, "Скачать шаблоны", by=By.XPATH, wait_for_navigation=False
            )

            # Шаг 10: Ожидание скачивания файла
            logger.info("Ожидание скачивания файла...")
            time.sleep(5)  # Даём время на начало скачивания
            
            # Ищем последний скачанный XLSX файл
            max_wait_time = 30  # Максимальное время ожидания (секунды)
            wait_interval = 1  # Интервал проверки (секунды)
            waited = 0
            
            while waited < max_wait_time:
                downloaded_files = list(self.downloads_dir.glob("*.xlsx"))
                if downloaded_files:
                    # Сортируем по времени модификации (новейший первый)
                    downloaded_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    latest_file = downloaded_files[0]
                    
                    # Проверяем, что файл действительно новый (скачался после клика)
                    file_mtime = latest_file.stat().st_mtime
                    if file_mtime >= time_before_click:
                        self.downloaded_file_path = latest_file
                        logger.success(f"Файл скачан: {latest_file}")
                        
                        # Открываем файл
                        self.open_file(latest_file)
                        return latest_file
                
                time.sleep(wait_interval)
                waited += wait_interval
                logger.debug(f"Ожидание скачивания... ({waited}/{max_wait_time}с)")
            
            logger.warning("XLSX файл не найден в папке downloads после ожидания")
            return None

        except Exception as e:
            logger.error(f"ОШИБКА В ПРОЦЕССЕ ВЫПОЛНЕНИЯ: {e}")
            logger.exception("Детали ошибки:")
            raise

    def close(self) -> None:
        """Закрытие браузера."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Браузер закрыт")
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера: {e}")
