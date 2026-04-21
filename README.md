# r_crm — Yangi Mahalla

CRM-система для продаж квартир в многоквартирных жилых комплексах.

## Стек

- **Backend**: Python 3.12, Django 5.1, DRF, PostgreSQL 16, Celery 5.4, Redis 7
- **Frontend**: Vue 3, Vite, TypeScript, Pinia, Tailwind CSS, PrimeVue 4
- **Auth**: JWT (simplejwt)
- **i18n**: `ru`, `uz` (латиница), `oz` (кириллица)
- **Docs**: OpenAPI через drf-spectacular
- **Infra**: Docker Compose

## Структура репозитория

```
.
├── backend/      # Django + DRF
├── frontend/     # Vue 3 + Vite
├── docker/       # Dockerfiles
├── docs/         # Документация (архитектура, ADR)
├── scripts/      # Утилиты (миграция легаси, и т.д.)
└── docker-compose.yml
```

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

Открыть:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/
- API docs: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/

## Разработка

```bash
# Бэкенд — тесты
docker compose exec backend pytest

# Бэкенд — линт
docker compose exec backend ruff check .
docker compose exec backend ruff format .

# Фронт — тайпчек + линт
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
```

См. [CLAUDE.md](CLAUDE.md) для конвенций разработки.

## Документация

- [Архитектура](docs/architecture.md)
- [Именование моделей](CLAUDE.md#naming)
- [Миграция с легаси](docs/legacy_migration.md) (появится в Этапе 9)
