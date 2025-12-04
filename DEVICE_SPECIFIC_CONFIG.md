# Специфичные настройки устройства

Этот файл содержит список всех настроек, которые **привязаны к конкретному устройству** и должны быть проверены/изменены при переносе проекта на новое устройство.

---

## 🔴 КРИТИЧЕСКИЕ НАСТРОЙКИ (обязательно изменить)

### 1. Токен Ozon Seller (истекает!)

**Файлы с захардкоженным токеном:**
- `src/main.py` (строки 22-28)
- `run_selenium_download.py` (строки 24-30)
- `src/bot/handlers.py` (функция `run_parsing`)

**Текущий токен:**
```
eyJhbGciOiJIUzI1NiIsIm96b25pZCI6Im5vdHNlbnNpdGl2ZSIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo4NjYwNzMzNSwiaXNfcmVnaXN0cmF0aW9uIjpmYWxzZSwicmV0dXJuX3VybCI6Imh0dHBzOi8vc2VsbGVyLm96b24ucnUvYXBwL3Byb2R1Y3RzIiwicGF5bG9hZCI6bnVsbCwiZXhwIjoxNzY0MzQ3MDIxLCJpYXQiOjE3NjQzNDcwMTEsImlzcyI6Im96b25pZCJ9.xqCyVmJNVURosfFveqEuSIpYxTU-tNDNJeQt7VtzX14
```

**Дата истечения**: 2024-12-03 (⚠️ ПРОВЕРЬТЕ АКТУАЛЬНОСТЬ!)

**Как обновить:**
1. Авторизуйтесь на Ozon Seller в браузере
2. Перейдите на `https://seller.ozon.ru/app/products`
3. Скопируйте полный URL (он содержит токен)
4. Замените токен во всех трёх файлах выше

**Или** используйте `.env`:
```env
OZON_START_URL=https://seller.ozon.ru/app/products?token=НОВЫЙ_ТОКЕН
```

---

### 2. Номер телефона

**Файл:** `.env`
```env
PHONE_NUMBER=+79966444210
```

**Также по умолчанию в:** `src/config/settings.py` (строка 14)

**Действие:** Измените на номер телефона для нового устройства/пользователя

---

### 3. Telegram бот токен и пароль

**Файл:** `.env`
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_PASSWORD=your_password_here
```

**Действие:** 
- Создайте нового бота через @BotFather (или используйте существующего)
- Установите новый пароль для доступа

---

## 🟡 ВАЖНЫЕ НАСТРОЙКИ (рекомендуется проверить)

### 4. Профиль Chrome

**Файл:** `.env`
```env
CHROME_USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data
CHROME_PROFILE_NAME=Profile 1
```

**Действие:**
1. Найдите путь к профилю Chrome на новом устройстве:
   - Откройте Chrome → `chrome://version/`
   - Найдите "Путь к профилю"
2. Определите имя профиля (Default, Profile 1, Profile 2 и т.д.)
3. Обновите значения в `.env`

**Примечание:** Если не указано, будет использоваться автоматическое определение пути для текущей ОС.

---

### 5. Google Sheets настройки (если используется)

**Файл:** `.env`
```env
UPLOAD_TO_GOOGLE_SHEETS=true
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
GOOGLE_SHEETS_CREDENTIALS_PATH=google_sheets_credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=SPREADSHEET_ID
```

**Файл:** `google_sheets_credentials.json` (в корне проекта)

**Действие:**
1. Скопируйте `google_sheets_credentials.json` на новое устройство
2. Или создайте новый Service Account и скачайте новый JSON файл
3. Обновите `GOOGLE_SHEETS_URL` и `GOOGLE_SHEETS_SPREADSHEET_ID` если используете другую таблицу

---

## 🟢 ОПЦИОНАЛЬНЫЕ НАСТРОЙКИ (можно оставить по умолчанию)

### 6. Пути к папкам

**Файл:** `.env`
```env
DOWNLOADS_DIR=downloads
LOGS_DIR=logs
```

**Действие:** Обычно можно оставить как есть (относительные пути). Если нужны абсолютные пути, укажите полный путь.

---

### 7. Настройки браузера

**Файл:** `.env`
```env
HEADLESS=false
BROWSER_TYPE=chromium
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080
```

**Действие:** Обычно можно оставить как есть. Измените только если нужны другие настройки.

---

### 8. Задержки (имитация человеческого поведения)

**Файл:** `.env`
```env
DELAY_BEFORE_CLICK=1.5
DELAY_AFTER_CLICK=2.0
DELAY_BEFORE_TYPE=0.8
DELAY_AFTER_TYPE=1.2
DELAY_BETWEEN_KEYS=0.1
DELAY_PAGE_LOAD=3.0
```

**Действие:** Обычно можно оставить как есть. Измените только если возникают проблемы с таймаутами.

---

## 📝 ФАЙЛЫ, КОТОРЫЕ НУЖНО ПРОВЕРИТЬ/СКОПИРОВАТЬ

### Обязательно скопировать:

- [ ] `.env` - файл настроек (⚠️ НЕ коммитить в git!)
- [ ] `google_sheets_credentials.json` - если используется Google Sheets
- [ ] Весь код проекта (`src/`, `run_bot.py`, `run.py` и т.д.)

### Не нужно копировать (создаются автоматически):

- `venv/` - виртуальное окружение (создать заново)
- `downloads/` - папка для скачанных файлов (создастся автоматически)
- `logs/` - папка для логов (создастся автоматически)
- `__pycache__/` - кэш Python (создастся автоматически)

---

## 🔍 ЧЕКЛИСТ ПЕРЕНОСА НА НОВОЕ УСТРОЙСТВО

### Перед переносом:

- [ ] Проверить актуальность токена Ozon (может истечь!)
- [ ] Сохранить текущий `.env` файл
- [ ] Сохранить `google_sheets_credentials.json` (если используется)
- [ ] Записать текущие настройки профиля Chrome

### На новом устройстве:

- [ ] Установить Python 3.10+
- [ ] Установить Google Chrome
- [ ] Скопировать проект
- [ ] Создать виртуальное окружение
- [ ] Установить зависимости
- [ ] Создать `.env` из `env.example`
- [ ] Заполнить обязательные параметры в `.env`:
  - [ ] `PHONE_NUMBER`
  - [ ] `TELEGRAM_BOT_TOKEN`
  - [ ] `TELEGRAM_BOT_PASSWORD`
- [ ] Обновить токен Ozon в коде (если истёк)
- [ ] Настроить профиль Chrome (если используется)
- [ ] Скопировать `google_sheets_credentials.json` (если используется)
- [ ] Проверить работоспособность

---

## 📌 БЫСТРАЯ СПРАВКА

### Где что находится:

| Настройка | Файл | Строка/Раздел |
|-----------|------|---------------|
| Токен Ozon | `src/main.py` | 22-28 |
| Токен Ozon | `run_selenium_download.py` | 24-30 |
| Токен Ozon | `src/bot/handlers.py` | функция `run_parsing` |
| Номер телефона | `.env` | `PHONE_NUMBER` |
| Номер телефона (по умолчанию) | `src/config/settings.py` | 14 |
| Telegram токен | `.env` | `TELEGRAM_BOT_TOKEN` |
| Telegram пароль | `.env` | `TELEGRAM_BOT_PASSWORD` |
| Профиль Chrome | `.env` | `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_NAME` |
| Google Sheets | `.env` | `GOOGLE_SHEETS_*` |
| Google Sheets credentials | `google_sheets_credentials.json` | корень проекта |

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **Токен Ozon истекает!** Проверяйте актуальность перед каждым запуском или используйте `OZON_START_URL` в `.env`.

2. **Файл `.env` НЕ должен быть в git!** Он уже добавлен в `.gitignore`, но проверьте перед коммитом.

3. **Профиль Chrome** - если используете сохранение авторизации, убедитесь, что Chrome закрыт перед запуском скрипта.

4. **Google Sheets credentials** - файл содержит секретные ключи, не публикуйте его в открытом доступе.

5. **Telegram токен и пароль** - также секретные данные, не публикуйте их.

---

**Последнее обновление**: 2025-12-03
