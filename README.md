# AI Expense Tracker Bot

Telegram бот для учета расходов с использованием искусственного интеллекта (Gemini 2.0).
Бот позволяет записывать расходы текстовыми сообщениями, голосовыми сообщениями и фотографиями чеков.

## Функционал

### Бесплатные функции:
* Добавление расходов текстовыми сообщениями
* Категоризация расходов
* Базовая аналитика
* До 3-х распознаваний чеков по фото
* Управление бюджетом

### Премиум функции (оплата через Telegram Stars):
* Безлимитное распознавание чеков по фото
* Распознавание голосовых сообщений
* Продвинутая аналитика с графиками
* Экспорт данных (CSV, Excel)

## Стек технологий
* Python 3.11+
* Aiogram 3.x
* SQLAlchemy 2.0 (Async) + PostgreSQL (asyncpg)
* Alembic (Миграции)
* Google Generative AI (Gemini)
* Docker & Docker Compose

## Быстрый старт (Docker)

1. Склонируйте репозиторий:
```bash
git clone <url>
cd ai-expense-tracker
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```
И заполните его своими данными (BOT_TOKEN, GEMINI_API_KEY и т.д.)

3. Запустите проект через Docker Compose:
```bash
docker-compose up -d --build
```

## Ручная установка (без Docker)

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Поднимите PostgreSQL и создайте базу данных `expense_tracker`

3. Настройте `.env` файл

4. Запустите миграции Alembic:
```bash
alembic upgrade head
```

5. Запустите бота:
```bash
python -m bot.main
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| BOT_TOKEN | Токен вашего Telegram бота | - |
| DATABASE_URL | Строка подключения к БД | postgresql+asyncpg://postgres:postgres@localhost:5432/expense_tracker |
| GEMINI_API_KEY | API ключ Google Gemini | - |
| ADMIN_IDS | Список ID администраторов (JSON массив) | [] |
| MONTHLY_STARS_PRICE | Стоимость премиум подписки в месяц (в звездах) | 150 |
| YEARLY_STARS_PRICE | Стоимость премиум подписки в год (в звездах) | 1500 |
| FREE_RECEIPT_LIMIT | Лимит бесплатных чеков | 3 |
| GEMINI_MODEL | Модель Gemini для текста | gemini-2.0-flash |
| GEMINI_VISION_MODEL | Модель Gemini для изображений | gemini-2.0-flash |

## Структура проекта
* `bot/` - Исходный код бота
  * `handlers/` - Обработчики сообщений
  * `database/` - Модели БД и подключение
  * `services/` - Бизнес-логика (Gemini, и т.д.)
  * `middlewares/` - Middleware (Auth, Throttling)
* `alembic/` - Миграции базы данных

## Лицензия
MIT
