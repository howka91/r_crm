# CLAUDE.md — конвенции r_crm

## <a name="naming"></a>Именование (glossary)

Новые имена моделей — чистые, без путаницы старого кода.

| Рус | Новое имя (код) | Старое имя (legacy) |
|---|---|---|
| Застройщик | `Developer` | `Requisite` (частично), `BuiltBy` |
| Жилой комплекс (ЖК) | `Project` | `RCObject` |
| Корпус / блок | `Building` | `Apartment` (!) |
| Подъезд | `Section` | `Section` |
| Этаж | `Floor` | `Stage` |
| Квартира | `Apartment` (!) | `Flat` |
| Правило скидок | `DiscountRule` | `DiscountPercent` |
| Расчёт для квартиры | `Calculation` | `Calculation` |
| Сотрудник CRM | `Staff` | `User` |
| Клиент | `Client` | `Client` |
| Контакт/представитель клиента | `ClientContact` | `Employee` |
| Банковские реквизиты клиента | `Requisite` | `Requisite` |
| Договор | `Contract` | `Contract` |
| Шаблон договора | `ContractTemplate` | `Template` |
| График платежей | `PaymentSchedule` | `InstallmentPlan` |
| Платёж | `Payment` | `Transaction` (частично) |
| Финансовая операция | `FinanceRecord` | `Transaction` |
| SMS шаблон | `SmsTemplate` | `Template` (в mailing) |
| Авторассылка | `AutoSms` | `AutoSend` |
| Лог статусов квартиры | `ApartmentStatusLog` | `FlatStatusHistory` |
| История цен этажа | `PriceHistory` | `StageHistory` |
| Лог действий | `AuditLog` | `UserActionHistory` |

**Внимание**: в старом коде `Apartment = корпус`, `Flat = квартира`. В новом коде `Apartment = квартира`, `Building = корпус`. Мигратор обязан делать соответствующий mapping.

## Django apps

Ровно 9 apps:

- `core` — `BaseModel`, `I18nField`, `MoneyField`, `AuditLog`, middleware, utilities
- `users` — `Staff`, `Role`, `PermissionTree` (hardcoded), JWT
- `references` — `Developer`, `SalesOffice`, `Currency`, справочники
- `objects` — `Project → Building → Section → Floor → Apartment` + `DiscountRule` + `Calculation` + `PaymentPlan` + `PriceHistory` + `ApartmentStatusLog`
- `clients` — `Client`, `ClientContact`, `Requisite`
- `contracts` — `Contract`, `ContractTemplate`, `PaymentSchedule`, `Payment`
- `finance` — `FinanceRecord`, ПКО-генерация
- `notifications` — `SmsTemplate`, `ManualSms`, `AutoSms`, `NotificationLog`, Eskiz-клиент
- `reports` — плейсхолдер, определяется позже

## Конвенции кода

### Backend (Django)

- **Деньги** — всегда `DecimalField(max_digits=14, decimal_places=2)` через `core.fields.MoneyField`. Никогда не `FloatField`.
- **Площадь** — `DecimalField(max_digits=8, decimal_places=2)`.
- **Мультиязычные поля** — `core.fields.I18nField` (subclass `JSONField`), формат `{"ru": "...", "uz": "...", "oz": "..."}`.
- **PK** — `BigAutoField` по умолчанию, `UUIDField` только для `Staff` (по архитектуре).
- **Бизнес-логика** — в `services/*.py` каждого app, не в моделях и не в сигналах. Сигналы — только для логирования и инвалидации кэша.
- **Транзакции** — явно через `transaction.atomic()` в сервисах, которые меняют несколько таблиц.
- **Конкурентность (бронирование)** — `select_for_update()` на `Apartment` внутри `transaction.atomic()`.
- **Soft delete** — через `is_active=False` + `SoftDeleteManager` из `core.managers`.
- **Timezone** — `Asia/Tashkent`, все `DateTimeField` работают в TZ-aware режиме (`USE_TZ=True`).
- **API** — DRF ViewSet + router. Сериализаторы в `{app}/serializers.py`, views в `{app}/views.py`, filters в `{app}/filters.py`.
- **Permissions** — DRF permission class `HasPermission("module.key")` проверяет `Staff.role.permissions` dict.
- **Тесты** — pytest-django, фабрики через factory-boy, file per model `tests/test_<entity>.py`.
- **Импорты** — абсолютные от корня (`from apps.users.models import Staff`), не `from .models`.
- **Layout моделей** — по умолчанию `{app}/models.py` один файл. Когда моделей в app ≥ 4 — переходим на **пакет** `{app}/models/` c одним файлом на модель (`developer.py`, `sales_office.py`, ...) + `__init__.py`, который re-export'ит всё для обратной совместимости (`from apps.X.models import Y` должно работать). Родственные мелкие таблицы (LookupModel-потомки) кладём в один общий `models/lookups.py`, а не плодим по файлу на каждую. **Эталон**: `apps/references/models/` — `developer.py`, `sales_office.py`, `currency.py`, `lookups.py`.
- **Factories для одинаковых ViewSet'ов**. Если регистрируем 5+ почти идентичных CRUD-эндпоинтов (13 lookup'ов, серия отчётов и т.п.) — не копипастим ViewSet, а делаем фабрику `make_X_viewset(model)` и регистрируем циклом в `urls.py`. Эталон: `apps/references/{serializers,views}.py#make_lookup_*`.

### Frontend (Vue 3)

- **Стор** — Pinia, один store per domain (`useAuthStore`, `useClientsStore`). Setup syntax.
- **TypeScript** — strict mode включён, типы моделей в `src/types/` (генерируются из OpenAPI schema через `openapi-typescript`).
- **Компоненты** — Composition API + `<script setup>`. Стили — Tailwind utility classes + PrimeVue slots.
- **i18n** — vue-i18n@9, ключи в `src/locales/{ru,uz,oz}.json`. Использовать `t()` вместо хардкода строк.
- **Роутинг** — Vue Router 4, каждый route имеет `meta.permission: "module.key"`. Guard проверяет через CASL.
- **Формы** — vee-validate@4 + Yup. Все поля через PrimeVue компоненты.
- **API** — axios-клиент в `src/api/client.ts` с interceptors (JWT refresh, error toast).
- **Именование** — `PascalCase` для компонентов, `camelCase` для переменных/функций, `kebab-case` для route paths.

## Workflow Contract.action

```
request  → wait  → approve  → sign_in
           ↓
           edit  (запрос на редактирование → обратно в wait)
```

Все переходы — через `contracts.services.transition_contract()`, без прямого `contract.action = ...`.

## Каскад пересчёта цен

```
Floor.price_per_sqm меняется
  → recalc_floor(floor) в objects.services.pricing
    → для каждого Apartment пересчитать total_price
    → для каждого Calculation пересчитать (с учётом DiscountRule)
```

Вызывается **явно** из ViewSet / management command / миграции. **Не через сигналы.**

## PDF generation

- Шаблоны договоров: HTML в `ContractTemplate.body` (Tiptap-редактор на фронте) с плейсхолдерами `{{key}}`. `ContractTemplate.placeholders` хранит admin-декларируемый список `[{key, path, label}]` — `key` это то, что пишут в шаблоне, `path` — дотточный путь резолвинга в контексте контракта (например `client.full_name`, `apartment.number`).
- Конвертация HTML → PDF: **WeasyPrint** (в том же backend-контейнере, отдельного сервиса нет).
- ПКО: `reportlab` с встроенным шрифтом `DejaVuSans` (поддержка кириллицы + узбекской латиницы).
- QR: `qrcode` lib, PNG как base64 data-URI встраивается в HTML перед рендером.

## i18n на бэке

- Мультиязычные поля хранятся как JSON `{ru, uz, oz}`.
- API отдаёт **полный объект** (не фильтрует по `Accept-Language`). Фронт сам выбирает язык.
- Ошибки/сообщения — через `django.utils.translation.gettext_lazy` (обычный Django i18n).

## Git

- Commit messages на английском, imperative: `Add Apartment model`, `Fix pricing cascade on Floor update`.
- Один PR = одна фаза (или её логическая часть).
- Без co-author меток.

## Что НЕ делаем

- Не используем сигналы для бизнес-логики (только логирование).
- Не создаём модели без `created_at` / `modified_at` (наследуем `BaseModel`).
- Не делаем каскадные `on_delete=CASCADE` без обоснования — по умолчанию `PROTECT` или `SET_NULL`.
- Не пишем бизнес-логику в сериализаторах — только валидация форматов.
- Не используем `FloatField` для денег/площадей.
- Не хардкодим строки UI — всё через `t()` / `gettext`.
- Не создаём `.md` документы без запроса пользователя, кроме `README.md`, `CLAUDE.md` и `docs/` по плану.

## RTK (Rust Token Killer)

Пользовательская конвенция — всегда префиксить команды `rtk` (см. `~/.claude/CLAUDE.md`):
```bash
rtk git status
rtk docker compose logs backend
rtk pytest
```
Даже в цепочках через `&&`.
