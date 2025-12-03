"""Обработчики команд и сообщений Telegram бота."""
import asyncio
import threading
from pathlib import Path
from typing import Optional

from loguru import logger
from telegram import Update, Document
from telegram.ext import ContextTypes

from src.agents.browser_agent import BrowserAgent
from src.config.settings import Settings
from src.bot.state_manager import StateManager
from src.bot.utils import format_logs, get_last_log_file


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    
    # Проверяем авторизацию
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text(
            "🔐 Для использования бота необходимо авторизоваться.\n\n"
            "Введите пароль:"
        )
        StateManager.set_waiting_for_password(user_id, True)
        return
    
    await update.message.reply_text(
        "👋 Добро пожаловать в бот парсера Ozon!\n\n"
        "Доступные команды:\n"
        "/parse - Запустить парсинг цен\n"
        "/status - Статус последнего запуска\n"
        "/logs - Последние логи\n"
        "/download - Скачать последний файл\n"
        "/guide - Гайд по установке\n"
        "/settings - Настройки\n"
        "/logout - Выйти из аккаунта"
    )


async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /parse - запуск парсинга."""
    user_id = update.effective_user.id
    
    # Проверяем авторизацию
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text("❌ Вы не авторизованы. Используйте /start")
        return
    
    # Проверяем, не запущен ли уже парсинг
    if StateManager.is_parsing_active(user_id):
        await update.message.reply_text("⏳ Парсинг уже выполняется. Подождите завершения.")
        return
    
    await update.message.reply_text("🚀 Запускаю парсинг...")
    
    # Запускаем парсинг в отдельном потоке
    thread = threading.Thread(
        target=run_parsing,
        args=(user_id, context.bot, update.effective_chat.id),
        daemon=True
    )
    thread.start()
    
    StateManager.set_parsing_active(user_id, True)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /status - статус последнего запуска."""
    user_id = update.effective_user.id
    
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text("❌ Вы не авторизованы. Используйте /start")
        return
    
    status = StateManager.get_parsing_status(user_id)
    if not status:
        await update.message.reply_text("ℹ️ Парсинг ещё не запускался.")
        return
    
    status_text = f"📊 Статус последнего запуска:\n\n"
    status_text += f"Статус: {status.get('status', 'Неизвестно')}\n"
    status_text += f"Время: {status.get('time', 'Неизвестно')}\n"
    
    if status.get('error'):
        status_text += f"\n❌ Ошибка: {status['error']}"
    elif status.get('file_path'):
        status_text += f"\n✅ Файл: {Path(status['file_path']).name}"
    
    await update.message.reply_text(status_text)


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /logs - последние логи."""
    user_id = update.effective_user.id
    
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text("❌ Вы не авторизованы. Используйте /start")
        return
    
    log_file = get_last_log_file()
    if not log_file:
        await update.message.reply_text("ℹ️ Логи не найдены.")
        return
    
    logs_text = format_logs(log_file, lines=50)
    
    if len(logs_text) > 4096:
        # Если лог слишком длинный, отправляем частями
        parts = [logs_text[i:i+4096] for i in range(0, len(logs_text), 4096)]
        for part in parts:
            await update.message.reply_text(f"```\n{part}\n```", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"```\n{logs_text}\n```", parse_mode='Markdown')


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /download - скачать последний файл."""
    user_id = update.effective_user.id
    
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text("❌ Вы не авторизованы. Используйте /start")
        return
    
    status = StateManager.get_parsing_status(user_id)
    if not status or not status.get('file_path'):
        await update.message.reply_text("❌ Файл не найден. Запустите парсинг через /parse")
        return
    
    file_path = Path(status['file_path'])
    if not file_path.exists():
        await update.message.reply_text("❌ Файл не найден на диске.")
        return
    
    try:
        await update.message.reply_document(
            document=open(file_path, 'rb'),
            filename=file_path.name
        )
        
        # Отправляем ссылку на Google таблицу, если есть
        if status.get('google_sheets_url'):
            await update.message.reply_text(
                f"📊 Google таблица: {status['google_sheets_url']}"
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await update.message.reply_text(f"❌ Ошибка при отправке файла: {e}")


async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /guide - гайд по установке."""
    guide_text = """📖 ГАЙД ПО УСТАНОВКЕ ПАРСЕРА OZON

1️⃣ УСТАНОВКА PYTHON
   • Скачайте Python 3.10+ с https://www.python.org/downloads/
   • При установке отметьте "Add Python to PATH"
   • Проверьте установку: откройте командную строку и введите:
     python --version

2️⃣ УСТАНОВКА GIT (опционально)
   • Скачайте Git с https://git-scm.com/download/win
   • Установите с настройками по умолчанию

3️⃣ КЛОНИРОВАНИЕ ПРОЕКТА
   • Откройте командную строку (Win+R, введите cmd)
   • Перейдите в нужную папку:
     cd D:\\Projects
   • Клонируйте репозиторий:
     git clone <URL_РЕПОЗИТОРИЯ>
   • Или распакуйте архив проекта

4️⃣ СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ
   • Перейдите в папку проекта:
     cd OzonPriceParse
   • Создайте виртуальное окружение:
     python -m venv venv
   • Активируйте его:
     venv\\Scripts\\activate

5️⃣ УСТАНОВКА ЗАВИСИМОСТЕЙ
   • Установите зависимости:
     pip install -r requirements.txt
   • Установите браузеры для Playwright (если используется):
     playwright install chromium

6️⃣ НАСТРОЙКА ОКРУЖЕНИЯ
   • Скопируйте env.example в .env:
     copy env.example .env
   • Откройте .env в текстовом редакторе
   • Заполните необходимые параметры:
     - PHONE_NUMBER - ваш номер телефона
     - TELEGRAM_BOT_TOKEN - токен бота (получите у @BotFather)
     - TELEGRAM_BOT_PASSWORD - пароль для доступа к боту

7️⃣ НАСТРОЙКА GOOGLE SHEETS (опционально)
   • Создайте проект в Google Cloud Console
   • Включите Google Sheets API и Google Drive API
   • Создайте Service Account
   • Скачайте JSON файл с credentials
   • Положите его в корень проекта как google_sheets_credentials.json
   • Укажите путь в .env: GOOGLE_SHEETS_CREDENTIALS_PATH

8️⃣ ЗАПУСК БОТА
   • Активируйте виртуальное окружение (если не активировано):
     venv\\Scripts\\activate
   • Запустите бота:
     python run_bot.py

9️⃣ ИСПОЛЬЗОВАНИЕ
   • Найдите вашего бота в Telegram
   • Отправьте /start
   • Введите пароль (из .env файла)
   • Используйте команды:
     /parse - запустить парсинг
     /status - статус
     /logs - логи
     /download - скачать файл

❓ ПРОБЛЕМЫ?
   • Проверьте, что Python установлен: python --version
   • Проверьте, что виртуальное окружение активировано
   • Проверьте, что все зависимости установлены: pip list
   • Проверьте логи в папке logs/
"""
    
    await update.message.reply_text(guide_text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /settings - настройки."""
    user_id = update.effective_user.id
    
    if not StateManager.is_authorized(user_id):
        await update.message.reply_text("❌ Вы не авторизованы. Используйте /start")
        return
    
    settings = Settings()
    settings_text = "⚙️ Текущие настройки:\n\n"
    settings_text += f"Телефон: {settings.phone_number}\n"
    settings_text += f"Папка загрузок: {settings.downloads_dir}\n"
    settings_text += f"Папка логов: {settings.logs_dir}\n"
    settings_text += f"Headless режим: {'Да' if settings.headless else 'Нет'}\n"
    
    if settings.upload_to_google_sheets:
        settings_text += f"\n📊 Google Sheets: Включено\n"
        if settings.google_sheets_url:
            settings_text += f"URL: {settings.google_sheets_url}"
    else:
        settings_text += f"\n📊 Google Sheets: Выключено"
    
    await update.message.reply_text(settings_text)


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /logout - выход из аккаунта."""
    user_id = update.effective_user.id
    StateManager.logout(user_id)
    await update.message.reply_text("👋 Вы вышли из аккаунта. Для входа используйте /start")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Обработка пароля
    if StateManager.is_waiting_for_password(user_id):
        settings = Settings()
        if text == settings.telegram_bot_password:
            StateManager.set_authorized(user_id, True)
            StateManager.set_waiting_for_password(user_id, False)
            await update.message.reply_text("✅ Авторизация успешна! Используйте /start для просмотра команд.")
        else:
            await update.message.reply_text("❌ Неверный пароль. Попробуйте ещё раз.")
        return
    
    # Обработка кода 2FA
    if StateManager.is_waiting_for_2fa(user_id):
        code = text.strip()
        if code.isdigit() and len(code) == 6:
            StateManager.set_2fa_code(user_id, code)
            await update.message.reply_text("✅ Код получен. Продолжаю парсинг...")
        else:
            await update.message.reply_text("❌ Код должен состоять из 6 цифр. Попробуйте ещё раз.")
        return
    
    # Обработка дополнительного кода (extraOtp)
    if StateManager.is_waiting_for_extra_otp(user_id):
        code = text.strip()
        if code.isdigit() and len(code) == 6:
            StateManager.set_extra_otp_code(user_id, code)
            await update.message.reply_text("✅ Дополнительный код получен. Продолжаю парсинг...")
        else:
            await update.message.reply_text("❌ Код должен состоять из 6 цифр. Попробуйте ещё раз.")
        return
    
    # Неизвестное сообщение
    await update.message.reply_text("❓ Неизвестная команда. Используйте /start для просмотра доступных команд.")


def _send_message_sync(bot, chat_id: int, text: str) -> None:
    """Отправка сообщения синхронно из потока."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.send_message(chat_id=chat_id, text=text))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


def _send_document_sync(bot, chat_id: int, file_path: Path) -> None:
    """Отправка документа синхронно из потока."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with open(file_path, 'rb') as f:
            loop.run_until_complete(bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=file_path.name
            ))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке документа: {e}")


def run_parsing(user_id: int, bot, chat_id: int) -> None:
    """Запуск парсинга в отдельном потоке."""
    try:
        settings = Settings()
        from src.utils.logger import setup_logger
        setup_logger(settings.logs_dir)
        
        # Создаём агента с callback для 2FA
        agent = BrowserAgentWithTelegram(settings, user_id, bot, chat_id)
        
        # URL для старта
        start_url = (
            "https://seller.ozon.ru/app/products?token="
            "eyJhbGciOiJIUzI1NiIsIm96b25pZCI6Im5vdHNlbnNpdGl2ZSIsInR5cCI6IkpXVCJ9."
            "eyJ1c2VyX2lkIjo4NjYwNzMzNSwiaXNfcmVnaXN0cmF0aW9uIjpmYWxzZSwicmV0dXJuX3VybCI6"
            "Imh0dHBzOi8vc2VsbGVyLm96b24ucnUvYXBwL3Byb2R1Y3RzIiwicGF5bG9hZCI6bnVsbCwiZXhw"
            "IjoxNzY0MzQ3MDIxLCJpYXQiOjE3NjQzNDcwMTEsImlzcyI6Im96b25pZCJ9."
            "xqCyVmJNVURosfFveqEuSIpYxTU-tNDNJeQt7VtzX14"
        )
        
        # Уведомление о начале
        _send_message_sync(bot, chat_id, "🚀 Парсинг запущен...")
        
        # Запускаем парсинг
        downloaded_file = agent.execute_flow(start_url)
        
        # Обновляем статус
        from datetime import datetime
        status = {
            'status': 'completed',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'file_path': str(downloaded_file) if downloaded_file else None,
            'google_sheets_url': settings.google_sheets_url if settings.upload_to_google_sheets else None
        }
        StateManager.set_parsing_status(user_id, status)
        StateManager.set_parsing_active(user_id, False)
        
        if downloaded_file:
            # Отправляем файл
            _send_message_sync(bot, chat_id, "✅ Парсинг завершён успешно!")
            _send_document_sync(bot, chat_id, downloaded_file)
            
            # Отправляем ссылку на Google таблицу
            if settings.upload_to_google_sheets and settings.google_sheets_url:
                _send_message_sync(bot, chat_id, f"📊 Google таблица: {settings.google_sheets_url}")
        else:
            _send_message_sync(bot, chat_id, "⚠️ Парсинг завершён, но файл не был скачан.")
        
        agent.close()
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        error_msg = f"❌ Ошибка при парсинге: {str(e)}"
        _send_message_sync(bot, chat_id, error_msg)
        
        status = {
            'status': 'error',
            'time': "Неизвестно",
            'error': str(e)
        }
        StateManager.set_parsing_status(user_id, status)
        StateManager.set_parsing_active(user_id, False)


class BrowserAgentWithTelegram(BrowserAgent):
    """Расширенный BrowserAgent с поддержкой Telegram для 2FA."""
    
    def __init__(self, settings: Settings, user_id: int, bot, chat_id: int):
        super().__init__(settings)
        self.user_id = user_id
        self.bot = bot
        self.chat_id = chat_id
    
    def get_user_input(self, prompt: str) -> str:
        """Запрос ввода от пользователя через Telegram."""
        logger.warning(f"ТРЕБУЕТСЯ ВВОД ОТ ПОЛЬЗОВАТЕЛЯ: {prompt}")
        
        # Определяем тип кода
        is_2fa = "пуш-уведомления" in prompt.lower() or "otp" in prompt.lower()
        is_extra_otp = "email" in prompt.lower() or "extraotp" in prompt.lower()
        
        # Отправляем запрос через Telegram
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if is_2fa:
                StateManager.set_waiting_for_2fa(self.user_id, True)
                loop.run_until_complete(self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"🔐 {prompt}\n\nВведите код из Telegram:"
                ))
            elif is_extra_otp:
                StateManager.set_waiting_for_extra_otp(self.user_id, True)
                loop.run_until_complete(self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"🔐 {prompt}\n\nВведите код из email:"
                ))
            else:
                loop.run_until_complete(self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"🔐 {prompt}\n\nВведите код:"
                ))
            
            loop.close()
        except Exception as e:
            logger.error(f"Ошибка при отправке запроса кода: {e}")
        
        # Ждём код
        max_wait = 300  # 5 минут
        waited = 0
        import time
        
        while waited < max_wait:
            if is_2fa:
                code = StateManager.get_2fa_code(self.user_id)
                if code:
                    StateManager.set_waiting_for_2fa(self.user_id, False)
                    StateManager.set_2fa_code(self.user_id, None)
                    logger.info(f"Пользователь ввёл код: {code[:2]}** (скрыто)")
                    return code
            elif is_extra_otp:
                code = StateManager.get_extra_otp_code(self.user_id)
                if code:
                    StateManager.set_waiting_for_extra_otp(self.user_id, False)
                    StateManager.set_extra_otp_code(self.user_id, None)
                    logger.info(f"Пользователь ввёл дополнительный код: {code[:2]}** (скрыто)")
                    return code
            
            time.sleep(1)
            waited += 1
        
        # Сбрасываем флаги при таймауте
        StateManager.set_waiting_for_2fa(self.user_id, False)
        StateManager.set_waiting_for_extra_otp(self.user_id, False)
        raise TimeoutError("Превышено время ожидания ввода кода")
