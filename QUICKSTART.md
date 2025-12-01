# Быстрый старт

## 1. Установка зависимостей

```bash
# Активируйте виртуальное окружение (если еще не активировано)
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/Mac

# Установите зависимости
pip install -r requirements.txt

# Установите браузеры для Playwright
playwright install chromium
```

## 2. Настройка

Создайте файл `.env` (если еще не создан) и укажите:

```env
PHONE_NUMBER=+79966444210
```

Остальные настройки можно оставить по умолчанию.

## 3. Запуск

```bash
python run.py
```

Или:

```bash
python -m src.main
```

## 4. Что происходит

1. Откроется браузер (видимый)
2. Скрипт автоматически выполнит все шаги
3. **Когда потребуется код из пуш-уведомления** - скрипт остановится и попросит вас ввести код
4. После ввода кода скрипт продолжит работу
5. Файл XLSX будет скачан в папку `downloads/`

## Важно

- ⚠️ Браузер будет видимым - вы сможете наблюдать весь процесс
- ⚠️ При любой ошибке скрипт остановится и выведет сообщение
- ⚠️ Все действия логируются в консоль и в файлы `logs/`

## Устранение проблем

**Ошибка: "playwright не установлен"**
```bash
pip install playwright
playwright install chromium
```

**Ошибка: "Модуль не найден"**
```bash
pip install -r requirements.txt
```

**Браузер не открывается**
- Проверьте, что `HEADLESS=false` в `.env`
- Убедитесь, что установлен браузер: `playwright install chromium`

## 5. Коммит и пуш в новую ветку

```bash
# Создайте новую ветку
git checkout -b dev/browser-automation

# Добавьте все изменения
git add .

# Создайте коммит
git commit -m "feat: добавлена автоматизация браузера для парсинга цен Ozon"

# Отправьте ветку в удаленный репозиторий
git push -u origin dev/browser-automation
```

Или если хотите использовать другое имя ветки:

```bash
git checkout -b feature/ozon-parser
git add .
git commit -m ""
git push -u origin feature/ozon-parser
```

