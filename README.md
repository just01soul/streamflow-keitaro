# Streamflow

Веб-интерфейс для управления кампаниями в рекламном трекере **Keitaro**. Позволяет создавать кампании с двумя потоками (белый + офферный) и редактировать список офферов в существующих кампаниях.

## Возможности

- **Создание кампании** — форма с полями: имя, GEO-код страны, оффер, домен, группа, источник трафика. Создаёт кампанию в Keitaro с двумя потоками:
  - `White (Google)` — белый поток: ловит трафик из указанной страны и редиректит на Google.
  - `Offer` — офферный поток: редиректит на выбранный оффер.
- **Редактор офферов** — загружает кампанию по ID, показывает её потоки и список офферов, позволяет добавлять и удалять офферы в потоке.
- **Лог действий** — каждое создание и обновление записывается в PostgreSQL (таблица `campaign_logs`).

## Стек

| Компонент | Технология |
|---|---|
| Backend | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Драйвер БД | asyncpg |
| Миграции | Alembic |
| HTTP-клиент | httpx |
| Конфиг | Pydantic Settings |
| БД | PostgreSQL 14+ |
| Frontend | HTML + Vanilla JS + Tailwind CSS (локально) |

## Требования

- **Python** 3.12+
- **PostgreSQL** 14+

## Установка

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd Streamflow
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
```

Активировать:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat
```

### 3. Установить зависимости

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Настроить переменные окружения

Скопировать `.env.example` в `.env`:

```bash
# Linux / macOS
cp .env.example .env

# Windows
Copy-Item .env.example .env
```

Открыть `.env` и вписать реальные значения:

```env
KEITARO_BASE_URL=https://tlgk.host/admin_api/v1
KEITARO_API_KEY=ваш-ключ-из-админки-Keitaro
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/streamflow
APP_DEBUG=false
```

**Где взять `KEITARO_API_KEY`:** в админке Keitaro → раздел **Admin API** → скопировать ключ.

### 5. Создать базу данных

Если БД `streamflow` ещё нет — создать одним из способов:

**Через psql:**

```bash
psql -U postgres -h localhost -c "CREATE DATABASE streamflow;"
```

**Через pgAdmin:** правой кнопкой на **Databases** → **Create** → **Database** → Name: `streamflow`.

**Через Python (если psql не установлен):**

Создать файл `create_db.py`:

```python
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        user="postgres", password="postgres",
        host="localhost", port=5432, database="postgres",
    )
    try:
        await conn.execute("CREATE DATABASE streamflow")
        print("База streamflow создана")
    except asyncpg.exceptions.DuplicateDatabaseError:
        print("База streamflow уже существует")
    finally:
        await conn.close()

asyncio.run(main())
```

Запустить: `python create_db.py`.

### 6. Применить миграции

```bash
alembic upgrade head
```

Создаст таблицу `campaign_logs`.

### 7. Запустить приложение

```bash
uvicorn app.main:app --reload
```

После запуска доступны:

- **Фронт:** http://127.0.0.1:8000/static/
- **Swagger:** http://127.0.0.1:8000/docs
- **Healthcheck:** http://127.0.0.1:8000/health

## Миграции (Alembic)

```bash
# Создать новую миграцию после изменения моделей
alembic revision --autogenerate -m "описание изменений"

# Применить все миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1

# Текущая ревизия
alembic current

# История миграций
alembic history
```

## API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/campaigns` | Создать кампанию с двумя потоками |
| `GET` | `/api/campaigns/{id}` | Получить кампанию с потоками и офферами |
| `POST` | `/api/streams/{id}/offers` | Заменить список офферов в потоке |
| `GET` | `/api/domains` | Список доменов Keitaro |
| `GET` | `/api/groups` | Список групп кампаний |
| `GET` | `/api/sources` | Список источников трафика |
| `GET` | `/api/offers` | Список офферов |
| `GET` | `/health` | Проверка живости сервера |

Полная документация — в Swagger UI (`/docs`).

## Структура проекта

```
Streamflow/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI-приложение, эндпоинты, lifespan
│   ├── config.py            # настройки из .env (Pydantic Settings)
│   ├── database.py          # engine, сессия, Base
│   ├── models.py            # модель CampaignLog
│   ├── schemas.py           # Pydantic-схемы запросов и ответов
│   ├── keitaro_client.py    # async-клиент Keitaro Admin API
│   └── services.py          # бизнес-логика (создание кампании, обновление офферов)
├── alembic/
│   ├── env.py               # async-окружение Alembic
│   ├── script.py.mako
│   └── versions/            # файлы миграций
├── static/
│   ├── index.html           # фронт (форма + редактор)
├── .env.example             # пример переменных окружения
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```