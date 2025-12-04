# Инструкция по настройке проекта на новом устройстве

Этот документ содержит все специфичные настройки проекта, которые необходимо настроить при переносе на новое устройство.

## 📋 Содержание

1. [Системные требования](#системные-требования)
2. [Установка зависимостей](#установка-зависимостей)
3. [Настройка окружения](#настройка-окружения)
4. [Специфичные настройки устройства](#специфичные-настройки-устройства)
5. [Хардкод в коде](#хардкод-в-коде)
6. [Проверка работоспособности](#проверка-работоспособности)

---

## Системные требования

### Обязательные компоненты:

- **ОС**: Windows 10/11 (проект настроен для Windows, но может работать на Linux/macOS с небольшими изменениями)
- **Python**: 3.10 или выше
- **Google Chrome**: последняя версия (для Selenium)
- **Git**: для клонирования репозитория (опционально)

### Проверка установки:

```bash
# Проверка Python
python --version
# Должно быть: Python 3.10.x или выше

# Проверка Chrome
# Откройте Chrome и введите в адресной строке: chrome://version/
# Убедитесь, что Chrome установлен
```

---

## Установка зависимостей

### 1. Клонирование/копирование проекта

```bash
# Если используете Git
git clone <repository-url>
cd OzonPriceParse

# Или просто скопируйте папку проекта на новое устройство
```

### 2. Создание виртуального окружения

```bash
# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate
```

### 3. Установка Python-зависимостей

```bash
# Установка всех зависимостей
pip install -r requirements.txt

# Проверка установки
pip list
```

### 4. Установка браузеров для Playwright (если используется)

```bash
playwright install chromium
```

---

## Настройка окружения

### 1. Создание файла .env

```bash
# Windows
copy env.example .env

# Linux/Mac
cp env.example .env
```

### 2. Заполнение обязательных параметров в .env

Откройте файл `.env` в текстовом редакторе и заполните следующие параметры:

#### ⚠️ ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ:

```env
# Номер телефона для входа в Ozon Seller
PHONE_NUMBER=+79966444210

# Telegram бот (получите токен у @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_PASSWORD=your_password_here
```

#### 📝 ОПЦИОНАЛЬНЫЕ ПАРАМЕТРЫ:

```env
# URL для старта (если отличается от стандартного)
OZON_START_URL=https://seller.ozon.ru/app/products

# Профиль Chrome (см. раздел ниже)
CHROME_USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data
CHROME_PROFILE_NAME=Profile 1

# Google Sheets интеграция (если используется)
UPLOAD_TO_GOOGLE_SHEETS=true
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
GOOGLE_SHEETS_CREDENTIALS_PATH=google_sheets_credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=YOUR_SPREADSHEET_ID
```

---

## Специфичные настройки устройства

### 1. Настройка профиля Chrome

**ВАЖНО**: Для сохранения авторизации в Ozon Seller необходимо настроить профиль Chrome.

#### Шаг 1: Найдите путь к профилю Chrome

**Windows:**
1. Откройте Chrome с нужным профилем
2. Введите в адресной строке: `chrome://version/`
3. Найдите строку "Путь к профилю" (Profile Path)
4. Пример: `C:\Users\ВашеИмя\AppData\Local\Google\Chrome\User Data\Profile 1`

**Или используйте универсальный путь:**
```env
CHROME_USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data
```

#### Шаг 2: Определите имя профиля

Из пути профиля возьмите последнюю часть:
- Если путь: `...\User Data\Profile 1` → имя профиля: `Profile 1`
- Если путь: `...\User Data\Default` → имя профиля: `Default`

#### Шаг 3: Добавьте в .env

```env
# Универсальный путь (рекомендуется)
CHROME_USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data
CHROME_PROFILE_NAME=Profile 1

# Или полный путь
# CHROME_USER_DATA_DIR=C:\Users\ВашеИмя\AppData\Local\Google\Chrome\User Data
# CHROME_PROFILE_NAME=Profile 1
```

#### Шаг 4: Первая авторизация

1. Откройте Chrome с этим профилем вручную
2. Авторизуйтесь на Ozon Seller один раз
3. Закройте Chrome полностью
4. Теперь скрипт будет использовать сохранённую сессию

**⚠️ ВАЖНО**: Не запускайте Chrome вручную одновременно с запущенным скриптом!

### 2. Настройка Google Sheets (если используется)

#### Шаг 1: Создание Service Account

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите API:
   - Google Sheets API
   - Google Drive API
4. Создайте Service Account:
   - Перейдите в "IAM & Admin" → "Service Accounts"
   - Нажмите "Create Service Account"
   - Заполните данные и создайте
5. Создайте ключ:
   - Откройте созданный Service Account
   - Перейдите в "Keys" → "Add Key" → "Create new key"
   - Выберите формат JSON
   - Скачайте файл

#### Шаг 2: Настройка доступа к таблице

1. Откройте скачанный JSON файл
2. Найдите поле `client_email` (например: `ozon-parser@project-id.iam.gserviceaccount.com`)
3. Откройте вашу Google таблицу
4. Нажмите "Поделиться" (Share)
5. Добавьте email из `client_email` с правами "Редактор" (Editor)
6. Сохраните JSON файл в корень проекта как `google_sheets_credentials.json`

#### Шаг 3: Добавьте в .env

```env
UPLOAD_TO_GOOGLE_SHEETS=true
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
GOOGLE_SHEETS_CREDENTIALS_PATH=google_sheets_credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=YOUR_SPREADSHEET_ID
```

**Где взять SPREADSHEET_ID:**
- Из URL таблицы: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
- Скопируйте часть между `/d/` и `/edit`

### 3. Настройка Telegram бота

#### Шаг 1: Создание бота

1. Откройте Telegram и найдите **@BotFather**
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: "Ozon Parser Bot")
   - Введите username бота (должен заканчиваться на `bot`, например: `ozon_parser_bot`)
4. BotFather отправит токен вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Скопируйте токен

#### Шаг 2: Добавьте в .env

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_PASSWORD=your_secure_password_here
```

**⚠️ ВАЖНО**: 
- Придумайте сложный пароль для доступа к боту
- Не публикуйте токен и пароль в открытом доступе
- Не коммитьте файл `.env` в git (он уже в `.gitignore`)

---

## Хардкод в коде

### ⚠️ ВАЖНО: Токен Ozon захардкожен в коде!

В следующих файлах есть захардкоженный токен Ozon, который **истекает**:

1. `src/main.py` (строки 22-28)
2. `run_selenium_download.py` (строки 24-30)
3. `src/bot/handlers.py` (в функции `run_parsing`)

**Текущий токен:**
```
eyJhbGciOiJIUzI1NiIsIm96b25pZCI6Im5vdHNlbnNpdGl2ZSIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo4NjYwNzMzNSwiaXNfcmVnaXN0cmF0aW9uIjpmYWxzZSwicmV0dXJuX3VybCI6Imh0dHBzOi8vc2VsbGVyLm96b24ucnUvYXBwL3Byb2R1Y3RzIiwicGF5bG9hZCI6bnVsbCwiZXhwIjoxNzY0MzQ3MDIxLCJpYXQiOjE3NjQzNDcwMTEsImlzcyI6Im96b25pZCJ9.xqCyVmJNVURosfFveqEuSIpYxTU-tNDNJeQt7VtzX14
```

**Дата истечения**: 2024-12-03 (проверьте актуальность!)

### Как получить новый токен:

1. Откройте браузер и авторизуйтесь на Ozon Seller
2. Перейдите на страницу товаров: `https://seller.ozon.ru/app/products`
3. Скопируйте URL полностью (он содержит токен)
4. Извлеките токен из URL: `https://seller.ozon.ru/app/products?token=ВАШ_ТОКЕН`
5. Замените токен во всех трёх файлах выше

**Или** используйте параметр `OZON_START_URL` в `.env` с полным URL включая токен.

### Номер телефона по умолчанию

В `src/config/settings.py` (строка 14) указан номер телефона по умолчанию:
```python
phone_number: str = "+79966444210"
```

Это значение переопределяется из `.env` файла, но если `.env` не настроен, будет использоваться этот номер.

---

## Проверка работоспособности

### 1. Проверка настроек

```bash
# Активируйте виртуальное окружение
venv\Scripts\activate

# Запустите проверку настроек
python -c "from src.config.settings import Settings; s = Settings(); print(f'Phone: {s.phone_number}'); print(f'Token: {s.telegram_bot_token[:20] if s.telegram_bot_token else None}...')"
```

### 2. Тестовый запуск бота

```bash
python run_bot.py
```

Ожидаемый вывод:
```
✓ Файл .env найден: D:\...\OzonPriceParse\.env
TELEGRAM_BOT_TOKEN из os.environ: установлен
TELEGRAM_BOT_PASSWORD из os.environ: установлен
Бот запущен и готов к работе!
```

### 3. Тестовый запуск парсера (без бота)

```bash
python run.py
```

Или:

```bash
python -m src.main
```

### 4. Проверка структуры проекта

Убедитесь, что существуют следующие папки:
- `downloads/` - для скачанных файлов
- `logs/` - для логов
- `venv/` - виртуальное окружение
- `.env` - файл настроек (не должен быть в git!)

---

## Чеклист настройки нового устройства

- [ ] Установлен Python 3.10+
- [ ] Установлен Google Chrome
- [ ] Проект скопирован на новое устройство
- [ ] Создано виртуальное окружение (`venv`)
- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Создан файл `.env` из `env.example`
- [ ] Заполнен `PHONE_NUMBER` в `.env`
- [ ] Настроен Telegram бот (токен и пароль в `.env`)
- [ ] Настроен профиль Chrome (если используется сохранение авторизации)
- [ ] Настроен Google Sheets (если используется)
- [ ] Обновлён токен Ozon в коде (если истёк)
- [ ] Проверена работоспособность бота (`python run_bot.py`)
- [ ] Проверена работоспособность парсера (`python run.py`)

---

## Частые проблемы

### Проблема: "TELEGRAM_BOT_PASSWORD не указан"

**Решение:**
1. Проверьте, что в `.env` файле строка не закомментирована (нет `#` в начале)
2. Убедитесь, что нет пробелов вокруг знака `=`
3. Убедитесь, что значение не пустое
4. Проверьте кодировку файла (должна быть UTF-8)

### Проблема: "Chrome профиль не найден"

**Решение:**
1. Проверьте путь к профилю Chrome в `.env`
2. Убедитесь, что Chrome закрыт перед запуском скрипта
3. Используйте универсальный путь: `%LOCALAPPDATA%\Google\Chrome\User Data`

### Проблема: "Токен Ozon истёк"

**Решение:**
1. Получите новый токен из URL Ozon Seller
2. Обновите токен в файлах: `src/main.py`, `run_selenium_download.py`, `src/bot/handlers.py`
3. Или используйте `OZON_START_URL` в `.env` с полным URL

### Проблема: "Google Sheets не загружается"

**Решение:**
1. Проверьте, что Service Account имеет доступ к таблице
2. Проверьте путь к `google_sheets_credentials.json`
3. Убедитесь, что включены Google Sheets API и Google Drive API

---

## Дополнительная информация

### Структура проекта

```
OzonPriceParse/
├── src/
│   ├── agents/          # Агенты для автоматизации
│   ├── bot/             # Telegram бот
│   ├── config/          # Настройки
│   └── utils/           # Утилиты
├── downloads/           # Скачанные файлы
├── logs/               # Логи приложения
├── pages_code/         # HTML страниц для справки
├── venv/               # Виртуальное окружение
├── .env                # Настройки (НЕ коммитить!)
├── requirements.txt    # Python зависимости
└── run_bot.py         # Запуск бота
```

### Логи

Логи сохраняются в папке `logs/` с именем `app_YYYY-MM-DD.log`

### Файлы результатов

Скачанные файлы сохраняются в папке `downloads/` с именем вида:
`Цены товаров_DD.MM.YYYY.xlsx`

---

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи в папке `logs/`
2. Проверьте настройки в `.env`
3. Убедитесь, что все зависимости установлены
4. Проверьте версию Python и Chrome

---

**Последнее обновление**: 2025-12-03
**Версия проекта**: 1.0.0

