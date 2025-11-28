# Инструкция по тестовому запуску

## 📋 Что нужно для запуска

### 1. Установка зависимостей
```bash
# Создать виртуальное окружение (если еще не создано)
python -m venv venv

# Активировать виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка API ключей Ozon

Создайте файл `.env` в корне проекта на основе `env.example`:

```bash
# Скопировать пример
cp env.example .env
```

Заполните в `.env`:
```
OZON_CLIENT_ID=ваш_client_id
OZON_API_KEY=ваш_api_key
```

**Где взять ключи:**
- Зайдите в личный кабинет Ozon Seller
- Перейдите в раздел "Настройки" → "API ключи"
- Создайте новый API ключ или используйте существующий
- Скопируйте Client-ID и API Key

### 3. Подготовка списка товаров

Создайте файл со списком ID товаров. Поддерживаются форматы:

**Вариант 1: Текстовый файл** (`data/products.txt`)
```
12345
67890
11111
22222
# Комментарии начинаются с #
```

**Вариант 2: CSV файл** (`data/products.csv`)
```csv
product_id
12345
67890
11111
22222
```

**Вариант 3: Прямо в коде** (для быстрого теста)
- Отредактируйте `src/main.py`, строка 37

---

## 🚀 Поэтапный процесс запуска

### Этап 1: Инициализация и проверка

**Что происходит:**
1. Запускается логирование (`setup_logger()`)
2. Проверяется наличие API ключей в `.env`
3. Если ключей нет → ошибка и выход

**Логи:**
```
2024-11-26 22:00:00 | INFO     | Запуск приложения OzonPriceParse
```

**Код:**
```python
# src/main.py, строки 15-24
setup_logger()
logger.info("Запуск приложения OzonPriceParse")

if not settings.ozon_client_id or not settings.ozon_api_key:
    logger.error("Ozon API credentials не настроены...")
    sys.exit(1)
```

---

### Этап 2: Инициализация агента

**Что происходит:**
1. Создается экземпляр `OzonAPIAgent`
2. Загружаются настройки из конфига
3. Настраивается rate limiting

**Логи:**
```
2024-11-26 22:00:00 | INFO     | Инициализирован агент: OzonAPIAgent
```

**Код:**
```python
# src/main.py, строки 27-33
agent = OzonAPIAgent(config={
    "client_id": settings.ozon_client_id,
    "api_key": settings.ozon_api_key,
    "batch_size": settings.batch_size,  # 1000
    "request_delay": settings.request_delay,  # 0.2 сек
    "max_requests_per_minute": settings.max_requests_per_minute,  # 60
})
```

---

### Этап 3: Загрузка списка товаров

**Что происходит:**
1. Загружается список ID товаров
2. Пока захардкожен в коде: `["12345", "67890"]`
3. В будущем: загрузка из файла

**Логи:**
```
2024-11-26 22:00:00 | INFO     | Начало парсинга 2 товаров
```

**Код:**
```python
# src/main.py, строка 37
product_ids = ["12345", "67890"]  # TODO: загрузка из файла
```

---

### Этап 4: Парсинг цен (основной процесс)

**Что происходит:**

#### 4.1. Разбивка на батчи
- Товары разбиваются на батчи по 1000 штук (лимит API)
- Для 2 товаров = 1 батч

**Логи:**
```
2024-11-26 22:00:00 | INFO     | Начало парсинга 2 товаров через Ozon Seller API
2024-11-26 22:00:00 | INFO     | Обработка батча 1/1 (2 товаров)
```

**Код:**
```python
# src/agents/ozon_api_agent.py, строки 94-96
for batch_start in range(0, len(product_ids), self.batch_size):
    batch = product_ids[batch_start:batch_start + self.batch_size]
    batch_num = (batch_start // self.batch_size) + 1
```

#### 4.2. Rate limiting
- Проверяется лимит запросов (60/минуту)
- Если лимит достигнут → ожидание
- Минимальная задержка 0.2 сек между запросами

**Логи:**
```
2024-11-26 22:00:00 | DEBUG    | Отправка запроса к API: 2 товаров
```

**Код:**
```python
# src/agents/ozon_api_agent.py, строка 49
await self._rate_limit()
```

#### 4.3. HTTP запрос к API
- Отправляется POST запрос к `https://api-seller.ozon.ru/v5/product/info/prices`
- Headers: `Client-Id`, `Api-Key`, `Content-Type`
- Payload: фильтр `visibility: "ALL"`, limit: 1000

**Логи:**
```
2024-11-26 22:00:00 | DEBUG    | Payload: {'filter': {'visibility': 'ALL'}, 'limit': 2, 'cursor': ''}
2024-11-26 22:00:00 | DEBUG    | Ответ API получен: 1234 байт
```

**Код:**
```python
# src/agents/ozon_api_agent.py, строки 155-170
response = await client.post(
    self.api_url,
    json=payload,
    headers=headers
)
response_data = response.json()
```

#### 4.4. Парсинг ответа
- Извлекаются товары из ответа (`items` или `result.items`)
- Сопоставляются с запрошенными ID
- Извлекаются все поля цен

**Логи:**
```
2024-11-26 22:00:00 | DEBUG    | Получено 2 товаров из API
2024-11-26 22:00:00 | DEBUG    | Товар 12345: price=999.0, marketing_seller_price=899.0
2024-11-26 22:00:00 | INFO     | Батч 1 завершен: получено 2 цен
```

**Код:**
```python
# src/agents/ozon_api_agent.py, строки 177-220
items_list = response_data.get("items", [])
for item in items_list:
    price_data = self._extract_price_data(item)
    results[matched_id] = price_data
```

#### 4.5. Обработка ошибок
- Если товар не найден → помечается как ошибка
- Если ошибка API → логируется и пропускается

**Логи:**
```
2024-11-26 22:00:00 | WARNING  | Товар 67890 не найден в ответе API
```

---

### Этап 5: Экспорт результатов

**Что происходит:**
1. Создается директория `data/output/`
2. Результаты экспортируются в CSV
3. Результаты экспортируются в XLSX (если установлен openpyxl)

**Логи:**
```
2024-11-26 22:00:01 | INFO     | Результаты экспортированы в CSV: data/output/prices_main.csv
2024-11-26 22:00:01 | INFO     | Результаты экспортированы в XLSX: data/output/prices_main.xlsx
```

**Код:**
```python
# src/main.py, строки 44-59
output_dir = Path("data/output")
csv_path = output_dir / f"prices_{timestamp}.csv"
export_results(results, str(csv_path), format="csv")
export_results(results, str(xlsx_path), format="xlsx")
```

---

### Этап 6: Статистика и завершение

**Что происходит:**
1. Подсчитывается количество успешных и ошибочных запросов
2. Выводится итоговая статистика
3. Программа завершается

**Логи:**
```
2024-11-26 22:00:01 | INFO     | Парсинг завершен: 1 успешно, 1 ошибок
2024-11-26 22:00:01 | INFO     | Результаты сохранены: data/output/prices_main.csv
2024-11-26 22:00:01 | INFO     | Парсинг завершен: 1 успешно, 1 ошибок, время: 1.23 сек (0.02 мин)
```

**Код:**
```python
# src/main.py, строки 61-68
success_count = sum(1 for v in results.values() if "error" not in v)
error_count = len(results) - success_count
logger.info(f"Парсинг завершен: {success_count} успешно, {error_count} ошибок")
```

---

## 📊 Пример полного лога запуска

```
2024-11-26 22:00:00 | INFO     | Запуск приложения OzonPriceParse
2024-11-26 22:00:00 | INFO     | Инициализирован агент: OzonAPIAgent
2024-11-26 22:00:00 | INFO     | Начало парсинга 2 товаров
2024-11-26 22:00:00 | INFO     | Начало парсинга 2 товаров через Ozon Seller API
2024-11-26 22:00:00 | INFO     | Обработка батча 1/1 (2 товаров)
2024-11-26 22:00:00 | DEBUG    | Отправка запроса к API: 2 товаров
2024-11-26 22:00:00 | DEBUG    | Payload: {'filter': {'visibility': 'ALL'}, 'limit': 2, 'cursor': ''}
2024-11-26 22:00:00 | DEBUG    | Ответ API получен: 1234 байт
2024-11-26 22:00:00 | DEBUG    | Получено 2 товаров из API
2024-11-26 22:00:00 | DEBUG    | Товар 12345: price=999.0, marketing_seller_price=899.0
2024-11-26 22:00:00 | WARNING  | Товар 67890 не найден в ответе API
2024-11-26 22:00:00 | INFO     | Батч 1 завершен: получено 1 цен
2024-11-26 22:00:01 | INFO     | Парсинг завершен: 1 успешно, 1 ошибок, время: 1.23 сек (0.02 мин)
2024-11-26 22:00:01 | INFO     | Результаты экспортированы в CSV: data/output/prices_main.csv
2024-11-26 22:00:01 | INFO     | Результаты экспортированы в XLSX: data/output/prices_main.xlsx
2024-11-26 22:00:01 | INFO     | Парсинг завершен: 1 успешно, 1 ошибок
2024-11-26 22:00:01 | INFO     | Результаты сохранены: data/output/prices_main.csv
```

---

## 🔧 Команда для запуска

```bash
# Активировать виртуальное окружение
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/Mac

# Вариант 1: Запуск через run.py (рекомендуется)
python run.py

# Вариант 2: Запуск через модуль
python -m src.main

# Вариант 3: Прямой запуск (требует установки пакета)
python src/main.py
```

---

## ⚠️ Возможные проблемы

### Ошибка: "Ozon API credentials не настроены"
**Решение:** Проверьте файл `.env`, убедитесь что `OZON_CLIENT_ID` и `OZON_API_KEY` заполнены

### Ошибка: "Товар не найден в ответе API"
**Причина:** Товар с таким ID не существует в вашем кабинете Ozon
**Решение:** Используйте реальные ID товаров из вашего кабинета

### Ошибка: "Rate limit exceeded"
**Причина:** Слишком много запросов
**Решение:** Увеличьте `REQUEST_DELAY` в `.env` или уменьшите `MAX_REQUESTS_PER_MINUTE`

### Ошибка: "openpyxl не установлен"
**Решение:** `pip install openpyxl` (XLSX экспорт необязателен, CSV работает)

---

## 📝 Формат выходных файлов

### CSV файл (`data/output/prices_main.csv`)
```csv
product_id,offer_id,matched_id,price,old_price,marketing_seller_price,currency,available,timestamp
12345,OFFER-123,12345,999.0,1199.0,899.0,RUB,True,2024-11-26T22:00:00
67890,,67890,,,,RUB,False,2024-11-26T22:00:00,Товар не найден в ответе API,NotFound
```

### XLSX файл
Та же структура, но в формате Excel

