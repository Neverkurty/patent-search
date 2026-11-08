# Paten — семантический поиск по патентам ФИПС

Monorepo: парсер → PostgreSQL + pgvector → FastAPI → React (Vite).

## Быстрый старт

### 1. База данных

```bash
cd paten
docker compose up -d
copy .env.example .env
```

PostgreSQL слушает порт **5433** (если локально уже занят 5432).

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Проверка: http://localhost:8000/health

### 3. Загрузка данных

```bash
# Сначала сгенерировать или спарсить parser/output/patents_dump.json
python scripts/load_data.py
```

### 4. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Поиск в реальном времени

- В UI: ввод запроса и кнопка «Найти патенты» → запрос к API с `"live": true`.
- Бэкенд при `live=true` запрашивает ФИПС (Selenium), сохраняет новые патенты в БД и выполняет гибридный поиск.
- Нужны Chrome и пакеты `selenium`, `undetected-chromedriver` в venv бэкенда.
- Кэш запросов к ФИПС: 5 минут (`FIPS_SEARCH_CACHE_TTL`).

### Ошибка ChromeDriver / Chrome version mismatch

Если в ответе `ChromeDriver only supports Chrome version 149` при браузере 148, добавьте в `.env`:

```env
CHROME_VERSION_MAIN=148
```

Бэкенд сам пробует версии Chrome ±1, но явная настройка надёжнее. Обновите Chrome до последней версии — тогда можно удалить эту переменную.

```bash
curl -X POST http://localhost:8000/api/v1/search -H "Content-Type: application/json" -d "{\"query\": \"нейросеть\", \"top_k\": 10, \"mode\": \"hybrid\", \"live\": true}"
```

## Структура

- `contracts/patent.schema.json` — контракт данных parser ↔ loader ↔ API
- `parser/` — сбор данных с ФИПС
- `backend/` — API и поиск
- `frontend/` — веб-интерфейс
