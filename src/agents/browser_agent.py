"""Агент для автоматизации браузера Ozon Seller."""
import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from src.config.settings import Settings


class BrowserAgent:
    """Агент для автоматизации браузера с пошаговой логикой."""

    def __init__(self, settings: Settings):
        """Инициализация агента."""
        self.settings = settings
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.downloads_dir = settings.downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_file_path: Optional[Path] = None

    async def _human_delay(self, seconds: float, reason: str = "") -> None:
        """Задержка для имитации человеческого поведения."""
        if reason:
            logger.debug(f"Задержка {seconds:.2f}с: {reason}")
        await asyncio.sleep(seconds)

    async def _log_action(
        self, action: str, details: str = "", element: str = ""
    ) -> None:
        """Логирование действия с подробностями."""
        log_msg = f"Действие: {action}"
        if element:
            log_msg += f" | Элемент: {element}"
        if details:
            log_msg += f" | Детали: {details}"
        logger.info(log_msg)

    async def start_browser(self) -> None:
        """Запуск браузера."""
        self._log_action("Запуск браузера", f"Тип: {self.settings.browser_type}")
        playwright = await async_playwright().start()

        browser_type_map = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit,
        }
        browser_launcher = browser_type_map.get(
            self.settings.browser_type, playwright.chromium
        )

        self.browser = await browser_launcher.launch(
            headless=self.settings.headless,
            args=["--start-maximized"] if not self.settings.headless else [],
        )

        self.context = await self.browser.new_context(
            viewport={
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            },
            accept_downloads=True,
        )

        # Настраиваем путь для скачивания файлов
        await self.context.set_extra_http_headers(
            {"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}
        )

        self.page = await self.context.new_page()

        # Обработчик скачивания файлов
        async def handle_download(download):
            """Обработка скачивания файла."""
            filename = download.suggested_filename
            filepath = self.downloads_dir / filename
            await download.save_as(filepath)
            self.downloaded_file_path = filepath
            logger.success(f"Файл скачан: {filepath}")

        self.page.on("download", handle_download)

        logger.success("Браузер запущен")

    async def navigate_to_url(self, url: str) -> None:
        """Переход по URL."""
        self._log_action("Переход по URL", url)
        await self.page.goto(url, wait_until="domcontentloaded")
        await self._human_delay(
            self.settings.delay_page_load, "Ожидание загрузки страницы"
        )
        logger.success(f"Переход выполнен: {url}")

    async def click_button(
        self, selector: str, description: str = "", wait_for_navigation: bool = False
    ) -> None:
        """Клик по кнопке с задержками."""
        self._log_action("Клик по кнопке", description, selector)
        await self._human_delay(
            self.settings.delay_before_click, f"Перед кликом: {description}"
        )

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=10000, state="visible"
            )
            if not element:
                raise Exception(f"Элемент не найден: {selector}")

            await element.click()
            await self._human_delay(
                self.settings.delay_after_click, f"После клика: {description}"
            )

            if wait_for_navigation:
                await self.page.wait_for_load_state("networkidle")
                await self._human_delay(
                    self.settings.delay_page_load, "Ожидание загрузки после навигации"
                )

            logger.success(f"Клик выполнен: {description}")
        except PlaywrightTimeoutError:
            error_msg = f"Таймаут при ожидании элемента: {selector}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def fill_input(
        self, selector: str, value: str, description: str = ""
    ) -> None:
        """Заполнение поля ввода с человеческими задержками."""
        self._log_action("Заполнение поля", description, selector)
        await self._human_delay(
            self.settings.delay_before_type, f"Перед вводом: {description}"
        )

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=10000, state="visible"
            )
            if not element:
                raise Exception(f"Поле ввода не найдено: {selector}")

            await element.click()
            await self._human_delay(0.3, "Клик по полю ввода")

            # Очищаем поле
            await element.fill("")
            await self._human_delay(0.2, "Очистка поля")

            # Вводим текст посимвольно для имитации человеческого ввода
            for char in value:
                await element.type(char, delay=self.settings.delay_between_keys * 1000)
                await self._human_delay(
                    self.settings.delay_between_keys, f"Ввод символа: {char}"
                )

            await self._human_delay(
                self.settings.delay_after_type, f"После ввода: {description}"
            )
            logger.success(f"Поле заполнено: {description}")
        except PlaywrightTimeoutError:
            error_msg = f"Таймаут при ожидании поля ввода: {selector}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def wait_for_element(
        self, selector: str, description: str = "", timeout: int = 10000
    ) -> bool:
        """Ожидание появления элемента."""
        self._log_action("Ожидание элемента", description, selector)
        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            logger.success(f"Элемент найден: {description}")
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Элемент не найден: {description} ({selector})")
            return False

    async def get_user_input(self, prompt: str) -> str:
        """Запрос ввода от пользователя."""
        logger.warning(f"ТРЕБУЕТСЯ ВВОД ОТ ПОЛЬЗОВАТЕЛЯ: {prompt}")
        print(f"\n{'='*60}")
        print(f"ВНИМАНИЕ: {prompt}")
        print(f"{'='*60}")
        user_input = input("Введите код и нажмите Enter: ").strip()
        logger.info(f"Пользователь ввел: {user_input[:2]}** (скрыто)")
        return user_input

    async def execute_flow(self, start_url: str) -> Optional[Path]:
        """Выполнение основного потока работы."""
        try:
            # Шаг 1: Запуск браузера
            await self.start_browser()

            # Шаг 2: Переход по начальной ссылке
            await self.navigate_to_url(start_url)

            # Шаг 3: Проверка и нажатие кнопки "Войти" (если требуется)
            login_button_selector = 'span.c9r90-a2:has-text("Войти")'
            if await self.wait_for_element(
                login_button_selector, "Кнопка 'Войти'", timeout=5000
            ):
                await self.click_button(
                    login_button_selector,
                    "Кнопка 'Войти'",
                    wait_for_navigation=True,
                )

            # Шаг 4: Ввод номера телефона
            phone_input_selector = 'input[type="tel"][name="autocomplete"]'
            await self.wait_for_element(phone_input_selector, "Поле ввода телефона")
            await self.fill_input(
                phone_input_selector,
                self.settings.phone_number,
                "Номер телефона",
            )

            # Нажимаем кнопку "Войти" после ввода телефона
            submit_phone_button = 'button[type="submit"]:has-text("Войти")'
            if await self.wait_for_element(submit_phone_button, "Кнопка 'Войти'", timeout=5000):
                await self.click_button(
                    submit_phone_button, "Кнопка 'Войти' после ввода телефона", wait_for_navigation=True
                )

            # Шаг 5: Выбор альтернативного способа входа
            different_way_selector = 'div.ga5_3_10-a2:has-text("Войти другим способом")'
            if await self.wait_for_element(
                different_way_selector, "Кнопка 'Войти другим способом'", timeout=5000
            ):
                await self.click_button(
                    different_way_selector,
                    "Войти другим способом",
                    wait_for_navigation=True,
                )

            # Шаг 6: Ввод кода из пуш-уведомления
            otp_input_selector = 'input[name="otp"][type="number"]'
            await self.wait_for_element(otp_input_selector, "Поле ввода кода OTP")
            otp_code = await self.get_user_input(
                "Введите код из пуш-уведомления (6 цифр)"
            )
            await self.fill_input(otp_input_selector, otp_code, "Код из пуш-уведомления")

            # Ожидаем автоматической отправки или ищем кнопку подтверждения
            await self._human_delay(2.0, "Ожидание обработки кода")

            # Шаг 7: Обработка дополнительной проверки (если требуется)
            extra_otp_selector = 'input[name="extraOtp"][type="number"]'
            if await self.wait_for_element(
                extra_otp_selector, "Поле дополнительного кода", timeout=5000
            ):
                # Сначала может быть кнопка "Войти"
                extra_login_button = 'button:has-text("Войти")'
                if await self.wait_for_element(
                    extra_login_button, "Кнопка 'Войти' для дополнительной проверки", timeout=3000
                ):
                    await self.click_button(
                        extra_login_button,
                        "Кнопка 'Войти' для дополнительной проверки",
                        wait_for_navigation=True,
                    )

                # Затем ввод кода
                await self.wait_for_element(extra_otp_selector, "Поле дополнительного кода")
                extra_otp_code = await self.get_user_input(
                    "Введите код, отправленный на email (6 цифр)"
                )
                await self.fill_input(
                    extra_otp_selector, extra_otp_code, "Дополнительный код"
                )
                await self._human_delay(2.0, "Ожидание обработки дополнительного кода")

            # Шаг 8: Ожидание загрузки страницы товаров
            await self._human_delay(3.0, "Ожидание загрузки страницы товаров")

            # Шаг 9: Поиск и нажатие кнопки "Скачать шаблоны"
            download_button_selector = 'span.c9r90-a2:has-text("Скачать шаблоны")'
            await self.wait_for_element(
                download_button_selector, "Кнопка 'Скачать шаблоны'", timeout=15000
            )
            
            # Сбрасываем путь к файлу перед кликом
            self.downloaded_file_path = None
            
            # Ожидаем событие скачивания
            async with self.page.expect_download(timeout=30000) as download_info:
                await self.click_button(
                    download_button_selector, "Скачать шаблоны", wait_for_navigation=False
                )

            # Шаг 10: Обработка скачанного файла
            download = await download_info.value
            filename = download.suggested_filename
            
            if not filename.endswith('.xlsx'):
                logger.warning(f"Скачан файл не в формате XLSX: {filename}")
            
            filepath = self.downloads_dir / filename
            await download.save_as(filepath)
            
            # Проверяем, что файл действительно создан
            if filepath.exists():
                file_size = filepath.stat().st_size
                logger.success(
                    f"Файл успешно скачан: {filepath} (размер: {file_size} байт)"
                )
                return filepath
            else:
                logger.error("Файл не был создан после скачивания")
                return None

        except Exception as e:
            logger.error(f"ОШИБКА В ПРОЦЕССЕ ВЫПОЛНЕНИЯ: {e}")
            logger.exception("Детали ошибки:")
            raise

    async def close(self) -> None:
        """Закрытие браузера."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Браузер закрыт")

