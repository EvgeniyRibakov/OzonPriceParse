"""Агент для автоматизации браузера Ozon Seller (Selenium версия)."""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from openpyxl import load_workbook
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
                    
                    # Обновляем настройки загрузок в профиле Chrome
                    downloads_path = str(self.downloads_dir.absolute())
                    logger.info("="*60)
                    logger.info("ОБНОВЛЕНИЕ НАСТРОЕК ЗАГРУЗОК В ПРОФИЛЕ CHROME")
                    logger.info("="*60)
                    if self._update_chrome_preferences(profile_path, downloads_path):
                        logger.success("✓ Настройки профиля Chrome успешно обновлены")
                    else:
                        logger.warning("⚠ Не удалось обновить настройки профиля, используем стандартные prefs")
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

    def _update_chrome_preferences(self, profile_path: Path, downloads_path: str) -> bool:
        """Обновляет файл Preferences профиля Chrome для изменения папки загрузок.
        
        Args:
            profile_path: Путь к папке профиля Chrome
            downloads_path: Путь к папке для загрузок
            
        Returns:
            True если настройки успешно обновлены, False в противном случае
        """
        preferences_file = profile_path / "Preferences"
        
        if not preferences_file.exists():
            logger.warning(f"Файл Preferences не найден: {preferences_file}")
            logger.info("Chrome создаст файл Preferences при первом запуске с этим профилем")
            return False
        
        # Проверяем, не заблокирован ли файл (Chrome может быть запущен)
        try:
            # Пробуем открыть файл в режиме записи для проверки блокировки
            test_file = open(preferences_file, 'r+', encoding='utf-8')
            test_file.close()
        except PermissionError:
            logger.warning("⚠ Файл Preferences заблокирован. Возможно, Chrome запущен.")
            logger.warning("⚠ Закройте все окна Chrome перед запуском скрипта для изменения настроек.")
            logger.info("→ Продолжаем с настройками через prefs (могут быть перезаписаны Chrome)")
            return False
        except Exception as e:
            logger.warning(f"Не удалось проверить доступность файла Preferences: {e}")
            return False
        
        try:
            # Читаем текущие настройки
            logger.info(f"Чтение файла Preferences: {preferences_file}")
            with open(preferences_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
            
            # Обновляем настройки загрузок
            # Chrome хранит настройки в разных местах в зависимости от версии
            updated = False
            
            # Способ 1: Обновляем в секции download
            if 'download' not in prefs:
                prefs['download'] = {}
            
            old_download_dir = prefs['download'].get('default_directory', 'не установлена')
            prefs['download']['default_directory'] = downloads_path
            prefs['download']['directory_upgrade'] = True
            updated = True
            logger.info(f"Обновлена секция download: {old_download_dir} -> {downloads_path}")
            
            # Способ 2: Обновляем в секции profile (для некоторых версий Chrome)
            if 'profile' not in prefs:
                prefs['profile'] = {}
            
            if 'default_content_setting_values' not in prefs['profile']:
                prefs['profile']['default_content_setting_values'] = {}
            
            prefs['profile']['default_content_setting_values']['automatic_downloads'] = 1
            
            # Способ 3: Обновляем в корне (для старых версий Chrome)
            prefs['download.default_directory'] = downloads_path
            prefs['download.prompt_for_download'] = False
            prefs['download.directory_upgrade'] = True
            
            # Сохраняем обновлённые настройки
            logger.info(f"Сохранение обновлённых настроек в {preferences_file}")
            # Создаём резервную копию
            backup_file = preferences_file.with_suffix('.prefs.backup')
            try:
                import shutil
                shutil.copy2(preferences_file, backup_file)
                logger.info(f"Создана резервная копия: {backup_file}")
            except Exception as e:
                logger.warning(f"Не удалось создать резервную копию: {e}")
            
            # Сохраняем обновлённый файл
            try:
                with open(preferences_file, 'w', encoding='utf-8') as f:
                    json.dump(prefs, f, indent=2, ensure_ascii=False)
            except PermissionError:
                logger.warning("⚠ Не удалось записать файл Preferences (файл заблокирован)")
                logger.warning("⚠ Закройте все окна Chrome перед запуском скрипта")
                return False
            
            logger.success(f"✓ Настройки загрузок обновлены в профиле Chrome: {downloads_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при чтении JSON файла Preferences: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении Preferences: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _find_downloaded_file(self, template_name: str, time_before_click: float, max_wait: int = 10) -> Optional[Path]:
        """Вспомогательный метод для поиска скачанного файла в файловой системе.
        
        Args:
            template_name: Название шаблона (например, "Цены товаров")
            time_before_click: Время до клика (для проверки, что файл новый)
            max_wait: Максимальное время ожидания в секундах
            
        Returns:
            Path к найденному файлу или None
        """
        if template_name is None:
            template_name = "Цены товаров"
        
        # Собираем все возможные папки для поиска файла
        search_dirs = [self.downloads_dir]
        
        def add_dir_if_exists(path: Path, description: str):
            """Добавляет папку в список поиска, если она существует."""
            if path.exists() and path not in search_dirs:
                search_dirs.append(path)
        
        # Стандартные папки загрузок
        add_dir_if_exists(Path.home() / "Downloads", "стандартную папку загрузок")
        
        if os.name == 'nt':  # Windows
            user_profile = os.getenv('USERPROFILE')
            if user_profile:
                add_dir_if_exists(Path(user_profile) / "Downloads", "папку загрузок из USERPROFILE")
            
            # Реестр Windows
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                )
                downloads_path = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                winreg.CloseKey(key)
                if downloads_path:
                    add_dir_if_exists(Path(downloads_path), "папку загрузок из реестра")
            except:
                pass
            
            # Альтернативные пути
            user_profile = os.getenv('USERPROFILE') or str(Path.home())
            alternative_paths = [
                Path(user_profile) / "Documents" / "Downloads",
                Path(user_profile) / "Документы" / "Downloads",
                Path(user_profile) / "Documents" / "Загрузки",
            ]
            
            for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = Path(f"{drive_letter}:") / "Документы и файлы" / "Documents" / "Downloads"
                if drive_path.exists():
                    alternative_paths.append(drive_path)
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    add_dir_if_exists(alt_path, "альтернативную папку")
        
        # Папка загрузок из профиля Chrome
        if self.settings.chrome_user_data_dir:
            profile_downloads = self.settings.chrome_user_data_dir / self.settings.chrome_profile_name / "Downloads"
            add_dir_if_exists(profile_downloads, "папку загрузок профиля Chrome")
        
        # Формируем паттерн для поиска
        today_date = datetime.now().strftime("%d.%m.%Y")
        template_name_escaped = re.escape(template_name)
        file_pattern = re.compile(
            rf"^{template_name_escaped}_{re.escape(today_date)}(?:\s*\(\d+\))?\.xlsx$",
            re.IGNORECASE
        )
        
        # Ищем файл
        waited = 0
        wait_interval = 1
        while waited < max_wait:
            matching_files = []
            for search_dir in search_dirs:
                try:
                    all_files = list(search_dir.glob("*.xlsx"))
                    for file_path in all_files:
                        if file_pattern.match(file_path.name):
                            matching_files.append(file_path)
                except:
                    pass
            
            if matching_files:
                matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                latest_file = matching_files[0]
                file_mtime = latest_file.stat().st_mtime
                
                # Проверяем, что файл новый
                if file_mtime >= time_before_click:
                    return latest_file
                # Если файл старый, но недавно изменён (в пределах 5 минут), тоже возвращаем
                elif (time.time() - file_mtime) < 300:
                    return latest_file
            
            time.sleep(wait_interval)
            waited += wait_interval
        
        return None

    def open_file(self, filepath: Path) -> None:
        """Открывает файл в системе используя стандартное приложение."""
        logger.info("="*60)
        logger.info(f"ОТКРЫТИЕ ФАЙЛА: {filepath.name}")
        logger.info("="*60)
        
        # Проверяем, что файл существует
        if not filepath.exists():
            logger.error(f"Файл не существует: {filepath}")
            raise FileNotFoundError(f"Файл не найден: {filepath}")
        
        # Проверяем, что это файл, а не директория
        if not filepath.is_file():
            logger.error(f"Путь указывает не на файл: {filepath}")
            raise ValueError(f"Путь не является файлом: {filepath}")
        
        logger.info(f"Путь к файлу: {filepath.absolute()}")
        logger.info(f"Размер файла: {filepath.stat().st_size} байт")
        
        opened = False
        
        # Способ 1: os.startfile (Windows) - самый надежный для Windows
        if os.name == 'nt':  # Windows
            try:
                logger.info("Способ 1: Открытие через os.startfile (Windows)...")
                os.startfile(str(filepath.absolute()))
                opened = True
                logger.success("✓ Файл открыт через os.startfile")
            except Exception as e:
                logger.warning(f"os.startfile не сработал: {e}")
        
        # Способ 2: subprocess для Windows (альтернатива)
        if not opened and os.name == 'nt':
            try:
                logger.info("Способ 2: Открытие через subprocess (Windows)...")
                import subprocess
                subprocess.Popen(['start', '', str(filepath.absolute())], shell=True)
                opened = True
                logger.success("✓ Файл открыт через subprocess")
            except Exception as e:
                logger.warning(f"subprocess не сработал: {e}")
        
        # Способ 3: macOS/Linux через open/xdg-open
        if not opened and os.name == 'posix':
            try:
                if sys.platform == 'darwin':  # macOS
                    logger.info("Способ 3: Открытие через open (macOS)...")
                    os.system(f'open "{filepath.absolute()}"')
                else:  # Linux
                    logger.info("Способ 3: Открытие через xdg-open (Linux)...")
                    os.system(f'xdg-open "{filepath.absolute()}"')
                opened = True
                logger.success("✓ Файл открыт через системную команду")
            except Exception as e:
                logger.warning(f"Системная команда не сработала: {e}")
        
        # Способ 4: subprocess для macOS/Linux (альтернатива)
        if not opened:
            try:
                logger.info("Способ 4: Открытие через subprocess (универсальный)...")
                import subprocess
                if sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', str(filepath.absolute())])
                elif sys.platform.startswith('linux'):  # Linux
                    subprocess.Popen(['xdg-open', str(filepath.absolute())])
                elif os.name == 'nt':  # Windows (если предыдущие способы не сработали)
                    subprocess.Popen(['cmd', '/c', 'start', '', str(filepath.absolute())], shell=False)
                opened = True
                logger.success("✓ Файл открыт через subprocess (универсальный)")
            except Exception as e:
                logger.warning(f"subprocess (универнальный) не сработал: {e}")
        
        if opened:
            logger.success(f"✓✓✓ ФАЙЛ УСПЕШНО ОТКРЫТ: {filepath.name} ✓✓✓")
            logger.info(f"Файл должен открыться в программе по умолчанию для .xlsx файлов")
            time.sleep(1)  # Даём время на открытие файла
        else:
            logger.error("❌ Не удалось открыть файл ни одним из способов!")
            logger.error("Попробуйте открыть файл вручную:")
            logger.error(f"  {filepath.absolute()}")
            raise RuntimeError(f"Не удалось открыть файл: {filepath}")

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

            # Шаг 9.5: Поиск всех кабинетов и обработка каждого
            logger.info("="*60)
            logger.info("ПОИСК ВСЕХ КАБИНЕТОВ")
            logger.info("="*60)
            
            cabinets = self._find_all_cabinets()
            if not cabinets:
                logger.warning("Кабинеты не найдены, обрабатываем текущий кабинет")
                # Продолжаем со старым алгоритмом для одного кабинета
                latest_file = self._process_single_cabinet()
                return latest_file
            
            logger.info(f"Найдено кабинетов: {len(cabinets)}")
            for i, cabinet_name in enumerate(cabinets, 1):
                logger.info(f"  {i}. {cabinet_name}")
            
            # Обрабатываем каждый кабинет
            all_downloaded_files = []
            for cabinet_name in cabinets:
                try:
                    logger.info("="*60)
                    logger.info(f"ОБРАБОТКА КАБИНЕТА: {cabinet_name}")
                    logger.info("="*60)
                    
                    # Переключаемся на кабинет
                    self._switch_to_cabinet(cabinet_name)
                    
                    # Обрабатываем кабинет
                    downloaded_file = self._process_single_cabinet(cabinet_name)
                    
                    if downloaded_file:
                        all_downloaded_files.append(downloaded_file)
                        
                        # Загружаем данные в соответствующий лист Google Sheets
                        if self.settings.upload_to_google_sheets and self.settings.google_sheets_url:
                            try:
                                self.upload_to_google_sheets(downloaded_file, sheet_name=cabinet_name)
                            except Exception as e:
                                logger.error(f"Ошибка при загрузке в Google Sheets для кабинета {cabinet_name}: {e}")
                                logger.exception("Детали ошибки:")
                    
                    # Небольшая пауза между кабинетами
                    time.sleep(2.0)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке кабинета {cabinet_name}: {e}")
                    logger.exception("Детали ошибки:")
                    continue
            
            # Возвращаем последний скачанный файл
            return all_downloaded_files[-1] if all_downloaded_files else None

        except Exception as e:
            logger.error(f"ОШИБКА В ПРОЦЕССЕ ВЫПОЛНЕНИЯ: {e}")
            logger.exception("Детали ошибки:")
            raise

    def _find_all_cabinets(self) -> list[str]:
        """Находит все доступные кабинеты на странице товаров.
        
        Returns:
            Список названий кабинетов
        """
        try:
            # Сначала открываем выпадающий список кабинетов
            # Селектор для кнопки открытия списка кабинетов
            company_dropdown_selector = "span.index_companyItem_2gg8o"
            
            if self.wait_for_element(company_dropdown_selector, "Кнопка выбора кабинета", timeout=5, silent=True):
                try:
                    dropdown_button = self.driver.find_element(By.CSS_SELECTOR, company_dropdown_selector)
                    # Кликаем, чтобы открыть выпадающий список
                    dropdown_button.click()
                    time.sleep(1.0)  # Ждём открытия списка
                    logger.info("Выпадающий список кабинетов открыт")
                except Exception as e:
                    logger.warning(f"Не удалось открыть выпадающий список: {e}")
            
            # Теперь ищем все кабинеты в выпадающем списке
            # Селектор для кабинетов: div.cs090-a.cs290-a4
            # Название кабинета: div.c0s90-a3.c0s90-a5.table-500
            cabinet_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "div.cs290-a4 div.c0s90-a3.c0s90-a5.table-500"
            )
            
            # Если не нашли, пробуем альтернативный селектор
            if not cabinet_elements:
                cabinet_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div.cs090-a.cs290-a4 div.c0s90-a3.c0s90-a5.table-500"
                )
            
            cabinets = []
            for elem in cabinet_elements:
                try:
                    cabinet_name = elem.text.strip()
                    if cabinet_name:
                        cabinets.append(cabinet_name)
                        logger.info(f"Найден кабинет: {cabinet_name}")
                except Exception as e:
                    logger.debug(f"Ошибка при чтении названия кабинета: {e}")
                    continue
            
            # Закрываем выпадающий список, кликнув вне его или на ESC
            if cabinets:
                try:
                    # Кликаем вне выпадающего списка, чтобы закрыть его
                    self.driver.execute_script("document.body.click();")
                    time.sleep(0.5)
                except:
                    pass
            
            return cabinets
        except Exception as e:
            logger.error(f"Ошибка при поиске кабинетов: {e}")
            return []

    def _close_modal_window(self) -> None:
        """Закрывает модальное окно после скачивания файла."""
        try:
            logger.info("="*60)
            logger.info("ЗАКРЫТИЕ МОДАЛЬНОГО ОКНА")
            logger.info("="*60)
            
            # Ищем кнопку закрытия (крестик) по SVG path
            # SVG path: M5.44 5.44a1.5 1.5 0 0 1 2.12 0L12 9.878l4.44-4.44a1.5 1.5 0 0 1 2.12 2.122L14.122 12l4.44 4.44a1.5 1.5 0 0 1-2.122 2.12L12 14.122l-4.44 4.44a1.5 1.5 0 0 1-2.12-2.122L9.878 12l-4.44-4.44a1.5 1.5 0 0 1 0-2.12
            close_button_xpath = "//svg[@width='20' and @height='20']//path[contains(@d, 'M5.44 5.44')]"
            
            # Пробуем найти кнопку закрытия
            close_buttons = self.driver.find_elements(By.XPATH, close_button_xpath)
            
            if close_buttons:
                # Находим родительский элемент (кнопку)
                close_button = close_buttons[0]
                # Поднимаемся до кликабельного элемента
                try:
                    parent_button = close_button.find_element(By.XPATH, "./ancestor::button | ./ancestor::div[@role='button'] | ./ancestor::*[@onclick]")
                    
                    # Прокручиваем к элементу
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", parent_button)
                    time.sleep(0.3)
                    
                    # Кликаем
                    parent_button.click()
                    logger.success("✓ Модальное окно закрыто")
                    time.sleep(1.0)  # Ждём закрытия
                    return
                except Exception as e:
                    logger.debug(f"Не удалось кликнуть на родительский элемент: {e}")
                    # Пробуем кликнуть напрямую через JavaScript
                    try:
                        self.driver.execute_script("arguments[0].click();", close_button)
                        logger.success("✓ Модальное окно закрыто (через JavaScript)")
                        time.sleep(1.0)
                        return
                    except:
                        pass
            
            # Альтернативный способ: ищем кнопку закрытия по классу
            close_selectors = [
                "button[aria-label*='закрыть' i]",
                "button[aria-label*='close' i]",
                "div.t6c90-a3",  # Класс кнопки закрытия из CSS
                "button[class*='close']",
                "div[class*='close']",
            ]
            
            for selector in close_selectors:
                try:
                    close_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if close_elements:
                        close_element = close_elements[0]
                        if close_element.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", close_element)
                            time.sleep(0.3)
                            close_element.click()
                            logger.success(f"✓ Модальное окно закрыто (селектор: {selector})")
                            time.sleep(1.0)
                            return
                except:
                    continue
            
            # Последний способ: нажать ESC
            try:
                from selenium.webdriver.common.keys import Keys
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                logger.info("Попытка закрыть модальное окно через ESC")
                time.sleep(1.0)
            except:
                pass
            
            logger.warning("Не удалось найти кнопку закрытия модального окна")
            
        except Exception as e:
            logger.warning(f"Ошибка при закрытии модального окна: {e}")
            # Пробуем ESC в любом случае
            try:
                from selenium.webdriver.common.keys import Keys
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(1.0)
            except:
                pass

    def _switch_to_cabinet(self, cabinet_name: str) -> None:
        """Переключается на указанный кабинет.
        
        Args:
            cabinet_name: Название кабинета
        """
        try:
            logger.info(f"Переключение на кабинет: {cabinet_name}")
            
            # Сначала открываем выпадающий список кабинетов
            company_dropdown_selector = "span.index_companyItem_2gg8o"
            
            if self.wait_for_element(company_dropdown_selector, "Кнопка выбора кабинета", timeout=5, silent=True):
                try:
                    dropdown_button = self.driver.find_element(By.CSS_SELECTOR, company_dropdown_selector)
                    # Кликаем, чтобы открыть выпадающий список
                    dropdown_button.click()
                    time.sleep(1.0)  # Ждём открытия списка
                    logger.info("Выпадающий список кабинетов открыт")
                except Exception as e:
                    logger.warning(f"Не удалось открыть выпадающий список: {e}")
            
            # Ищем элемент кабинета по названию
            cabinet_xpath = f"//div[contains(@class, 'c0s90-a3') and contains(@class, 'c0s90-a5') and contains(@class, 'table-500') and normalize-space(text())='{cabinet_name}']"
            
            # Проверяем, активен ли уже этот кабинет (есть ли галочка)
            try:
                cabinet_element = self.driver.find_element(By.XPATH, cabinet_xpath)
                # Ищем родительский div с классом cs090-a
                parent_div = cabinet_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'cs090-a')]")
                
                # Проверяем наличие галочки (svg в div.cs290-a7)
                try:
                    checkmark = parent_div.find_element(By.CSS_SELECTOR, "div.cs290-a7 svg")
                    logger.info(f"Кабинет '{cabinet_name}' уже активен (найдена галочка)")
                    return
                except:
                    # Галочки нет, нужно кликнуть
                    pass
                
                # Кликаем на кабинет
                logger.info(f"Клик по кабинету '{cabinet_name}'...")
                cabinet_element.click()
                time.sleep(2.0)  # Ждём переключения
                
                # Проверяем, что кабинет стал активным
                try:
                    checkmark = parent_div.find_element(By.CSS_SELECTOR, "div.cs290-a7 svg")
                    logger.success(f"✓ Кабинет '{cabinet_name}' успешно активирован")
                except:
                    logger.warning(f"⚠ Не удалось подтвердить активацию кабинета '{cabinet_name}'")
                    
            except Exception as e:
                logger.error(f"Ошибка при переключении на кабинет '{cabinet_name}': {e}")
                raise
                
        except Exception as e:
            logger.error(f"Ошибка при переключении кабинета: {e}")
            raise

    def _process_single_cabinet(self, cabinet_name: str | None = None) -> Optional[Path]:
        """Обрабатывает один кабинет: скачивает Excel файл.
        
        Args:
            cabinet_name: Название кабинета (для логирования)
            
        Returns:
            Path к скачанному файлу или None
        """
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
            # Примеры: <диск>:\Документы и файлы\Documents\Downloads или <диск>:\Documents\Downloads
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
                    
                    # Закрываем модальное окно после скачивания
                    self._close_modal_window()
                    
                    # Не открываем файл - просто возвращаем путь
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
                # Закрываем модальное окно после скачивания
                self._close_modal_window()
                # Не открываем файл - просто возвращаем путь
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
                # Закрываем модальное окно после скачивания
                self._close_modal_window()
                # Не открываем файл - просто возвращаем путь
                return newest_recent
        
        return None
    
    def _read_excel_data_directly(self, excel_file: Path) -> list:
        """Читает данные из Excel файла напрямую, обходя проблемы со стилями.
        
        Args:
            excel_file: Путь к Excel файлу
            
        Returns:
            Список списков с данными из листа "Товары и цены" или второго листа
        """
        logger.info("Чтение данных из Excel файла (обходя проблемы со стилями)...")
        
        # Пробуем разные способы чтения
        methods = [
            ("pandas с engine='xlrd'", lambda: self._read_with_pandas_xlrd(excel_file)),
            ("pandas с engine='openpyxl' и ignore стили", lambda: self._read_with_pandas_openpyxl(excel_file)),
            ("openpyxl напрямую из XML", lambda: self._read_with_openpyxl_xml(excel_file)),
        ]
        
        for method_name, method_func in methods:
            try:
                logger.info(f"Попытка чтения через: {method_name}...")
                data = method_func()
                if data:
                    logger.success(f"✓ Успешно прочитано через {method_name}: {len(data)} строк")
                    return data
            except Exception as e:
                logger.debug(f"Метод {method_name} не сработал: {e}")
                continue
        
        logger.error("Все методы чтения Excel файла не сработали")
        raise RuntimeError("Не удалось прочитать Excel файл")
    
    def _read_with_pandas_xlrd(self, excel_file: Path) -> list:
        """Читает через pandas с xlrd (для старых форматов)."""
        try:
            df = pd.read_excel(excel_file, sheet_name=0, header=None, engine='xlrd')
            data = df.fillna("").values.tolist()
            return [row for row in data if any(str(cell).strip() if cell != "" else False for cell in row)]
        except:
            raise
    
    def _read_with_pandas_openpyxl(self, excel_file: Path) -> list:
        """Читает через pandas с openpyxl, игнорируя стили."""
        try:
            # Используем openpyxl напрямую с read_only и data_only
            from openpyxl import load_workbook
            wb = load_workbook(excel_file, read_only=True, data_only=True, keep_vba=False)
            
            # Ищем лист "Товары и цены" или используем второй лист
            target_sheet = None
            for name in wb.sheetnames:
                if "Товары и цены" in name or "товары и цены" in name.lower():
                    target_sheet = name
                    break
            
            if not target_sheet:
                if len(wb.sheetnames) > 1:
                    target_sheet = wb.sheetnames[1]
                else:
                    target_sheet = wb.sheetnames[0]
            
            ws = wb[target_sheet]
            data = []
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None and str(cell).strip() for cell in row):
                    data.append([str(cell) if cell is not None else "" for cell in row])
            
            return data
        except:
            raise
    
    def _read_with_openpyxl_xml(self, excel_file: Path) -> list:
        """Читает напрямую из XML файлов внутри Excel (обходя стили)."""
        import zipfile
        from xml.etree import ElementTree as ET
        
        try:
            # Excel файл - это ZIP архив
            with zipfile.ZipFile(excel_file, 'r') as zip_ref:
                # Читаем workbook.xml для получения списка листов
                workbook_xml = zip_ref.read('xl/workbook.xml')
                workbook_root = ET.fromstring(workbook_xml)
                
                # Находим лист "Товары и цены" или второй лист
                sheets = workbook_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')
                target_sheet_id = None
                target_sheet_name = None
                
                for i, sheet in enumerate(sheets):
                    name = sheet.get('name', '')
                    if "Товары и цены" in name or "товары и цены" in name.lower():
                        target_sheet_id = sheet.get('sheetId', str(i+1))
                        target_sheet_name = name
                        break
                
                if not target_sheet_id:
                    if len(sheets) > 1:
                        target_sheet_id = sheets[1].get('sheetId', '2')
                        target_sheet_name = sheets[1].get('name', 'Sheet2')
                    else:
                        target_sheet_id = sheets[0].get('sheetId', '1')
                        target_sheet_name = sheets[0].get('name', 'Sheet1')
                
                # Читаем данные из sharedStrings.xml (если есть)
                shared_strings = {}
                try:
                    strings_xml = zip_ref.read('xl/sharedStrings.xml')
                    strings_root = ET.fromstring(strings_xml)
                    for i, si in enumerate(strings_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si')):
                        text_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                        if text_elem is not None:
                            shared_strings[i] = text_elem.text or ""
                except:
                    pass
                
                # Читаем данные из worksheet
                worksheet_path = f'xl/worksheets/sheet{target_sheet_id}.xml'
                try:
                    worksheet_xml = zip_ref.read(worksheet_path)
                except:
                    # Пробуем найти по имени
                    worksheet_path = None
                    for name in zip_ref.namelist():
                        if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                            worksheet_xml = zip_ref.read(name)
                            worksheet_path = name
                            break
                    if not worksheet_path:
                        raise
                
                worksheet_root = ET.fromstring(worksheet_xml)
                
                # Извлекаем данные из строк
                data = []
                rows = worksheet_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
                
                for row in rows:
                    row_data = []
                    cells = row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                    
                    for cell in cells:
                        cell_value = ""
                        v_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                        if v_elem is not None and v_elem.text:
                            # Проверяем, является ли значение ссылкой на shared strings
                            t_attr = cell.get('t')
                            if t_attr == 's':
                                idx = int(v_elem.text)
                                cell_value = shared_strings.get(idx, "")
                            else:
                                cell_value = v_elem.text
                        
                        row_data.append(cell_value)
                    
                    if any(str(cell).strip() for cell in row_data):
                        data.append(row_data)
                
                return data
        except Exception as e:
            logger.debug(f"Ошибка чтения через XML: {e}")
            raise
    
    def upload_to_google_sheets(self, excel_file: Path, sheet_name: str | None = None) -> None:
        """Загружает Excel файл напрямую в Google Sheets через Drive API.
        Загружает файл целиком, Google автоматически конвертирует его в формат Google Sheets.
        
        Args:
            excel_file: Путь к Excel файлу
            sheet_name: Название листа для загрузки данных (если None, используется первый лист)
        """
        logger.info("="*60)
        logger.info("ЗАГРУЗКА EXCEL ФАЙЛА В GOOGLE SHEETS ЧЕРЕЗ DRIVE API")
        logger.info("="*60)
        
        if not excel_file.exists():
            logger.error(f"Файл не существует: {excel_file}")
            return
        
        # Извлекаем spreadsheet_id из URL
        spreadsheet_id = self._extract_spreadsheet_id()
        if not spreadsheet_id:
            logger.error("Не удалось извлечь ID таблицы из URL")
            return
        
        # Проверяем наличие credentials
        if not self.settings.google_sheets_credentials_path:
            logger.error("Не указан путь к credentials файлу для Google Sheets API")
            logger.info("Укажите GOOGLE_SHEETS_CREDENTIALS_PATH в .env файле")
            return
        
        # Обрабатываем путь к credentials файлу (поддерживаем относительные пути)
        credentials_path_str = self.settings.google_sheets_credentials_path
        if not credentials_path_str:
            logger.error("Не указан путь к credentials файлу")
            return
        
        # Если путь относительный, разрешаем его относительно корня проекта
        credentials_path = Path(credentials_path_str)
        if not credentials_path.is_absolute():
            # Получаем корень проекта (где находится run.py)
            project_root = Path(__file__).parent.parent.parent
            credentials_path = project_root / credentials_path
        
        if not credentials_path.exists():
            logger.error(f"Файл credentials не найден: {credentials_path}")
            logger.info(f"  Проверьте путь: {credentials_path_str}")
            return
        
        logger.info(f"Используем credentials файл: {credentials_path}")
        
        try:
            # Аутентификация через service account
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(
                str(credentials_path),
                scopes=scopes
            )
            
            # Создаем сервис Sheets API
            sheets_service = build('sheets', 'v4', credentials=creds)
            
            logger.info(f"Чтение данных из Excel файла...")
            logger.info(f"  Файл: {excel_file.name}")
            logger.info(f"  Размер: {excel_file.stat().st_size} байт")
            
            # Читаем данные из Excel файла локально (обходя проблемы со стилями)
            data = self._read_excel_data_directly(excel_file)
            
            if not data:
                logger.warning("В файле нет данных для загрузки")
                return
            
            logger.info(f"  Прочитано {len(data)} строк из Excel файла")
            
            # Определяем название листа
            if sheet_name:
                target_sheet_name = sheet_name
                logger.info(f"Используем лист: {target_sheet_name}")
            else:
                # Получаем список листов и используем первый
                spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheets = spreadsheet.get('sheets', [])
                if sheets:
                    target_sheet_name = sheets[0]['properties']['title']
                    logger.info(f"Используем первый лист: {target_sheet_name}")
                else:
                    logger.error("В таблице нет листов")
                    return
            
            # Проверяем, существует ли лист с таким названием
            spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            existing_sheets = {sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])}
            
            if target_sheet_name not in existing_sheets:
                logger.warning(f"Лист '{target_sheet_name}' не найден в таблице")
                logger.info(f"Доступные листы: {', '.join(existing_sheets)}")
                logger.info(f"Создаём новый лист '{target_sheet_name}'...")
                
                # Создаём новый лист
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': target_sheet_name
                        }
                    }
                }]
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                logger.success(f"✓ Лист '{target_sheet_name}' создан")
            
            # Очищаем лист
            logger.info(f"Очистка листа '{target_sheet_name}'...")
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{target_sheet_name}'!A1:ZZ10000"
            ).execute()
            
            # Загружаем данные в лист
            logger.info(f"Загрузка данных в лист '{target_sheet_name}'...")
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{target_sheet_name}'!A1",
                valueInputOption='RAW',
                body={'values': data}
            ).execute()
            
            logger.success(f"✓ Excel файл успешно загружен в лист '{target_sheet_name}'!")
            logger.info(f"  Всего строк: {len(data)}")
            logger.info(f"  URL таблицы: {self.settings.google_sheets_url}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке в Google Sheets: {e}")
            logger.exception("Детали ошибки:")
            raise

    def _extract_spreadsheet_id(self) -> str | None:
        """Извлекает spreadsheet_id из URL Google Sheets.
        
        Returns:
            ID таблицы или None
        """
        if not self.settings.google_sheets_url:
            return None
        
        # Формат URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, self.settings.google_sheets_url)
        
        if match:
            spreadsheet_id = match.group(1)
            logger.info(f"Извлечен spreadsheet_id: {spreadsheet_id}")
            return spreadsheet_id
        
        # Если ID уже указан в настройках
        if self.settings.google_sheets_spreadsheet_id:
            return self.settings.google_sheets_spreadsheet_id
        
        logger.warning("Не удалось извлечь spreadsheet_id из URL")
        return None

    def close(self) -> None:
        """Закрытие браузера."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Браузер закрыт")
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера: {e}")
