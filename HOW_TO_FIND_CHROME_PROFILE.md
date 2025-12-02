# Как найти имя папки профиля Chrome

## Быстрый способ (рекомендуется)

1. **Откройте Chrome с нужным профилем** (например, "Евгений Рыбаков")

2. **В адресной строке введите:** `chrome://version/`

3. **Найдите строку "Путь к профилю"** (или "Profile Path")

4. **Скопируйте последнюю часть пути:**
   - Если путь: `C:\...\User Data\Profile 1` → имя профиля: **`Profile 1`**
   - Если путь: `C:\...\User Data\Profile 2` → имя профиля: **`Profile 2`**
   - Если путь: `C:\...\User Data\Default` → имя профиля: **`Default`**

5. **Используйте это имя в `.env`:**
   ```env
   CHROME_USER_DATA_DIR=C:\Пользователи\fisher\AppData\Local\Google\Chrome\User Data
   CHROME_PROFILE_NAME=Profile 1
   ```

## Альтернативный способ

1. Откройте папку `User Data` в проводнике:
   ```
   C:\Пользователи\fisher\AppData\Local\Google\Chrome\User Data
   ```

2. Там вы увидите папки: `Default`, `Profile 1`, `Profile 2` и т.д.

3. Чтобы понять, какая папка соответствует вашему профилю:
   - Откройте файл `User Data\Local State` в текстовом редакторе (Notepad++)
   - Нажмите Ctrl+F и найдите имя вашего профиля (например, "Евгений Рыбаков")
   - Рядом будет указано имя папки (например, `"profile_path": "Profile 1"`)

## Пример для вашего случая

Если у вас профиль "Евгений Рыбаков":
1. Откройте Chrome с профилем "Евгений Рыбаков"
2. Перейдите на `chrome://version/`
3. Посмотрите "Путь к профилю"
4. Скорее всего там будет `Profile 1` или `Profile 2`
5. Используйте это имя в `.env`

## Важно помнить

- **Имя папки** — это `Profile 1`, `Profile 2`, `Default` и т.д.
- **НЕ используйте** отображаемое имя пользователя ("Евгений Рыбаков", "Павел" и т.д.)
- Это техническое имя папки, а не имя пользователя!

## Универсальные пути для разных устройств

### Windows
Используйте переменную окружения `%LOCALAPPDATA%` или стандартный путь:
```env
# Вариант 1: Использование переменной окружения (рекомендуется)
CHROME_USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data

# Вариант 2: Полный путь (замените YourUsername на ваше имя пользователя)
CHROME_USER_DATA_DIR=C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data
```

### Linux
```env
CHROME_USER_DATA_DIR=~/.config/google-chrome
```

### macOS
```env
CHROME_USER_DATA_DIR=~/Library/Application Support/Google/Chrome
```

## Инсайты из успешной настройки

**Что помогло найти профиль:**
1. ✅ Использование `os.path.exists()` вместо `Path.exists()` для лучшей совместимости с Windows
2. ✅ Преобразование пути в абсолютный через `Path.absolute()` перед проверкой
3. ✅ Использование строкового представления пути для проверки существования
4. ✅ Проверка существования как папки `User Data`, так и папки профиля внутри неё

**Важно:** 
- Путь должен указывать **только до папки `User Data`**, без имени профиля
- Имя профиля указывается отдельно в `CHROME_PROFILE_NAME`
- Пример правильной настройки:
  ```env
  CHROME_USER_DATA_DIR=C:\Users\fisher\AppData\Local\Google\Chrome\User Data
  CHROME_PROFILE_NAME=Profile 2
  ```
- НЕ указывайте имя профиля в пути `CHROME_USER_DATA_DIR`!

