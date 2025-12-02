"""Агент для автоматизации браузера Ozon Seller (Selenium версия)."""
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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
        
        # Использование профиля Chrome для сохранения авторизации
        if self.settings.chrome_user_data_dir:
            user_data_path = Path(self.settings.chrome_user_data_dir)
            # Проверяем существование пути (используем os.path.exists для лучшей совместимости с Windows)
            import os
            path_str = str(user_data_path.absolute())
            if os.path.exists(path_str):
                # Используем абсолютный путь в кавычках для Windows (на случай пробелов в пути)
                options.add_argument(f'--user-data-dir={path_str}')
                options.add_argument(f"--profile-directory={self.settings.chrome_profile_name}")
                logger.info(f"Используется профиль Chrome: {path_str} / {self.settings.chrome_profile_name}")
                
                # Проверяем, что папка профиля существует
                profile_path = user_data_path / self.settings.chrome_profile_name
                if os.path.exists(str(profile_path.absolute())):
                    logger.success(f"Папка профиля найдена: {profile_path}")
                else:
                    logger.warning(f"Папка профиля не найдена: {profile_path}")
            else:
                logger.warning(f"Путь к профилю Chrome не существует: {path_str}")
                logger.info(f"Попробуйте использовать полный путь или проверьте, что папка не скрыта")
        
        # Убираем признаки автоматизации
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Настройка скачивания файлов
        # ВАЖНО: При использовании профиля Chrome может игнорировать эти настройки
        # и использовать папку загрузок из профиля пользователя
        downloads_path = str(self.downloads_dir.absolute())
        # Убеждаемся, что папка существует
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        prefs = {
            "download.default_directory": downloads_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1,  # Разрешить автоматические загрузки
        }
        options.add_experimental_option("prefs", prefs)
        logger.info(f"Настроена папка для скачивания: {downloads_path}")
        
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
        self, selector: str, description: str = "", timeout: int = 15, by: By = By.CSS_SELECTOR, silent: bool = False
    ) -> bool:
        """Ожидание появления элемента."""
        if not silent:
            self._log_action("Ожидание элемента", description, selector)
        if not self.driver:
            return False
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            if not silent:
                logger.success(f"Элемент найден: {description}")
            return True
        except Exception as e:
            if not silent:
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
                EC.presence_of_element_located((by, selector))
            )
            
            # Прокручиваем к элементу, чтобы он был виден
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)  # Небольшая задержка после прокрутки
            
            # Пробуем обычный клик
            try:
                element.click()
            except Exception as click_error:
                # Если обычный клик не работает (элемент перекрыт), используем JavaScript клик
                logger.warning(f"Обычный клик не сработал, используем JavaScript клик: {click_error}")
                self.driver.execute_script("arguments[0].click();", element)
            
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
        """Выполнение основного потока работы (по алгоритму из context_of_project).
        
        Автоматически определяет текущий этап и пропускает уже пройденные шаги.
        """
        # Переменная для хранения названия выбранного шаблона (используется при поиске файла)
        selected_template_name = None
        
        try:
            # Шаг 1: Запуск браузера
            self.start_browser()

            # Шаг 2: Переход по начальной ссылке
            self.navigate_to_url(start_url)
            
            logger.info("="*60)
            logger.info("ОПРЕДЕЛЕНИЕ ТЕКУЩЕГО ЭТАПА")
            logger.info("="*60)
            logger.info("Проверяем этапы авторизации... (если уже авторизованы, этапы будут пропущены)")

            # Шаг 3: Проверка и нажатие кнопки "Войти" (если требуется)
            # Селектор: <span class="c9r90-a2">Войти</span>
            login_button_xpath = "//span[contains(@class, 'c9r90-a2') and contains(text(), 'Войти')]"
            if self.wait_for_element(
                login_button_xpath, "Кнопка 'Войти'", timeout=3, by=By.XPATH, silent=True
            ):
                logger.info("✓ Этап 3: Найдена кнопка 'Войти', выполняем клик")
                self.click_button(
                    login_button_xpath,
                    "Кнопка 'Войти'",
                    by=By.XPATH,
                    wait_for_navigation=True,
                )
            else:
                logger.info("→ Этап 3 пропущен: кнопка 'Войти' не найдена (возможно, уже авторизованы)")

            # Шаг 4: Ввод номера телефона (проверяем, нужен ли этот этап)
            # Селектор: <input autocomplete="off" type="tel" name="autocomplete" ...>
            phone_input_selector = 'input[type="tel"][name="autocomplete"]'
            if self.wait_for_element(phone_input_selector, "Поле ввода телефона", timeout=3, silent=True):
                logger.info("✓ Этап 4: Найдено поле ввода телефона, выполняем ввод")
                self.fill_input(
                phone_input_selector,
                self.settings.phone_number,
                "Номер телефона",
            )

                # Нажимаем кнопку "Войти" после ввода телефона (чтобы отправить код)
                # Селектор: <button type="submit" class="b25_5_1-a0 ..."><div class="b25_5_1-a"></div></button>
                submit_phone_selector = 'button[type="submit"].b25_5_1-a0'
                # Альтернативный селектор через внутренний div: div.b25_5_1-a
                if self.wait_for_element(submit_phone_selector, "Кнопка 'Войти'", timeout=3, silent=True):
                    self.click_button(
                        submit_phone_selector,
                        "Кнопка 'Войти' после ввода телефона",
                        wait_for_navigation=True,
                    )
                
                # Ждём, пока появится либо поле для кода, либо страница с QR-кодом
                time.sleep(2.0)
            else:
                logger.info("→ Этап 4 пропущен: поле ввода телефона не найдено (возможно, уже авторизованы)")

            # Шаг 5: Проверяем, появилась ли страница с QR-кодом
            # Используем вход по QR-коду (универсально для всех сотрудников)
            qr_success = False  # Флаг успешного сканирования QR-кода
            qr_page_xpath = "//span[contains(text(), 'Вход по QR-коду')]"
            if self.wait_for_element(
                qr_page_xpath, "Страница 'Вход по QR-коду'", timeout=3, by=By.XPATH, silent=True
            ):
                logger.info("✓ Этап 5: Найдена страница входа по QR-коду")
                logger.info("Обнаружена страница входа по QR-коду")
                
                # Ждём появления QR-кода на странице
                qr_code_selector = 'div.u2p_35 img.b95_3_4-a'
                if self.wait_for_element(qr_code_selector, "QR-код", timeout=10):
                    logger.success("QR-код найден на странице")
                    
                    # Показываем инструкцию пользователю
                    print("\n" + "="*60)
                    print("ВХОД ПО QR-КОДУ")
                    print("="*60)
                    print("Отсканируйте QR-код в приложении Ozon на вашем телефоне")
                    print("и подтвердите вход в приложении.")
                    print("="*60 + "\n")
                    
                    # Ждём, пока пользователь отсканирует QR-код и подтвердит вход
                    # Проверяем успешную авторизацию по переходу на страницу товаров
                    # или исчезновению страницы с QR-кодом
                    logger.info("Ожидание сканирования QR-кода пользователем...")
                    
                    max_wait_time = 120  # Максимальное время ожидания: 2 минуты
                    check_interval = 2  # Проверяем каждые 2 секунды
                    waited_time = 0
                    
                    while waited_time < max_wait_time:
                        try:
                            # Проверяем, исчезла ли страница с QR-кодом
                            qr_page_present = self.wait_for_element(
                                qr_page_xpath, "", timeout=1, by=By.XPATH, silent=True
                            )
                            
                            # Проверяем, появилась ли страница товаров
                            products_page_indicator = "//span[contains(text(), 'Скачать шаблоны')]"
                            products_page_present = self.wait_for_element(
                                products_page_indicator, "", timeout=1, by=By.XPATH, silent=True
                            )
                            
                            if not qr_page_present or products_page_present:
                                logger.success("QR-код успешно отсканирован! Авторизация прошла.")
                                qr_success = True
                                break
                                
                        except Exception:
                            # Если произошла ошибка при проверке, продолжаем ждать
                            pass
                        
                        time.sleep(check_interval)
                        waited_time += check_interval
                        
                        # Показываем прогресс каждые 10 секунд
                        if waited_time % 10 == 0:
                            logger.info(f"Ожидание сканирования QR-кода... ({waited_time}/{max_wait_time} сек)")
                    
                    if waited_time >= max_wait_time:
                        logger.warning("Превышено время ожидания сканирования QR-кода")
                        raise TimeoutError("QR-код не был отсканирован в течение отведённого времени")
                    
                    time.sleep(2.0)
                else:
                    logger.warning("QR-код не найден на странице, переходим к альтернативному способу")
                    # Если QR-код не найден, пробуем альтернативный способ
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

            else:
                logger.info("→ Этап 5 пропущен: страница QR-кода не найдена (возможно, уже авторизованы)")

            # Шаг 6: Ввод кода из пуш-уведомления (если не использовали QR-код)
            if not qr_success:
                # Селектор: <input autocomplete="off" inputmode="numeric" type="number" name="otp" ...>
                otp_input_selector = 'input[name="otp"][type="number"]'
                if self.wait_for_element(otp_input_selector, "Поле ввода кода OTP", timeout=3, silent=True):
                    logger.info("✓ Этап 6: Найдено поле ввода OTP, запрашиваем код")
                    # Запрашиваем код у пользователя (код уже должен быть отправлен после нажатия "Войти")
                    otp_code = self.get_user_input(
                        "Введите код из пуш-уведомления (6 цифр)"
                    )
                    self.fill_input(otp_input_selector, otp_code, "Код из пуш-уведомления")
                else:
                    logger.info("→ Этап 6 пропущен: поле ввода OTP не найдено (возможно, уже авторизованы)")

            # Ожидаем автоматической отправки или ищем кнопку подтверждения
            time.sleep(2.0)

            # Шаг 7: Обработка страницы "Давайте убедимся, что это вы" (если требуется)
            # Проверяем, появилась ли страница проверки с нового устройства
            verify_page_xpath = "//span[contains(text(), 'Давайте убедимся, что это вы')]"
            if self.wait_for_element(
                verify_page_xpath, "Страница проверки 'Давайте убедимся, что это вы'", timeout=3, by=By.XPATH, silent=True
            ):
                logger.info("✓ Этап 7: Найдена страница проверки, выполняем действия")
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

            else:
                logger.info("→ Этап 7 пропущен: страница проверки не найдена (возможно, уже авторизованы)")

            # Шаг 8: Обработка дополнительной проверки - ввод кода с email (если требуется)
            # Селектор: <input autocomplete="off" inputmode="numeric" type="number" name="extraOtp" ...>
            extra_otp_selector = 'input[name="extraOtp"][type="number"]'
            if self.wait_for_element(
                extra_otp_selector, "Поле дополнительного кода", timeout=3, silent=True
            ):
                logger.info("✓ Этап 8: Найдено поле дополнительного кода, запрашиваем код")
                # Ввод кода
                self.wait_for_element(extra_otp_selector, "Поле дополнительного кода")
                extra_otp_code = self.get_user_input(
                    "Введите код, отправленный на email (6 цифр)"
                )
                self.fill_input(
                    extra_otp_selector, extra_otp_code, "Дополнительный код"
                )
                time.sleep(2.0)
            else:
                logger.info("→ Этап 8 пропущен: поле дополнительного кода не найдено (возможно, уже авторизованы)")

            # Шаг 9: Ожидание загрузки страницы товаров и проверка, что мы на правильной странице
            logger.info("="*60)
            logger.info("ПРОВЕРКА: Находимся ли мы на странице товаров?")
            logger.info("="*60)
            time.sleep(2.0)

            # Шаг 10: Поиск и нажатие кнопки "Скачать шаблоны"
            # Селектор: <span class="c9r90-a2">Скачать шаблоны</span>
            download_button_xpath = "//span[contains(@class, 'c9r90-a2') and contains(text(), 'Скачать шаблоны')]"
            if not self.wait_for_element(
                download_button_xpath, "Кнопка 'Скачать шаблоны'", timeout=10, by=By.XPATH, silent=True
            ):
                logger.error("КРИТИЧЕСКАЯ ОШИБКА: Кнопка 'Скачать шаблоны' не найдена!")
                logger.error("Возможно, авторизация не завершена или мы не на странице товаров")
                raise RuntimeError("Не удалось найти кнопку 'Скачать шаблоны'. Проверьте, что вы авторизованы и находитесь на странице товаров.")
            
            logger.success("✓ Этап 10: Кнопка 'Скачать шаблоны' найдена, продолжаем работу")
            
            # Кликаем по кнопке "Скачать шаблоны"
            self.click_button(
                download_button_xpath, "Скачать шаблоны", by=By.XPATH, wait_for_navigation=False
            )
            
            # Ждём появления выпадающего списка
            time.sleep(2.0)

            # Шаг 10: Нажатие на выпадающий список
            # Селектор: <div class="c8s90-b3"> с input placeholder="Выберите шаблон"
            # Пробуем несколько вариантов селекторов
            dropdown_selectors = [
                # Вариант 1: По placeholder
                ('input[placeholder="Выберите шаблон"]', By.CSS_SELECTOR),
                # Вариант 2: По классу div
                ('div.c8s90-b3', By.CSS_SELECTOR),
                # Вариант 3: По классу input
                ('input.c8s90-d7', By.CSS_SELECTOR),
                # Вариант 4: По XPath с placeholder
                ('//input[@placeholder="Выберите шаблон"]', By.XPATH),
            ]
            
            dropdown_clicked = False
            for selector, by_type in dropdown_selectors:
                try:
                    if self.wait_for_element(selector, "Выпадающий список", timeout=3, by=by_type):
                        # Пробуем кликнуть по элементу
                        element = self.driver.find_element(by_type, selector)
                        # Если это input, пробуем кликнуть по родительскому div
                        if element.tag_name == 'input':
                            # Ищем родительский кликабельный div
                            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'c8s90-b3')]")
                            parent.click()
                        else:
                            element.click()
                        logger.success("Выпадающий список открыт")
                        dropdown_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Не удалось использовать селектор {selector}: {e}")
                    continue
            
            if not dropdown_clicked:
                logger.warning("Не удалось найти выпадающий список, пробуем альтернативный способ")
                # Альтернативный способ: ищем SVG внутри выпадающего списка
                try:
                    svg_xpath = "//svg[@class='sc790-a0']"
                    if self.wait_for_element(svg_xpath, "SVG выпадающего списка", timeout=3, by=By.XPATH):
                        svg_element = self.driver.find_element(By.XPATH, svg_xpath)
                        parent = svg_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'c8s90')]")
                        parent.click()
                        logger.success("Выпадающий список открыт (через SVG)")
                        dropdown_clicked = True
                except Exception as e:
                    logger.error(f"Не удалось открыть выпадающий список: {e}")
                    raise
            
            time.sleep(1.5)

            # Шаг 11: Выбор пункта "Цены товаров"
            # Селектор: <div class="c0s90-a3 c0s90-a5 table-500">Цены товаров</div>
            prices_option_xpath = "//div[contains(@class, 'c0s90-a3') and contains(@class, 'table-500') and contains(text(), 'Цены товаров')]"
            self.wait_for_element(
                prices_option_xpath, "Пункт 'Цены товаров'", timeout=10, by=By.XPATH
            )
            
            # Получаем название выбранного шаблона для поиска файла
            template_element = self.driver.find_element(By.XPATH, prices_option_xpath)
            selected_template_name = template_element.text.strip()
            logger.info(f"Выбран шаблон: '{selected_template_name}'")
            
            self.click_button(
                prices_option_xpath, "Цены товаров", by=By.XPATH, wait_for_navigation=False
            )
            
            time.sleep(1.0)

            # Шаг 12: Нажатие на кнопку "Скачать"
            # Структура: <div class="c9r90-a0"><div class="c9r90-a1 c9r90-a2"><span class="c9r90-a2">Скачать</span></div></div>
            # ВАЖНО: Нужно кликать на родительский div.c9r90-a0, а не на span!
            # КРИТИЧНО: Нужно найти кнопку именно в модальном окне, а не "Скачать шаблоны" на главной странице!
            
            logger.info("="*60)
            logger.info("ПОИСК КНОПКИ 'СКАЧАТЬ' В МОДАЛЬНОМ ОКНЕ")
            logger.info("="*60)
            logger.info("Структура кнопки: <div class='c9r90-a0'><div class='c9r90-a1 c9r90-a2'><span>Скачать</span></div></div>")
            
            # Ждём, пока модальное окно полностью загрузится
            time.sleep(1.5)
            
            # Варианты селекторов (пробуем по порядку):
            # 1. Точный поиск: span с текстом ТОЧНО "Скачать" (не "Скачать шаблоны") внутри div.c9r90-a1.c9r90-a2
            download_xpath_1 = "//div[contains(@class, 'c9r90-a1') and contains(@class, 'c9r90-a2')]//span[contains(@class, 'c9r90-a2') and normalize-space(text())='Скачать']/ancestor::div[contains(@class, 'c9r90-a0')]"
            # 2. Поиск через родительский div.c9r90-a0, который содержит span с ТОЧНО текстом "Скачать"
            download_xpath_2 = "//div[contains(@class, 'c9r90-a0')][.//span[contains(@class, 'c9r90-a2') and normalize-space(text())='Скачать']]"
            # 3. Поиск span с текстом "Скачать" (но не "Скачать шаблоны"), затем поднимаемся к div.c9r90-a0
            download_xpath_3 = "//span[contains(@class, 'c9r90-a2') and normalize-space(text())='Скачать' and not(contains(text(), 'шаблоны'))]/ancestor::div[contains(@class, 'c9r90-a0')]"
            # 4. Поиск через div.c9r90-a1.c9r90-a2, который содержит span с текстом "Скачать"
            download_xpath_4 = "//div[contains(@class, 'c9r90-a1') and contains(@class, 'c9r90-a2')][.//span[normalize-space(text())='Скачать']]"
            # 5. Альтернативный: поиск всех div.c9r90-a0 и фильтрация по тексту
            download_xpath_5 = "//div[contains(@class, 'c9r90-a0')][.//span[normalize-space(text())='Скачать']]"
            
            element_found = False
            download_element = None
            used_selector = None
            
            # Пробуем найти элемент разными способами
            selectors_to_try = [
                (download_xpath_1, "XPath: div.c9r90-a1.c9r90-a2 -> span='Скачать' -> ancestor div.c9r90-a0", By.XPATH),
                (download_xpath_2, "XPath: div.c9r90-a0 с span='Скачать' (точное совпадение)", By.XPATH),
                (download_xpath_3, "XPath: span='Скачать' (без 'шаблоны') -> ancestor div.c9r90-a0", By.XPATH),
                (download_xpath_4, "XPath: div.c9r90-a1.c9r90-a2 с span='Скачать'", By.XPATH),
                (download_xpath_5, "XPath: div.c9r90-a0 с span='Скачать' (альтернативный)", By.XPATH),
            ]
            
            for selector, description, by_type in selectors_to_try:
                logger.info(f"Попытка найти кнопку: {description}")
                if self.wait_for_element(selector, f"Кнопка 'Скачать' ({description})", timeout=3, by=by_type, silent=True):
                    try:
                        elements = self.driver.find_elements(by_type, selector)
                        # Фильтруем элементы по тексту - ищем именно "Скачать", а не "Скачать шаблоны"
                        for elem in elements:
                            try:
                                text = elem.text.strip()
                                logger.info(f"  Проверяем элемент с текстом: '{text}'")
                                if text == "Скачать" or (text and "Скачать" in text and "шаблоны" not in text.lower()):
                                    download_element = elem
                                    element_found = True
                                    used_selector = description
                                    logger.success(f"✓ Кнопка 'Скачать' найдена: {description} (текст: '{text}')")
                                    break
                            except Exception as e:
                                logger.debug(f"  Ошибка при проверке элемента: {e}")
                                continue
                        
                        if element_found:
                            break
                    except Exception as e:
                        logger.warning(f"Элемент найден, но не удалось получить объект ({description}): {e}")
            
            if not element_found or not download_element:
                # Делаем скриншот для отладки
                try:
                    screenshot_path = self.downloads_dir / "debug_download_button_not_found.png"
                    self.driver.save_screenshot(str(screenshot_path))
                    logger.error(f"Скриншот сохранён: {screenshot_path}")
                    
                    # Пробуем найти все элементы с классом c9r90-a0 для отладки
                    try:
                        all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "div.c9r90-a0")
                        logger.info(f"Найдено элементов с классом c9r90-a0: {len(all_buttons)}")
                        for i, btn in enumerate(all_buttons[:5]):  # Показываем первые 5
                            try:
                                text = btn.text
                                logger.info(f"  Элемент {i+1}: текст='{text}', виден={btn.is_displayed()}")
                            except:
                                pass
                    except:
                        pass
                except:
                    pass
                raise RuntimeError("Не удалось найти кнопку 'Скачать'")
            
            # Проверяем видимость и кликабельность элемента
            logger.info("="*60)
            logger.info("ИНФОРМАЦИЯ О НАЙДЕННОМ ЭЛЕМЕНТЕ")
            logger.info("="*60)
            try:
                is_displayed = download_element.is_displayed()
                is_enabled = download_element.is_enabled()
                location = download_element.location
                size = download_element.size
                text = download_element.text
                tag_name = download_element.tag_name
                classes = download_element.get_attribute("class")
                
                logger.info(f"✓ Тег элемента: {tag_name}")
                logger.info(f"✓ Классы элемента: {classes}")
                logger.info(f"✓ Элемент виден: {is_displayed}")
                logger.info(f"✓ Элемент активен: {is_enabled}")
                logger.info(f"✓ Позиция: x={location['x']}, y={location['y']}")
                logger.info(f"✓ Размер: width={size['width']}, height={size['height']}")
                logger.info(f"✓ Текст элемента: '{text}'")
                logger.info(f"✓ Использованный селектор: {used_selector}")
                
                # КРИТИЧЕСКАЯ ПРОВЕРКА: Убеждаемся, что это правильная кнопка
                text_clean = text.strip() if text else ""
                if "шаблоны" in text_clean.lower():
                    logger.error(f"❌ ОШИБКА: Найден неправильный элемент с текстом '{text}' (содержит 'шаблоны')")
                    logger.error("Это кнопка 'Скачать шаблоны' на главной странице, а не 'Скачать' в модальном окне!")
                    logger.info("Пробуем найти правильную кнопку в модальном окне...")
                    
                    # Пробуем найти все кнопки с классом c9r90-a0 и фильтруем
                    all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "div.c9r90-a0")
                    logger.info(f"Найдено элементов div.c9r90-a0: {len(all_buttons)}")
                    
                    for i, btn in enumerate(all_buttons):
                        try:
                            btn_text = btn.text.strip()
                            logger.info(f"  Кнопка {i+1}: текст='{btn_text}', виден={btn.is_displayed()}")
                            if btn_text == "Скачать" or (btn_text and "Скачать" in btn_text and "шаблоны" not in btn_text.lower()):
                                download_element = btn
                                element_found = True
                                logger.success(f"✓ Найдена правильная кнопка 'Скачать' (кнопка {i+1})")
                                break
                        except Exception as e:
                            logger.debug(f"  Ошибка при проверке кнопки {i+1}: {e}")
                    
                    if not element_found:
                        raise RuntimeError("Не удалось найти кнопку 'Скачать' в модальном окне. Найден только элемент 'Скачать шаблоны'")
                elif text_clean != "Скачать":
                    logger.warning(f"⚠ ВНИМАНИЕ: Текст элемента '{text}' не точно 'Скачать', но продолжаем...")
                
            except Exception as e:
                logger.warning(f"Не удалось получить информацию об элементе: {e}")
            
            # Сбрасываем путь к файлу перед кликом
            self.downloaded_file_path = None
            
            # Запоминаем время перед кликом (для поиска нового файла)
            time_before_click = time.time()
            
            # Получаем список файлов ДО клика
            files_before = set(self.downloads_dir.glob("*.xlsx"))
            logger.info(f"Файлов XLSX в папке downloads ДО клика: {len(files_before)}")
            
            # Кликаем по кнопке "Скачать"
            logger.info("="*60)
            logger.info("НАЖАТИЕ НА КНОПКУ 'СКАЧАТЬ'")
            logger.info("="*60)
            
            try:
                # Прокручиваем к элементу
                logger.info("Прокрутка к элементу...")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", download_element)
                time.sleep(0.8)
                
                # Пробуем разные способы клика
                click_success = False
                
                # Способ 1: Обычный клик
                try:
                    logger.info("Способ 1: Обычный клик через Selenium...")
                    download_element.click()
                    logger.success("✓ Обычный клик выполнен успешно")
                    click_success = True
                except Exception as click_error:
                    logger.warning(f"Обычный клик не сработал: {click_error}")
                
                # Способ 2: JavaScript клик
                if not click_success:
                    try:
                        logger.info("Способ 2: JavaScript клик...")
                        self.driver.execute_script("arguments[0].click();", download_element)
                        logger.success("✓ JavaScript клик выполнен успешно")
                        click_success = True
                    except Exception as js_error:
                        logger.warning(f"JavaScript клик не сработал: {js_error}")
                
                # Способ 3: Клик через ActionChains
                if not click_success:
                    try:
                        logger.info("Способ 3: Клик через ActionChains...")
                        actions = ActionChains(self.driver)
                        actions.move_to_element(download_element).click().perform()
                        logger.success("✓ Клик через ActionChains выполнен успешно")
                        click_success = True
                    except Exception as action_error:
                        logger.warning(f"Клик через ActionChains не сработал: {action_error}")
                
                # Способ 4: JavaScript клик с принудительным удалением перекрывающих элементов
                if not click_success:
                    try:
                        logger.info("Способ 4: JavaScript клик с удалением перекрывающих элементов...")
                        # Удаляем перекрывающий элемент через JavaScript
                        self.driver.execute_script("""
                            var overlays = document.querySelectorAll('div.index_actionsContainer_ChnAG');
                            overlays.forEach(function(el) { el.style.display = 'none'; });
                        """)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].click();", download_element)
                        logger.success("✓ JavaScript клик с удалением перекрывающих элементов выполнен успешно")
                        click_success = True
                    except Exception as js_overlay_error:
                        logger.warning(f"JavaScript клик с удалением перекрывающих элементов не сработал: {js_overlay_error}")
                
                # Способ 5: Прямой вызов события click через JavaScript
                if not click_success:
                    try:
                        logger.info("Способ 5: Прямой вызов события click через JavaScript...")
                        self.driver.execute_script("""
                            var element = arguments[0];
                            var event = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            element.dispatchEvent(event);
                        """, download_element)
                        logger.success("✓ Прямой вызов события click выполнен успешно")
                        click_success = True
                    except Exception as event_error:
                        logger.warning(f"Прямой вызов события click не сработал: {event_error}")
                
                if not click_success:
                    raise RuntimeError("Все способы клика не сработали")
                
                # Ждём немного и проверяем, началось ли скачивание
                time.sleep(2)
                files_after = set(self.downloads_dir.glob("*.xlsx"))
                new_files = files_after - files_before
                if new_files:
                    logger.success(f"✓ Обнаружены новые файлы после клика: {[f.name for f in new_files]}")
                else:
                    logger.info("Новых файлов пока не обнаружено (это нормально, файл может скачиваться)")
                
                # Логируем текущий URL для отладки
                current_url = self.driver.current_url
                logger.info(f"Текущий URL после клика: {current_url}")
                
                # Шаг 12.5: Открытие файла через Chrome Downloads
                logger.info("="*60)
                logger.info("ОТКРЫТИЕ ФАЙЛА ЧЕРЕЗ CHROME DOWNLOADS")
                logger.info("="*60)
                
                try:
                    # Ждём немного, чтобы файл начал скачиваться
                    time.sleep(2)
                    
                    # Способ 1: Пробуем найти кнопку "Скачанные файлы" на панели инструментов
                    downloads_button_found = False
                    downloads_button_selectors = [
                        "//*[contains(text(), 'Скачанные файлы')]",
                        "//*[contains(text(), 'Downloads')]",
                        "//*[@title='Скачанные файлы']",
                        "//*[@title='Downloads']",
                        "//*[@aria-label='Скачанные файлы']",
                        "//*[@aria-label='Downloads']",
                        "//button[contains(@class, 'download')]",
                        "//a[contains(@href, 'downloads')]",
                    ]
                    
                    for selector in downloads_button_selectors:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, selector)
                            for btn in buttons:
                                try:
                                    if btn.is_displayed() and btn.is_enabled():
                                        logger.info(f"✓ Найдена кнопка 'Скачанные файлы': {btn.text or btn.get_attribute('title') or btn.get_attribute('aria-label')}")
                                        btn.click()
                                        downloads_button_found = True
                                        time.sleep(1.5)
                                        break
                                except:
                                    continue
                            if downloads_button_found:
                                break
                        except:
                            continue
                    
                    # Способ 2: Если кнопка не найдена, переходим напрямую на chrome://downloads/
                    if not downloads_button_found:
                        logger.info("Кнопка 'Скачанные файлы' не найдена, переходим на chrome://downloads/")
                        self.driver.get("chrome://downloads/")
                        time.sleep(3)  # Даём больше времени на загрузку страницы
                    
                    # Теперь ищем самый верхний (самый новый) файл на странице downloads
                    logger.info("Ищем самый новый файл на странице downloads...")
                    
                    # Страница chrome://downloads/ использует Shadow DOM, поэтому используем JavaScript
                    file_element = None
                    clicked = False
                    
                    # Способ 1: Используем JavaScript для работы с Shadow DOM на chrome://downloads/
                    try:
                        logger.info("Пробуем найти файл через JavaScript (Shadow DOM)...")
                        # JavaScript код для поиска первого .xlsx файла на странице downloads
                        # Ищем элемент с id="file-link" внутри Shadow DOM
                        click_result = self.driver.execute_script("""
                            // Ищем downloads-manager
                            var downloadsManager = document.querySelector('downloads-manager');
                            if (!downloadsManager) {
                                console.log('downloads-manager не найден');
                                return {success: false, error: 'downloads-manager not found'};
                            }
                            
                            // Получаем Shadow Root
                            var shadowRoot = downloadsManager.shadowRoot;
                            if (!shadowRoot) {
                                console.log('Shadow root downloads-manager не найден');
                                return {success: false, error: 'shadowRoot not found'};
                            }
                            
                            // Ищем downloads-list
                            var downloadsList = shadowRoot.querySelector('downloads-list');
                            if (!downloadsList) {
                                console.log('downloads-list не найден');
                                return {success: false, error: 'downloads-list not found'};
                            }
                            
                            // Получаем Shadow Root downloads-list
                            var listShadowRoot = downloadsList.shadowRoot;
                            if (!listShadowRoot) {
                                console.log('Shadow root downloads-list не найден');
                                return {success: false, error: 'listShadowRoot not found'};
                            }
                            
                            // Ищем все элементы download-item
                            var downloadItems = listShadowRoot.querySelectorAll('download-item');
                            if (!downloadItems || downloadItems.length === 0) {
                                console.log('download-item элементы не найдены');
                                return {success: false, error: 'download-items not found'};
                            }
                            
                            console.log('Найдено элементов download-item: ' + downloadItems.length);
                            
                            // Ищем первый файл с расширением .xlsx (самый верхний в списке)
                            for (var i = 0; i < downloadItems.length; i++) {
                                var item = downloadItems[i];
                                var itemShadowRoot = item.shadowRoot;
                                if (!itemShadowRoot) {
                                    console.log('Shadow root для download-item ' + i + ' не найден');
                                    continue;
                                }
                                
                                // Ищем элемент с id="file-link" - это ссылка на файл
                                var fileLink = itemShadowRoot.querySelector('#file-link');
                                if (!fileLink) {
                                    console.log('file-link не найден в элементе ' + i);
                                    continue;
                                }
                                
                                // Получаем название файла из атрибута title или текста
                                var fileName = fileLink.getAttribute('title') || fileLink.textContent || fileLink.innerText || '';
                                console.log('Найден файл ' + i + ': ' + fileName);
                                
                                // Проверяем, что это .xlsx файл
                                if (fileName.toLowerCase().includes('.xlsx')) {
                                    console.log('Найден .xlsx файл: ' + fileName);
                                    // Кликаем на элемент
                                    try {
                                        fileLink.click();
                                        console.log('Клик выполнен успешно');
                                        return {success: true, fileName: fileName, index: i};
                                    } catch (clickError) {
                                        console.log('Ошибка при клике: ' + clickError);
                                        // Пробуем через dispatchEvent
                                        try {
                                            var clickEvent = new MouseEvent('click', {
                                                bubbles: true,
                                                cancelable: true,
                                                view: window
                                            });
                                            fileLink.dispatchEvent(clickEvent);
                                            console.log('Клик через dispatchEvent выполнен');
                                            return {success: true, fileName: fileName, index: i};
                                        } catch (eventError) {
                                            console.log('Ошибка при dispatchEvent: ' + eventError);
                                            return {success: false, error: 'click failed', fileName: fileName};
                                        }
                                    }
                                }
                            }
                            
                            console.log('.xlsx файл не найден');
                            return {success: false, error: 'xlsx file not found'};
                        """)
                        
                        if click_result and click_result.get('success'):
                            logger.success(f"✓ Файл найден и открыт: {click_result.get('fileName', 'Unknown')}")
                            time.sleep(2)
                            return None
                        else:
                            logger.warning(f"⚠ Не удалось найти или открыть файл через JavaScript: {click_result.get('error', 'unknown error') if click_result else 'no result'}")
                    except Exception as e:
                        logger.warning(f"Ошибка при работе с Shadow DOM: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    
                    # Способ 2: Пробуем обычные селекторы (на случай, если Shadow DOM недоступен)
                    if not clicked:
                        logger.info("Пробуем обычные селекторы...")
                        file_selectors = [
                            "//*[contains(@class, 'download')]//*[contains(text(), '.xlsx')]",
                            "//*[contains(@id, 'download')]//*[contains(text(), '.xlsx')]",
                            "//*[contains(text(), '.xlsx')]",
                            f"//*[contains(text(), '{selected_template_name}')]",
                            "//a[contains(@href, '.xlsx')]",
                            "//*[@role='listitem']//*[contains(text(), '.xlsx')]",
                            "//download-item//*[contains(text(), '.xlsx')]",
                        ]
                        
                        for file_selector in file_selectors:
                            try:
                                file_elements = self.driver.find_elements(By.XPATH, file_selector)
                                if file_elements:
                                    # Берём первый элемент (обычно самый новый файл вверху списка)
                                    file_element = file_elements[0]
                                    logger.success(f"✓ Найден файл на странице downloads: {file_element.text}")
                                    break
                            except:
                                continue
                        
                        # Если не нашли по тексту, пробуем найти кликабельные элементы
                        if not file_element:
                            try:
                                # Ищем все кликабельные элементы на странице downloads
                                clickable_elements = self.driver.find_elements(By.XPATH, "//a | //button | //*[@role='button'] | //*[@onclick] | //*[@role='link']")
                                # Фильтруем те, что содержат .xlsx в тексте или атрибутах
                                for elem in clickable_elements:
                                    try:
                                        text = elem.text or elem.get_attribute('title') or elem.get_attribute('aria-label') or ''
                                        href = elem.get_attribute('href') or ''
                                        if '.xlsx' in text.lower() or '.xlsx' in href.lower() or (selected_template_name and selected_template_name in text):
                                            file_element = elem
                                            logger.success(f"✓ Найден кликабельный элемент с файлом: {text or href}")
                                            break
                                    except:
                                        continue
                            except Exception as e:
                                logger.debug(f"Ошибка при поиске кликабельных элементов: {e}")
                    
                    # Если нашли файл, кликаем на него
                    if file_element and not clicked:
                        try:
                            logger.info("Кликаем на самый новый файл...")
                            # Прокручиваем к элементу
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", file_element)
                            time.sleep(0.5)
                            
                            # Пробуем разные способы клика
                            clicked = False
                            
                            # Способ 1: Обычный клик
                            try:
                                file_element.click()
                                clicked = True
                                logger.success("✓ Клик на файл выполнен успешно")
                            except Exception as e:
                                logger.debug(f"Обычный клик не сработал: {e}")
                            
                            # Способ 2: JavaScript клик
                            if not clicked:
                                try:
                                    self.driver.execute_script("arguments[0].click();", file_element)
                                    clicked = True
                                    logger.success("✓ JavaScript клик на файл выполнен успешно")
                                except Exception as e:
                                    logger.debug(f"JavaScript клик не сработал: {e}")
                            
                            # Способ 3: Клик по родительскому элементу (если файл - это текст внутри ссылки)
                            if not clicked:
                                try:
                                    parent = file_element.find_element(By.XPATH, "./ancestor::a | ./ancestor::button | ./ancestor::*[@role='button'] | ./ancestor::*[@onclick]")
                                    parent.click()
                                    clicked = True
                                    logger.success("✓ Клик по родительскому элементу выполнен успешно")
                                except Exception as e:
                                    logger.debug(f"Клик по родительскому элементу не сработал: {e}")
                            
                            # Способ 4: Прямой вызов события click через JavaScript
                            if not clicked:
                                try:
                                    self.driver.execute_script("""
                                        var element = arguments[0];
                                        var event = new MouseEvent('click', {
                                            view: window,
                                            bubbles: true,
                                            cancelable: true
                                        });
                                        element.dispatchEvent(event);
                                    """, file_element)
                                    clicked = True
                                    logger.success("✓ Прямой вызов события click выполнен успешно")
                                except Exception as e:
                                    logger.debug(f"Прямой вызов события не сработал: {e}")
                            
                            if clicked:
                                logger.success("✓ Файл открыт из Chrome Downloads!")
                                time.sleep(2)  # Даём время на открытие файла
                                # Возвращаем None, так как файл уже открыт
                                return None
                            else:
                                logger.warning("⚠ Не удалось кликнуть на файл в Chrome Downloads")
                        except Exception as e:
                            logger.warning(f"Ошибка при клике на файл: {e}")
                    else:
                        logger.warning("⚠ Файл не найден на странице Chrome Downloads")
                        
                except Exception as e:
                    logger.warning(f"Ошибка при попытке открыть файл через Chrome Downloads: {e}")
                    logger.info("→ Продолжаем поиск файла в файловой системе...")
                
            except Exception as e:
                logger.error(f"Ошибка при клике на кнопку 'Скачать': {e}")
                # Делаем скриншот для отладки
                try:
                    screenshot_path = self.downloads_dir / "debug_download_click_error.png"
                    self.driver.save_screenshot(str(screenshot_path))
                    logger.error(f"Скриншот сохранён: {screenshot_path}")
                except:
                    pass
                raise

            # Шаг 13: Ожидание скачивания файла (30 секунд)
            logger.info("="*60)
            logger.info("ОЖИДАНИЕ СКАЧИВАНИЯ ФАЙЛА")
            logger.info("="*60)
            logger.info(f"Настроенная папка для скачивания: {self.downloads_dir.absolute()}")
            
            # Собираем все возможные папки для поиска файла
            # Chrome может игнорировать настройки prefs при использовании профиля пользователя
            search_dirs = [self.downloads_dir]
            
            def add_dir_if_exists(path: Path, description: str):
                """Добавляет папку в список поиска, если она существует."""
                if path.exists() and path not in search_dirs:
                    search_dirs.append(path)
                    logger.info(f"✓ Проверяем {description}: {path}")
            
            # 1. Стандартная папка загрузок Windows (через Path.home())
            add_dir_if_exists(Path.home() / "Downloads", "стандартную папку загрузок (Path.home())")
            
            # 2. Папка загрузок через переменную окружения USERPROFILE
            if os.name == 'nt':  # Windows
                user_profile = os.getenv('USERPROFILE')
                if user_profile:
                    add_dir_if_exists(Path(user_profile) / "Downloads", "папку загрузок из USERPROFILE")
                
                # 3. Пробуем получить реальную папку Downloads через реестр Windows (Shell Folders)
                try:
                    import winreg
                    # Читаем из реестра путь к папке Downloads
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                    )
                    downloads_path = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                    winreg.CloseKey(key)
                    if downloads_path:
                        add_dir_if_exists(Path(downloads_path), "папку загрузок из реестра Windows")
                except Exception as e:
                    logger.debug(f"Не удалось получить папку Downloads из реестра: {e}")
                
                # 4. Проверяем альтернативные пути (OneDrive, Documents/Downloads и т.д.)
                # Путь вида D:\Документы и файлы\Documents\Downloads
                user_profile = os.getenv('USERPROFILE') or str(Path.home())
                
                # Варианты путей для поиска:
                alternative_paths = [
                    Path(user_profile) / "Documents" / "Downloads",  # Documents/Downloads
                    Path(user_profile) / "Документы" / "Downloads",  # Русская версия Documents
                    Path(user_profile) / "Documents" / "Загрузки",  # Русская версия Downloads
                ]
                
                # 5. Проверяем все диски на наличие папки "Документы и файлы\Documents\Downloads"
                # Это может быть OneDrive или другая синхронизированная папка
                for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive_path = Path(f"{drive_letter}:") / "Документы и файлы" / "Documents" / "Downloads"
                    if drive_path.exists():
                        alternative_paths.append(drive_path)
                        logger.debug(f"Найдена альтернативная папка на диске {drive_letter}: {drive_path}")
                
                # 6. Проверяем также варианты с другими названиями
                for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                    variants = [
                        Path(f"{drive_letter}:") / "Documents" / "Downloads",
                        Path(f"{drive_letter}:") / "Документы" / "Downloads",
                        Path(f"{drive_letter}:") / "Documents" / "Загрузки",
                    ]
                    for variant in variants:
                        if variant.exists() and variant not in alternative_paths:
                            alternative_paths.append(variant)
                
                for alt_path in alternative_paths:
                    if alt_path.exists():
                        add_dir_if_exists(alt_path, "альтернативную папку загрузок")
            
            # 5. Папка загрузок из профиля Chrome (если используется профиль)
            if self.settings.chrome_user_data_dir:
                profile_downloads = self.settings.chrome_user_data_dir / self.settings.chrome_profile_name / "Downloads"
                add_dir_if_exists(profile_downloads, "папку загрузок профиля Chrome")
            
            # 6. Linux/macOS стандартные пути
            if os.name == 'posix':
                if sys.platform == 'darwin':  # macOS
                    add_dir_if_exists(Path.home() / "Downloads", "папку загрузок macOS")
                else:  # Linux
                    add_dir_if_exists(Path.home() / "Downloads", "папку загрузок Linux")
                    add_dir_if_exists(Path.home() / "Загрузки", "папку загрузок Linux (русская)")
            
            logger.info(f"Всего проверяем {len(search_dirs)} папок для поиска файла")
            
            # Формируем паттерн для поиска файла на основе названия шаблона и даты
            today_date = datetime.now().strftime("%d.%m.%Y")
            
            # Если название шаблона не было получено, используем значение по умолчанию
            if selected_template_name is None:
                selected_template_name = "Цены товаров"
                logger.warning(f"Название шаблона не было получено, используем значение по умолчанию: '{selected_template_name}'")
            
            # Экранируем специальные символы для regex
            template_name_escaped = re.escape(selected_template_name)
            # Паттерн: "Цены товаров_02.12.2025.xlsx" или "Цены товаров_02.12.2025 (1).xlsx"
            file_pattern = re.compile(
                rf"^{template_name_escaped}_{re.escape(today_date)}(?:\s*\(\d+\))?\.xlsx$",
                re.IGNORECASE
            )
            logger.info(f"Ищем файл по паттерну: '{selected_template_name}_{today_date}.xlsx' (с возможными вариантами (1), (2) и т.д.)")
            
            time.sleep(5)  # Даём время на начало скачивания
            
            # Ищем последний скачанный XLSX файл
            max_wait_time = 30  # Максимальное время ожидания (секунды)
            wait_interval = 2  # Интервал проверки (секунды)
            waited = 0
            
            while waited < max_wait_time:
                # Ищем во всех папках файлы, соответствующие паттерну
                matching_files = []
                for search_dir in search_dirs:
                    try:
                        all_files = list(search_dir.glob("*.xlsx"))
                        for file_path in all_files:
                            if file_pattern.match(file_path.name):
                                matching_files.append(file_path)
                    except Exception as e:
                        logger.debug(f"Ошибка при проверке папки {search_dir}: {e}")
                
                if matching_files:
                    # Сортируем по времени модификации (новейший первый)
                    matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    latest_file = matching_files[0]
                    
                    # Проверяем, что файл действительно новый (скачался после клика)
                    file_mtime = latest_file.stat().st_mtime
                    if file_mtime >= time_before_click:
                        self.downloaded_file_path = latest_file
                        logger.success(f"✓ Файл найден по паттерну: {latest_file}")
                        logger.info(f"  Размер файла: {latest_file.stat().st_size} байт")
                        logger.info(f"  Время модификации: {time.ctime(file_mtime)}")
                        
                        # Открываем файл
                        self.open_file(latest_file)
                        return latest_file
                    else:
                        logger.debug(f"Файл {latest_file.name} слишком старый (до клика)")
                
                time.sleep(wait_interval)
                waited += wait_interval
                if waited % 5 == 0:  # Логируем каждые 5 секунд
                    logger.info(f"Ожидание скачивания... ({waited}/{max_wait_time}с)")
            
            # Если файл не найден, выводим список всех XLSX файлов для отладки
            logger.warning("="*60)
            logger.warning("XLSX файл не найден после ожидания")
            logger.warning("="*60)
            
            # Проверяем все папки и выводим информацию
            all_found_files = []
            for search_dir in search_dirs:
                try:
                    all_files = list(search_dir.glob("*.xlsx"))
                    if all_files:
                        logger.info(f"Найдено {len(all_files)} XLSX файлов в {search_dir}:")
                        for f in sorted(all_files, key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
                            file_info = {
                                'path': f,
                                'name': f.name,
                                'size': f.stat().st_size,
                                'mtime': f.stat().st_mtime,
                                'mtime_str': time.ctime(f.stat().st_mtime)
                            }
                            all_found_files.append(file_info)
                            logger.info(f"  - {f.name} (размер: {file_info['size']} байт, изменён: {file_info['mtime_str']})")
                    else:
                        logger.info(f"В папке {search_dir} нет XLSX файлов")
                except Exception as e:
                    logger.warning(f"Ошибка при проверке папки {search_dir}: {e}")
            
            # Если файл не найден по паттерну, ищем самый новый файл, соответствующий паттерну (даже если он старый)
            logger.info("Файл не найден по времени, ищем самый новый файл по паттерну...")
            all_matching_files = []
            for search_dir in search_dirs:
                try:
                    all_files = list(search_dir.glob("*.xlsx"))
                    for file_path in all_files:
                        if file_pattern.match(file_path.name):
                            all_matching_files.append(file_path)
                except Exception as e:
                    logger.debug(f"Ошибка при проверке папки {search_dir}: {e}")
            
            if all_matching_files:
                newest_matching = max(all_matching_files, key=lambda p: p.stat().st_mtime)
                logger.warning(f"Найден файл по паттерну (возможно, старый): {newest_matching}")
                logger.warning(f"  Время модификации: {time.ctime(newest_matching.stat().st_mtime)}")
                
                # Проверяем, не слишком ли старый файл (больше 5 минут назад)
                time_diff = time.time() - newest_matching.stat().st_mtime
                if time_diff < 300:  # 5 минут
                    logger.info(f"Файл изменён {int(time_diff)} секунд назад - возможно, это нужный файл")
                    self.downloaded_file_path = newest_matching
                    self.open_file(newest_matching)
                    return newest_matching
                else:
                    logger.warning(f"Файл слишком старый ({int(time_diff)} секунд назад), но соответствует паттерну")
            
            # Дополнительно: проверяем все файлы, изменённые за последние 5 минут и соответствующие паттерну
            logger.info(f"Поиск всех XLSX файлов по паттерну '{selected_template_name}_{today_date}...', изменённых за последние 5 минут...")
            recent_matching_files = []
            cutoff_time = time.time() - 300  # 5 минут назад
            
            for search_dir in search_dirs:
                try:
                    for file_path in search_dir.glob("*.xlsx"):
                        try:
                            if file_pattern.match(file_path.name) and file_path.stat().st_mtime >= cutoff_time:
                                recent_matching_files.append(file_path)
                        except:
                            pass
                except:
                    pass
            
            if recent_matching_files:
                newest_recent = max(recent_matching_files, key=lambda p: p.stat().st_mtime)
                logger.success(f"✓ Найден недавно изменённый файл по паттерну: {newest_recent}")
                self.downloaded_file_path = newest_recent
                self.open_file(newest_recent)
                return newest_recent
            
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
