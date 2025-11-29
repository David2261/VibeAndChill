# Vibe&Chill — Интернет-магазин

**Vibe&Chill** — это интернет-магазин для продажи товаров с функциональностью корзины, личного кабинета, отзывов, рейтингов и администрирования. Проект реализован на Python с использованием Flask и PostgreSQL.

## Основные возможности

* Просмотр каталога товаров с фильтрацией по категориям, цене, популярности и другим параметрам
* Корзина: добавление, редактирование и удаление товаров
* Личный кабинет пользователя: управление профилем, просмотр истории заказов
* Оставление отзывов и рейтингов товаров
* Административная панель: управление пользователями, ролями, товарами, заказами и аналитикой
* Интеграция с платёжными системами и службами доставки
* Безопасность: защита от SQL-инъекций, XSS, валидация вводимых данных

## Стек технологий

* **Python** 3.10+
* **Flask** — веб-фреймворк
* **Flask-Login** — управление сессиями пользователей
* **Flask-Admin** — административный интерфейс
* **SQLAlchemy** — ORM для работы с PostgreSQL
* **PostgreSQL** — база данных
* **Poetry** — управление зависимостями и виртуальным окружением

## Установка и запуск

1. Клонировать репозиторий:

```bash
git clone <репозиторий>
cd vibe-and-chill
```

2. Установить Poetry, если ещё не установлен:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Установить зависимости:

```bash
poetry install
```

4. Создать файл `.env` и настроить переменные окружения (пример):

```
FLASK_APP=main.py
FLASK_ENV=development
DATABASE_URL=postgresql://username:password@localhost:5432/vibeandchill
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secret
```

5. Инициализировать базу данных:

```bash
psql -U <user> -d <database> -f database/create_database.sql
psql -U <user> -d <database> -f database/insert_test_data.sql
```

6. Запустить приложение:

```bash
poetry run flask run
```

Приложение будет доступно по адресу: `http://127.0.0.1:5000`

## Структура проекта

* `main.py` — инициализация Flask-приложения и админки
* `models.py` — ORM-модели базы данных
* `admin.py` — конфигурация административного интерфейса
* `routes.py` — маршруты для пользователей
* `templates/` — HTML-шаблоны
* `static/` — изображения и статические файлы
* `database/` — SQL-скрипты и ER-диаграммы
* `tests/` — тесты функциональности, безопасности и производительности

## Тестирование

* Безопасность: `python tests/test_security.py`
* Производительность: `python tests/test_performance.py` (требуется запущенный сервер)
* PageSpeed Insights: `python tests/pagespeed_insights.py` (требуется PAGESPEED_API_KEY и PAGESPEED_TARGET_URL)

## Лицензия

Проект распространяется под лицензией GNU GENERAL PUBLIC LICENSE.
