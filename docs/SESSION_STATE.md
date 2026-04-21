# Session state — где остановились и что дальше

> Обновляется в конце каждой рабочей сессии. Следующий Claude (или я сам после паузы) должен прочитать этот файл **первым**, чтобы продолжить работу без повторного проектирования.

## Последняя сессия — 21 апреля 2026

### Что сделано

**Этапы 0 и 1 полностью закрыты и протестированы.**

#### Этап 0 — Foundation

- Монорепо: `backend/`, `frontend/`, `docker/`, `docs/`, `scripts/`
- Корневые файлы: `.gitignore`, `README.md`, `CLAUDE.md` (с glossary имён и конвенциями), `.env.example`, `.pre-commit-config.yaml`, `docker-compose.yml`
- Backend: Django 5.1 + Python 3.12, 9 apps (`core`, `users`, `references`, `objects`, `clients`, `contracts`, `finance`, `notifications`, `reports`), настройки в `conf/settings/{base,dev,prod}.py`, DRF + simplejwt + drf-spectacular + django-filter + celery-beat
- `apps/core/`: `BaseModel`, `I18nField` (ru/uz/oz), `MoneyField`, `AreaField`, `PercentField`, `SoftDeleteManager`, `AuditLog` модель + middleware, `HasPermission` DRF-класс, endpoint `/api/v1/health/`
- Frontend: Vite + Vue 3 + TypeScript (strict) + Pinia + Router + Tailwind + PrimeVue 4 (unstyled) + vue-i18n@9 + CASL + axios с JWT-refresh interceptor; base layout (AppShell/Sidebar/Topbar), LoginView, DashboardView, NotFoundView, ForbiddenView; три локали `ru/uz/oz` в `src/i18n/locales/`
- Docker Compose: `postgres:16`, `redis:7`, `backend`, `worker`, `beat`, `frontend`, `libreoffice` (кастомный Dockerfile в `docker/libreoffice.Dockerfile` для docx→pdf)
- `scripts/legacy_inspect.py` — дамп схемы легаси-БД в `docs/legacy_schema.md`
- Тесты: pytest-django + ruff + факторис
- Pre-commit hooks настроены

#### Этап 1 — Auth, Roles, Permission Tree

- `Role` с JSON-полем `permissions` формата `{dotted_key: bool}`, авто-дозаполняется всеми ключами дерева при save
- `Staff` (UUID PK, email-auth): `full_name`, `phone_number` (+998 regex), `language`, `theme`, `photo`, `role` FK (PROTECT)
- **Permission tree** в `apps/core/permission_tree.py` — hardcoded, 4 уровня, ~100 leaf-ключей, I18n-labels на 3 языках. Helpers: `all_permission_keys()`, `default_permissions()`
- **Check-семантика**: parent-off-disables-children (если `objects` = False, то `objects.apartments.book` недоступен)
- Endpoints `/api/v1/`:
  - `POST /auth/login/` → `{access, refresh, user}`
  - `POST /auth/refresh/`, `POST /auth/logout/`, `GET /auth/me/`
  - `GET /permissions/tree/`
  - `GET/POST/PATCH/DELETE /staff/` + `POST /staff/:id/reset-password/`
  - `GET/POST/PATCH/DELETE /roles/`
- Admin: Role + Staff с кастомным fieldset-раскладом
- Frontend: `stores/auth.ts`, `stores/permissions.ts` (CASL sync), router-guards по `meta.permission`; экраны `views/admin/UsersView.vue`, `RolesView.vue`, `RoleEditView.vue` + компонент `PermissionTreeEditor.vue` (рекурсивный cascade-toggle)
- Админ-юзер: `admin@rcrm.local` / `admin12345` (суперюзер, создан через shell)
- **40/40 backend-тестов зелёные**, vue-tsc 0 ошибок

### Инфраструктурное состояние

**Docker стек поднят на локальной машине пользователя**. Все 8 контейнеров работают:

```
rcrm_postgres_legacy   (отдельная sandbox-БД на порту 5433, с дампом 2025-11-06.sql)
rcrm_frontend          (Vite dev server — http://localhost:5173)
rcrm_beat              (Celery beat)
rcrm_worker            (Celery worker)
rcrm_backend           (Django runserver — http://localhost:8000)
rcrm_postgres          (основная dev-БД на 5432)
rcrm_redis             (на 6379)
rcrm_libreoffice       (на 2002, для docx→pdf в будущих этапах)
```

**Важное про Docker**: Docker Desktop ранее падал с `context canceled` из-за orphan WSL-дистрибутива `docker-desktop-data`. Удалён через `wsl --unregister docker-desktop-data`. Актуальная WSL-папка Docker — `F:\Docker\WSL\DockerDesktopWSL\main` (на C: только 4 ГБ свободно, нельзя класть туда образы).

### Архитектурные решения, зафиксированные с пользователем

1. **Иерархия объектов 6-уровневая** (не 4 как в архитектуре): `Developer → Project → Building → Section → Floor → Apartment`. Имена чистые (не `Flat`/`Stage` из старого кода). Mapping зафиксирован в `CLAUDE.md#naming`.
2. **`Customer` = `ClientContact`** — представитель клиента с паспортом/ИНН. Не отдельная сущность.
3. **Ипотека убрана**: только `Contract.is_mortgage: BooleanField` маркер, без арифметики `MortgageCurrency`.
4. **`Contract.action` workflow сохранён**: `request/wait/edit/approve/sign_in` (с экраном «Запросы на редактирование»).
5. **Файлы без `GenericForeignKey`**: три узкие таблицы — `DiscountRuleHistory.document`, `BuildingPhoto`, `Infrastructure.icon`. 99% файлов в легаси прикреплены к `discountpercenthistory` (3277 из 3320).
6. **Task Manager убран**.
7. **i18n = `{ru, uz, oz}`** — три языка, `JSONField` формата `{"ru": ..., "uz": ..., "oz": ...}`.
8. **Audit log** (357K строк легаси) **переносим** в `core.AuditLog`.
9. **Одна роль на Staff** (`ForeignKey`, не M2M).
10. **Дропаем**: Kanban, Презентация, Над проектами работали, SalesBPM, SaleOrder, KnowledgeBase (большинство справочников пересоздаются чистыми), BotSite, News, MortgageCurrency.

### Легаси-БД — что известно

Дамп `C:\Users\howka\Downloads\Telegram Desktop\2025-11-06.sql` (78 МБ) восстановлен в `rcrm_postgres_legacy:5433/zk_legacy` (юзер `zk_user`, пароль `rawa0040`). Полный отчёт по 135 таблицам + FK → `docs/legacy_schema.md` (72 КБ).

**Ключевые цифры**:
- 5 ЖК, 41 корпус, 80 подъездов, 957 этажей, **8 193 квартиры**
- **158 796 Calculation-строк** (8193 × ~19 % оплаты)
- 37 DiscountPercent, 56 DiscountPercentHistory
- 2 202 клиентов, 2 225 представителей, **3 023 договоров**, 4 074 графиков платежей
- **5 841 финансовых транзакций**
- 65 сотрудников, 8 ролей
- 8 SMS-шаблонов
- 3 320 прикреплённых файлов (3277 — акты скидок)
- 357 093 audit-записей

## План следующих этапов

### Этап 2 — References (следующий!)

Состав:
- `references.Developer` (застройщик): name, address, director, email, phone, bank_name, bank_account, inn, nds, oked, + JSONField для расширения
- `references.SalesOffice` (отдел продаж): name, address, latitude/longitude, work_start/work_end, photo
- `references.Currency`: code, symbol, rate (Decimal, курс к UZS)
- Справочники из knowledge_base старого кода — собираем чистые:
  - `references.ApartmentType` (квартира/апартамент/нежилое)
  - `references.RoomType`
  - `references.ConstructionStage` (этап строительства)
  - `references.Decoration`, `PremisesDecoration` (отделка)
  - `references.HomeMaterial`, `OutputWindows`, `OccupiedBy`
  - `references.Badge` (тэги квартир)
  - `references.PaymentMethod`, `PaymentInPercent`
  - `references.Region`, `Location`
- Все с `I18nField` для названий
- CRUD viewsets + admin
- Frontend: экраны справочников (список + CRUD), карта Leaflet для `SalesOffice`
- Тесты

Оценочно: **2 дня**.

### Этап 3 — Objects domain (самый сложный — 5-7 дней)

Главный этап. Модели:
- `Project` (ЖК): FK Developer, title, address, description, banks JSONField, `contract_number_index` (счётчик номеров договоров)
- `Building` (корпус): FK Project, cadastral_number, date_of_issue, planning_file, title, number, sort
- `Section` (подъезд): FK Building, title, sort, planning FK
- `Floor` (этаж): FK Section, number, `price_per_sqm` (Decimal), sort, planning FK
- `Apartment` (квартира): FK Floor, number, rooms_count, area (Decimal), `total_bti_area`, total_price (расчётное), surcharge, planning FK, status (CharField с choices: свободно/забронировано/бронь_руководство/оформлено/эскроу/продано), `booking_expires_at`, is_duplex, is_studio, is_euro_planning, decoration FK, output_window FK, occupied_by FK, characteristics M2M
- `ApartmentStatusLog`: apartment, old_status, new_status, changed_by (Staff), comment, created_at
- `PriceHistory`: floor, old_price, new_price, changed_by, created_at
- `PaymentPlan`: FK Project (не на Building!), name, `down_payment_percent`, `installment_months`, sort
- `DiscountRule`: FK Project, `area_start`/`area_end`, `payment_percent` (FK PaymentInPercent), `discount_percent`, is_duplex
- `Calculation`: FK Apartment, FK PaymentInPercent, `discount_percent`, installment_months, new_price_per_sqm, new_total_price, initial_fee, monthly_payment
- **`services/pricing.py`**: ЯВНЫЕ функции `recalc_apartment(apartment)`, `recalc_floor(floor)`, `recalc_project(project)`. Вызывать из ViewSet / management command, **не из сигналов** (это было багом старого кода).
- **`services/booking.py`**: `book_apartment(apartment, duration_days, by_staff)` с `select_for_update`, `release_booking()`, transition логируется в `ApartmentStatusLog`.
- CRUD viewsets + кастомные actions (`book`, `release`, `change_status`)
- Permissions по дереву: `objects.projects.*`, `objects.apartments.*`, etc.
- Frontend: hierarchical navigation Project → Building → Section → Floor → Apartments grid (SVG/HTML checkerboard). Клик по квартире → карточка со статусом и историей статусов.
- Экран редактирования цен этажа с подтверждением (каскад пересчёта отражается сразу)
- Тесты: pricing-каскад, booking-конкурентность (`select_for_update` работает), status-transitions

### Этап 4 — Clients (2 дня)

- `Client`: entity (phys/jur), gender, full_name, phones[] ArrayField, emails[] ArrayField, inn, oked, pin, birth_date (для phys), address, description, FK Staff (manager), FK status, groups M2M
- `ClientContact` (бывший Employee): FK Client, name, role (директор/подписант), is_chief, phones[], `passport` JSONField (серия, номер, кем выдан, дата выдачи, адрес прописки), birth_date, inn, pin
- `Requisite`: FK Client, type (internal/local), bank_requisite JSONField (счёт, банк, MFO)
- Frontend: список + карточка с табами (Договоры / Контакты / Реквизиты / Заметки)

### Этап 5 — Contracts (6-7 дней)

- `Contract`: FK Client, FK Apartment (через Calculation), FK Staff (author), FK signer (ClientContact, опционально), contract_number (уникальный в рамках Project), date, total_amount, down_payment, payment_type, `action` enum (request/wait/edit/approve/sign_in), is_signed, is_mortgage, requisite JSONField (snapshot реквизитов продавца на момент подписания), document JSONField (snapshot полей), old JSONField (предыдущие версии), file (PDF), qr (image), description, related_person (подписант-физлицо)
- `ContractTemplate`: file (.docx), placeholders
- `PaymentSchedule`: FK Contract, due_date, amount, paid_amount, debt, status
- `Payment`: FK PaymentSchedule, amount, payment_type, FK recorded_by, comment, created_at
- `services/contracts.py`: генерация номера, расчёт schedule, workflow transitions
- `services/docgen.py`: python-docx → заполнение → libreoffice headless → PDF + QR
- 3 экрана: «Не подписанные», «Подписанные», «Запросы на редактирование»
- Wizard создания договора

### Этап 6 — Finance (3-4 дня)

- `FinanceRecord`: type (income/expense), payment_type (cash/bank/barter), amount, FK Contract, FK Payment, receipt_number, description, date, FK Cashbox
- `services/pko.py`: ПКО PDF через ReportLab + DejaVu-шрифты + `num2words` (ru/uz)
- Экспорт/импорт Excel через openpyxl
- Дашборд по объектам × месяцам (Chart.js)

### Этап 7 — Notifications / SMS (3-4 дня)

- `SmsTemplate`: I18nField body с плейсхолдерами (@name, @contract_number и т.д.)
- `ManualSms`: связка с отправкой
- `AutoSms`: period (annual/quarterly/monthly), day, month, filters
- `NotificationLog`
- `clients/eskiz.py`: Eskiz API-клиент с auth, retry, батч
- Frontend: 3 экрана

### Этап 8 — Celery background jobs (2 дня)

- `release_expired_bookings` (каждую минуту): находит `Apartment.booking_expires_at < now`, меняет статус на свободно, отменяет договор, шлёт уведомление менеджеру
- `send_overdue_payment_sms` (ежедневно 09:00 Tashkent)
- `run_auto_sms_rules` (ежечасно)

### Этап 9 — Legacy data migration (3-4 дня)

Standalone скрипт `scripts/migrate_legacy.py` с dry-run. Порядок миграции:

1. Developer (из `rc_objects_builtby` + knowledge_base_requisite)
2. Project (из `rc_objects_rcobject`)
3. Building (из `apartments_apartment` — переименование!)
4. Section (из `apartments_section`)
5. Floor (из `apartments_stage` — переименование!)
6. Apartment (из `flats_flat` — переименование!)
7. PriceHistory (из `apartments_stagehistory`)
8. ApartmentStatusLog (из `flats_flatstatushistory`)
9. DiscountRule (из `rc_objects_discountpercent`)
10. DiscountRuleHistory (из `rc_objects_discountpercenthistory`)
11. Calculation (из `flats_calculation`, 159K строк — батчами)
12. Client (из `clients_client`)
13. ClientContact (из `clients_employee`)
14. Requisite (из `clients_requisite`)
15. ContractTemplate (из `knowledge_base_templatefile`)
16. Contract (из `clients_contract`)
17. PaymentSchedule (из `clients_installmentplan`)
18. Payment (из частей `finance_transaction`)
19. FinanceRecord (из `finance_transaction`)
20. SmsTemplate (из `mailing_template`)
21. AuditLog (из `users_useractionhistory`, 357K строк — батчами)

**Skip**: task_manager_*, sales_bpm_*, bot_site_*, knowledge_base_news/post/category/subcategory, clients_contractmortgage (только `is_mortgage` флаг).

Файлы `media/discountpercenthistory/*/` → `MEDIA_ROOT/discount_history/` с обновлением путей в `DiscountRuleHistory.document`.

### Этап 10 — Reports + Polish (TBD)

## Как продолжать работу

1. **Прочитай этот файл** + `docs/architecture.md` + `CLAUDE.md`.
2. **Проверь что стек поднят**: `docker compose ps` — должны быть все 8 контейнеров.
3. **Если Docker упал**: сначала запусти Docker Desktop, потом `docker compose up -d`. На Windows плагин compose находится в `C:\Program Files\Docker\Docker\resources\cli-plugins\docker-compose.exe`; если `docker compose` не работает — скопируй `.exe` в `~/.docker/cli-plugins/`.
4. **Логин в dev-админку**: http://localhost:5173/login — `admin@rcrm.local` / `admin12345`.
5. **Следующий этап — Этап 2 (References)**. Начинай с моделей в `backend/apps/references/models.py`.

## Полезные команды

```bash
# Run tests
docker compose exec backend pytest

# Make / apply migrations
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Django shell
docker compose exec backend python manage.py shell

# Connect to legacy DB
docker exec -it rcrm_postgres_legacy psql -U zk_user -d zk_legacy

# Dump current schema report
docker exec -e LEGACY_POSTGRES_HOST=host.docker.internal \
  -e LEGACY_POSTGRES_PORT=5433 \
  -e LEGACY_POSTGRES_DB=zk_legacy \
  -e LEGACY_POSTGRES_USER=zk_user \
  -e LEGACY_POSTGRES_PASSWORD=rawa0040 \
  rcrm_backend python /tmp/legacy_inspect.py --output /app/legacy_schema.md

# Typecheck frontend
docker compose exec frontend npx vue-tsc --noEmit

# Lint
docker compose exec backend ruff check .
docker compose exec frontend npm run lint
```

## Технический долг (накоплено в Этапе 1)

- Модалки в admin-экранах — простые HTML inputs, не PrimeVue. Перепишу на PrimeVue Dialog + InputText + Select в Этапе 2 при первом реальном CRUD-экране справочника.
- `HasPermission("key")` использует паттерн instance+`__call__` возвращает self — необычно, но работает с DRF. Можно отрефакторить в factory `has_permission(key)` возвращающий class, когда будет время.
- Нет фикстур для начального seeding ролей — сейчас Role создаётся через API. Нужна management command `seed_default_roles` с базовыми ролями (admin, sales-manager, collector) в Этапе 2.
