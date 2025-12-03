"""Запуск Telegram бота для парсера Ozon."""
import asyncio
from loguru import logger

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from src.config.settings import Settings
from src.bot.handlers import (
    start_command,
    parse_command,
    status_command,
    logs_command,
    download_command,
    guide_command,
    settings_command,
    logout_command,
    message_handler
)
from src.utils.logger import setup_logger


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже или проверьте логи."
            )
        except:
            pass


def main():
    """Основная функция запуска бота."""
    # Настраиваем логирование сначала (для диагностики)
    from pathlib import Path
    logs_dir = Path("logs")
    setup_logger(logs_dir)
    
    # Диагностика: проверяем наличие .env файла
    env_file = Path(".env")
    if not env_file.exists():
        logger.error(f"Файл .env не найден в {env_file.absolute()}")
        logger.info("Скопируйте env.example в .env и заполните настройки")
        return
    
    logger.info(f"✓ Файл .env найден: {env_file.absolute()}")
    
    # Загружаем настройки
    settings = Settings()
    
    # Диагностика: проверяем значения напрямую из os.environ
    import os
    from dotenv import load_dotenv
    
    # Читаем .env файл напрямую для диагностики
    try:
        with open(".env", "r", encoding="utf-8") as f:
            env_content = f.read()
            logger.debug("Содержимое .env файла:")
            # Показываем только строки с TELEGRAM (скрывая значения)
            for line in env_content.split("\n"):
                if "TELEGRAM" in line.upper():
                    # Скрываем значение после =
                    if "=" in line:
                        key, value = line.split("=", 1)
                        logger.debug(f"  {key.strip()}={'*' * min(len(value.strip()), 20)}")
                    else:
                        logger.debug(f"  {line}")
    except Exception as e:
        logger.warning(f"Не удалось прочитать .env файл: {e}")
    
    load_dotenv(override=True)  # Явно загружаем .env с перезаписью
    
    # Проверяем все переменные, начинающиеся с TELEGRAM
    all_telegram_vars = {k: v for k, v in os.environ.items() if "TELEGRAM" in k.upper()}
    logger.info(f"Все переменные TELEGRAM из os.environ: {list(all_telegram_vars.keys())}")
    
    token_from_env = os.getenv("TELEGRAM_BOT_TOKEN")
    password_from_env = os.getenv("TELEGRAM_BOT_PASSWORD")
    
    # Проверяем варианты с разным регистром
    password_variants = [
        os.getenv("TELEGRAM_BOT_PASSWORD"),
        os.getenv("telegram_bot_password"),
        os.getenv("Telegram_Bot_Password"),
    ]
    
    logger.info(f"TELEGRAM_BOT_TOKEN из os.environ: {'установлен' if token_from_env else 'НЕ УСТАНОВЛЕН'}")
    if token_from_env:
        logger.debug(f"  Первые 10 символов токена: {token_from_env[:10]}...")
        logger.debug(f"  Длина токена: {len(token_from_env)} символов")
    logger.info(f"TELEGRAM_BOT_PASSWORD из os.environ: {'установлен' if password_from_env else 'НЕ УСТАНОВЛЕН'}")
    if password_from_env:
        logger.debug(f"  Длина пароля: {len(password_from_env)} символов")
        logger.debug(f"  Пароль (первые 3 символа): {password_from_env[:3]}...")
    else:
        logger.warning("Пароль не найден в os.environ!")
        logger.debug(f"  Проверенные варианты: {[bool(v) for v in password_variants]}")
    
    logger.info(f"telegram_bot_token из Settings: {'установлен' if settings.telegram_bot_token else 'НЕ УСТАНОВЛЕН'}")
    logger.info(f"telegram_bot_password из Settings: {'установлен' if settings.telegram_bot_password else 'НЕ УСТАНОВЛЕН'}")
    
    # Проверяем, может быть значение пустое или только пробелы
    if password_from_env is not None:
        password_stripped = password_from_env.strip()
        if not password_stripped:
            logger.warning("TELEGRAM_BOT_PASSWORD найден, но значение пустое или содержит только пробелы!")
        else:
            logger.info(f"TELEGRAM_BOT_PASSWORD найден и не пустой (длина: {len(password_stripped)})")
    
    # Проверяем наличие токена
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не указан в .env файле!")
        logger.info("Получите токен у @BotFather в Telegram и добавьте его в .env")
        logger.info("Формат в .env: TELEGRAM_BOT_TOKEN=your_token_here")
        logger.info("ВАЖНО: Без пробелов вокруг знака =, без кавычек")
        if token_from_env:
            logger.warning(f"Но токен найден в os.environ! Возможно проблема с pydantic-settings")
            logger.info("Попробуем использовать токен из os.environ...")
            settings.telegram_bot_token = token_from_env
        else:
            return
    
    # Проверяем наличие пароля
    if not settings.telegram_bot_password:
        if password_from_env and password_from_env.strip():
            logger.warning("Пароль найден в os.environ, но не загружен в Settings!")
            logger.info("Используем пароль из os.environ...")
            settings.telegram_bot_password = password_from_env.strip()
        else:
            logger.error("TELEGRAM_BOT_PASSWORD не указан в .env файле!")
            logger.info("Укажите пароль для доступа к боту в .env")
            logger.info("Формат в .env: TELEGRAM_BOT_PASSWORD=your_password_here")
            logger.info("ВАЖНО: Без пробелов вокруг знака =, без кавычек")
            logger.info("Проверьте, что строка не закомментирована (нет # в начале)")
            return
    
    # Финальная проверка
    if not settings.telegram_bot_password or not settings.telegram_bot_password.strip():
        logger.error("TELEGRAM_BOT_PASSWORD пустой или содержит только пробелы!")
        return
    
    logger.info("=" * 60)
    logger.info("Запуск Telegram бота для парсера Ozon")
    logger.info("=" * 60)
    
    # Создаём приложение
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("parse", parse_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CommandHandler("guide", guide_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("logout", logout_command))
    
    # Регистрируем обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    logger.info("Найдите вашего бота в Telegram и отправьте /start")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
