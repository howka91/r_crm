# Session state — где остановились и что дальше

> Обновляется в конце каждой рабочей сессии. Следующий Claude (или я сам после паузы) должен прочитать этот файл **первым**, чтобы продолжить работу без повторного проектирования.

## Последняя сессия — 23 апреля 2026 (вечер)

### Что сделано

**Этап 5.2 — Contracts сервис-слой (transitions / numbering / schedule) + workflow API.**

Плюс до этого в тот же день закрыл **5.1** (модели и базовый CRUD), поменял авторизацию с email на login-поле, и открыл стек для локальной сети (Vite-прокси `/api → backend`, `DJANGO_ALLOWED_HOSTS=*`).

#### 5.2 — детали

**Префикс номера договора**: `Project.contract_number_prefix = CharField(blank, default="")`. Миграция `objects/0004_project_contract_number_prefix.py`. Пример: `prefix="ЯМ"` → номер `ЯМ-00001`. Пустой префикс — просто `00001`.

**Permission tree** расширен тремя ключами под `contracts.unsigned`:
- `contracts.unsigned.sign` — финальное подписание (approve → sign_in)
- `contracts.unsigned.request_edit` — возврат wait → edit
- `contracts.unsigned.generate_schedule` — пересборка графика из Calculation

**`apps/contracts/services/numbering.py`** — `mint_contract_number(project) → str`. Атомарный инкремент счётчика через `transaction.atomic() + select_for_update()` на Project — гонки между одновременными вызовами сериализуются на уровне row-lock. Format: `{prefix}-{index:05d}` (или `{index:05d}` при пустом префиксе).

**`apps/contracts/services/transitions.py`** — стейт-машина `Contract.action`:
- Таблица `_ALLOWED: dict[action, set[action]]` — единственный источник правды.
- 4 функции: `send_to_wait`, `approve`, `sign`, `request_edit(reason)`.
- Все атомарны (`transaction.atomic() + select_for_update()` на контракт).
- `send_to_wait` **минтит contract_number при первом вызове** — вход в workflow создаёт номер. Resubmit из `edit` номер не меняет.
- `sign` терминальный: flip `is_signed=True`, переходы дальше недоступны.
- `request_edit` снапшотит текущий `document` в `old[]` с метаданными (`snapshot_at`, `actor_id`, `reason`). Каждый новый edit-цикл append'ит запись.
- `TransitionError(current, target)` — 409 в API с `current_action` в payload.
- AuditLog полагается на middleware-level request-logging; domain-level «память» — в `old` и `action` сам по себе.

**`apps/contracts/services/schedule.py`** — `generate_schedule(contract) → list[PaymentSchedule]`:
- Строка #1 — `initial_fee` на `contract.date` (пропускается при 0).
- Строки #2..N — `monthly_payment` × `installment_months`, шаг `+1 calendar month` через `dateutil.relativedelta` (корректная обработка конца месяца: Jan 31 → Feb 28 / Feb 29).
- Регенерация **деструктивная** — предыдущие строки удаляются через `all_objects.delete()` (реальное удаление, не soft-delete), что каскадно сносит привязанные `Payment`'ы. Защита от этого — на уровне API (см. ниже).
- Бросает `ScheduleBuildError` если контракт без calculation.

**Custom actions на `ContractViewSet`**:
```
POST /contracts/:id/send-to-wait/        → contracts.unsigned.send_to_wait
POST /contracts/:id/approve/             → contracts.unsigned.approve
POST /contracts/:id/sign/                → contracts.unsigned.sign
POST /contracts/:id/request-edit/        → contracts.unsigned.request_edit
POST /contracts/:id/generate-schedule/   → contracts.unsigned.generate_schedule
```

- Illegal transitions возвращают **409** с `{"detail": ..., "current_action": ...}`.
- Ответ содержит полный сериализованный контракт после транзишена; при первом `send-to-wait` в payload добавлен `__minted_contract_number`.
- `/generate-schedule/` блокирован на `is_signed=True` контракте (409) — чтобы не оставлять Payment'ы сиротами после подписания.

**Тесты**: +31 → всего 59 в `apps/contracts/tests/`, **268/268 backend** (было 237).
- `test_numbering.py` (6): счёт с нуля, последовательные минты, разные проекты, пустой префикс, сохранение остальных полей Project, старт с уже ненулевого индекса.
- `test_transitions.py` (9): все легальные переходы, illegal, re-submit не меняет номер, append в `old`.
- `test_schedule.py` (6): initial + monthly, без calculation, без initial_fee, регенерация (удаляет старое), нулевые installment_months, end-of-month rollover.
- `test_workflow_api.py` (10): e2e через DRF-клиент по каждому endpoint'у, 409 на illegal transitions, scoped permission, блокировка generate-schedule на подписанном договоре.

### Что дальше — Этап 5.3

- **`apps/contracts/services/docgen.py`** — рендер договора:
  - `python-docx` открывает `ContractTemplate.file`, подставляет плейсхолдеры из `ContractTemplate.placeholders` + snapshot `document`.
  - Конвертация в PDF через HTTP-запрос к контейнеру `rcrm_libreoffice` (порт 2002) — у нас уже стоит в compose.
  - `qrcode` генерит PNG для `Contract.qr`, встраивается в PDF.
  - Snapshot-мёрдж: на вызове docgen заполняем `Contract.document` актуальными значениями (имя клиента/квартира/цена/реквизиты продавца) — с этого момента редактирование базовых сущностей не меняет уже выпущенный PDF.
  - Endpoint `POST /contracts/:id/generate-pdf/` с permission `contracts.unsigned.edit` (или новым `generate_pdf`).

### Что дальше — Этап 5.4 (Frontend)

3 экрана + wizard — начинаем после 5.3. Детали в плане ниже.

---

### Что сделано в тот же день раньше (для справки)

**Этап 5.1 — Contracts backend модели + базовый CRUD.**

Перед моделями пересверил легаси-схему (`clients_contract`, `clients_installmentplan`, `finance_transaction`, `clients_contract_payment_method`, `knowledge_base_templatefile`) и синхронизировал план в этом файле — см. «Поправки к Этапу 5, сессия 23 апреля» ниже.

#### Модели (`backend/apps/contracts/models/`)

Пакет из 4 моделей, все с `BaseModel` (soft-delete + timestamps):

- **`Contract`** — главная сущность продажи.
  - Связи: `project` (PROTECT), `apartment` (PROTECT), `calculation` (SET_NULL), `signer → ClientContact` (PROTECT, **not null**) — клиент всегда достаётся через `signer.client`, прямого FK на Client нет, повторяет легаси. `author → Staff` (SET_NULL).
  - Данные: `contract_number` (CharField, blank=True, default=""), `date`, `send_date`, `related_person` (свободный текст для нестандартного подписанта), `description`.
  - Деньги — snapshot на момент подписания: `total_amount`, `down_payment` (MoneyField).
  - `payment_methods` — M2M на `references.PaymentMethod` (контракт может комбинировать несколько каналов — в легаси 1144 связи на 3023 контракта).
  - Workflow-поля: `action` (enum request/wait/edit/approve/sign_in, **read-only в 5.1**), `is_signed`, `is_paid`, `is_mortgage`. Транзишены живут в сервисах (5.2), через прямой PATCH `action` изменить нельзя.
  - Snapshot'ы: `requisite` (реквизиты продавца на момент подписания), `document` (заполненные плейсхолдеры), `old` (список предыдущих версий document при цикле `edit → wait`).
  - Файлы: `file` (FileField, PDF), `qr` (ImageField).
  - Индексы: партиальный `UniqueConstraint(project, contract_number)` с `condition=~Q(contract_number="")` — черновики без номера не конфликтуют, выпущенные номера уникальны в рамках ЖК.
- **`ContractTemplate`** — `.docx`-шаблон + `placeholders = JSONField(default=list)` формата `[{model, field, field_name, description}]`. Легаси-таблица `clients_contracttemplatefield` (39 строк) схлопнута в JSON (объём мизерный).
- **`PaymentSchedule`** — пункт графика (FK Contract CASCADE): `due_date`, `amount`, `paid_amount`, `status` (pending/partial/paid/overdue). `debt` — вычисляемое `@property` (`max(0, amount - paid_amount)`).
- **`Payment`** — факт платежа (FK PaymentSchedule CASCADE): `amount`, `payment_type` (cash/bank/barter — **канал** оплаты, живёт на Payment, не на Contract), `paid_at`, `recorded_by → Staff` (SET_NULL), `receipt_number`, `comment`.

Миграция `contracts/0001_initial.py`.

#### Сервис-слой и API (пока базовый)

- 4 `ModelViewSet`'а: `ContractViewSet`, `ContractTemplateViewSet`, `PaymentScheduleViewSet`, `PaymentViewSet`. URL'ы: `/api/v1/{contracts,contract-templates,payment-schedules,payments}/`.
- **Permission bindings** (временные до 5.2):
  - `ContractViewSet` → `contracts.unsigned.*`
  - `ContractTemplateViewSet` → `references.templates.*`
  - `PaymentScheduleViewSet` + `PaymentViewSet` → `contracts.unsigned.*` (временно; `PaymentViewSet` переедет на `finance.*` в Фазе 6 — там нужна CRUD-подветка; сейчас в дереве только `finance.view/create_income/create_refund/export/import/charts`, без `_ACTION_SUFFIX`-совместимого шейпа).
- **В сериализаторе `Meta.validators = []`** — отключил авто-`UniqueTogetherValidator` для `(project, contract_number)`, потому что он форсит `required=True` на оба поля даже при `required=False`/`default=""`, ломая создание черновиков. Уникальность держит партиальный DB-индекс + будущий сервис номерации (5.2) через `select_for_update` на `Project.contract_number_index`.
- `action`, `is_signed`, `is_paid` помечены `read_only_fields` в сериализаторе — нельзя поменять через обычный PATCH. Транзишены подключатся в 5.2 как custom actions (`/contracts/:id/send-to-wait/` и т.д.).
- **Soft-валидация в `validate()`**: `down_payment <= total_amount`; `apartment.floor.section.building.project == contract.project` — нельзя прикрепить квартиру из чужого ЖК.
- Денормализация в `ContractSerializer`: `project_title`, `apartment_number`, `signer_name`, `client_id`, `client_name`, `author_name` — listing не делает N+1.

#### Тесты (`apps/contracts/tests/`)

28 новых тестов, итого **236/236 зелёные** (было 208).

Важный факт про фабрику: `ContractFactory` генерирует apartment внутри `project` (иначе валидация «квартира другого ЖК» режет). Использован `factory.LazyAttribute` вместо `SelfAttribute("..project")` — последнее не резолвится через вложенный SubFactory.

### Поправки к Этапу 5, сессия 23 апреля (после сверки с легаси)

1. **Client достаётся через signer**, не напрямую. `Contract.signer → ClientContact` (PROTECT, not null); `Client = signer.client`. Это сохраняет легаси-семантику `clients_contract.customer_id → clients_employee.company_id → clients_client.id`. Для физлиц без явного контакта миграция создаст синтетический `ClientContact(is_chief=True)` с ФИО клиента.
2. **`Contract.payment_methods` — M2M на `PaymentMethod`**, не `CharField`. Легаси `clients_contract_payment_method` = 1144 связи на 3023 контракта.
3. **`Contract.project` FK** хранится явно (а не через `apartment.floor.section.building.project`) — иначе на каждый листинг договоров ЖК — 4 JOIN. Уникальность `contract_number` — в рамках проекта, не глобально.
4. **`payment_type` перенесён с Contract на Payment** — это *канал* конкретной операции (куда ушли деньги), не свойство договора. На Contract'е остаётся только M2M `payment_methods` (план оплаты).
5. **`Contract.is_actual` из легаси дропнут** — дубликат `is_active`.
6. **`finance_transaction` (5841 строк)** в 5.1 трогать нет смысла: единая таблица в легаси разделяется на `Payment` (привязка к графику) и `FinanceRecord` (касса, Фаза 6). Мигратор из одной строки создаст обе записи.
7. **`clients_contracttemplatefield`** (39 строк) не мигрируется как отдельная таблица — placeholder'ы лежат в JSONField'е `ContractTemplate.placeholders` прямо на шаблоне.
8. **`clients_contractmortgage`** не мигрируется — только флаг `Contract.is_mortgage`.

### Что дальше — Этап 5.2 (сервис-слой)

- **`apps/contracts/services/transitions.py`** — стейт-машина `action`:
  - `request → wait` (send to wait) — `contracts.unsigned.send_to_wait`
  - `wait → approve` — `contracts.unsigned.approve`
  - `approve → sign_in` + `is_signed=True` — отдельное разрешение
  - `wait → edit` (клиент запросил правки) → обратно в `wait` после правок
  - Каждая транзиция пишет в `AuditLog` и сохраняет предыдущий `document` в `old` (список).
- **`apps/contracts/services/numbering.py`** — генерация номера:
  - `transaction.atomic()` + `select_for_update()` на `Project`
  - `contract_number_index += 1`
  - формат `{project.prefix}-{index:05d}` (префикс пока захардкодим, позже вынесем в `Project.contract_number_prefix`).
  - Номер присваивается **на транзишене** `request → wait`, не при создании. До этого номер пустой (черновик).
- **`apps/contracts/services/schedule.py`** — авто-построение графика:
  - По `Calculation` (`installment_months`, `monthly_payment`, `initial_fee`) создать `PaymentSchedule`-строки.
  - Первая строка — `down_payment`, срок = `date`.
  - Остальные — равные, по `monthly_payment`, с шагом ~30 дней (или точный месячный в `date`).
- **Custom actions** на `ContractViewSet`: `POST /contracts/:id/send-to-wait/`, `/approve/`, `/sign/`, `/request-edit/`, `/generate-schedule/`.

### Этап 5.3 — docgen (после 5.2)

- `apps/contracts/services/docgen.py`: `python-docx` → `libreoffice --headless` (контейнер `rcrm_libreoffice`) → PDF.
- `apps/contracts/services/qr.py`: `qrcode` lib → PNG → `Contract.qr`.
- Хранение snapshot'а в `Contract.document` при вызове docgen.

### Этап 5.4 — Frontend

3 экрана (`Неподписанные`, `Подписанные`, `Запросы на редактирование`) + wizard создания договора + карточка договора с табами (график / платежи / файлы).

## Предыдущая сессия — 22 апреля 2026 (вечер)

### Что сделано за день

Закрыты **Этапы 2, 3 и 4**. Теперь работающий продукт покрывает: авторизацию, справочники, учёт объектов со всей ценовой механикой и шахматкой, клиентскую базу с контактами и реквизитами.

#### Этап 2 — References (`aa0e64d`, `807b9a5`)

- Backend: `Developer`, `SalesOffice`, `Currency` + 13 lookup-моделей (`ApartmentType`, `RoomType`, `ConstructionStage`, `Decoration`, `PremisesDecoration`, `HomeMaterial`, `OutputWindows`, `OccupiedBy`, `Badge`+color, `PaymentMethod`, `PaymentInPercent`+percent, `Region`, `Location`+FK Region).
- Фабрика `make_lookup_viewset/serializer` в `apps/references/` — 13 CRUD-эндпоинтов регистрируются циклом по `LOOKUP_MODELS`.
- Модели в **package `models/`** по правилу «≥4 моделей». Lookup'ы — в одном файле `lookups.py`.
- Frontend: `/references` hub + 4 экрана (developers / sales-offices / currencies + универсальный lookups screen с query-param `?type=slug`).
- 55 тестов, включая 3×13 parametrized lookup smoke + 5 extras (Badge.color, Location.region FK, PaymentInPercent.percent, Currency normalization).

#### Этап 3 — Objects (10 моделей, 5 коммитов `b163477` → `5e40945`)

**Backend, иерархия 6 уровней**: `Project → Building → Section → Floor → Apartment` + `ApartmentStatusLog`, `PaymentPlan`, `DiscountRule`, `Calculation`, `PriceHistory`.

Ключевые инженерные решения:

- **PROTECT по умолчанию** на все FK между уровнями. Каскадное удаление — только через явный `?force=true` на `SectionViewSet.destroy` / `FloorViewSet.destroy`, использующий `all_objects` (обычный manager) вместо `SoftDeleteManager`, чтобы реально удалять строки, а не ставить `is_active=False`. См. `apps/objects/views.py#destroy`.
- **`apps/core/mixins.py#ProtectedDestroyMixin`** — перехватывает `ProtectedError` и отдаёт 409 с `blocked_by: {model: count}` вместо 500.
- **Сервисы**:
  - `services/apartments.change_status` — единственный вход для перехода статуса, `select_for_update` + запись `ApartmentStatusLog`. Легальные переходы в `_ALLOWED_TRANSITIONS`. `_NON_BOOKING_STATUSES` автоматически сбрасывает `booking_expires_at`.
  - `services/booking.py` — `book_apartment` / `release_booking` с `select_for_update`, инлайновым логом (не зовёт `change_status`, чтобы не было вложенных транзакций).
  - `services/pricing.py` — `find_applicable_discount` → `recalc_apartment` → `recalc_floor` → `recalc_project`; `change_floor_price` атомарно пишет `PriceHistory`, обновляет `Floor.price_per_sqm` и каскадом вызывает recalc. **Всё явными функциями, сигналов нет** (CLAUDE.md).
  - `services/section_duplication.duplicate_section(source, target_building)` — клонирует Section + Floors + Apartments в одну транзакцию. Планировочные файлы и Calculation не копируются (производные). Бронь сбрасывается. Номер секции авто-бампится до `max+1` при коллизии.
- **Custom actions**: `POST /apartments/:id/change-status|book|release|recalc/`, `POST /floors/:id/change-price/`, `POST /sections/:id/duplicate/`. Каждый с отдельной строкой в `action_perms`.
- **Permission tree расширен**: `objects.sections.*`, `objects.payment_plans.*`, `objects.calculations.*`, `objects.discounts.*` полный CRUD (было только view/edit).

**Frontend**: 4 экрана под `/objects`:

- `/objects` — grid ЖК-карточек.
- `/objects/projects/:id` — **Структура**: раскрывающееся дерево Корпус→Подъезд→Этаж→Квартира. На этаже — кнопка «Сменить цену» с модалкой (preview каскада + PriceHistory). На квартире — «Бронировать / Снять бронь / Сменить статус». Единый модал с `kind` dispatch (building/section/floor/apartment/status/book/price/duplicate_section).
- `/objects/projects/:id/pricing` — **Прайсинг**: CRUD `PaymentPlan` + `DiscountRule`.
- `/objects/projects/:id/shaxmatka` — **Шахматка**: визуальный grid этажей × квартир с цветовой легендой статусов, фильтром по комнатам, side-drawer на клик по квартире (инфо + Calculations + StatusLog + кнопки book/release/recalc).

**175 тестов на Objects** (173 при закрытии 3.5, +9 на section duplication, +6 на force delete → 188, +20 на Clients → итого 208 в конце дня).

#### Replace `alert()` / `confirm()` на in-app (`74446de`, `d37e94d`)

PrimeVue `Toast` и `ConfirmDialog` у нас в `unstyled` режиме с пустым preset — поэтому рендерились без стилей. Заменены на **собственные**:

- `src/store/toast.ts` + `src/components/ToastContainer.vue` — floating stack top-right, severity stripe, auto-dismiss.
- `src/store/confirm.ts` + `src/components/ConfirmDialog.vue` — Promise-based `ask({title, message, severity, okLabel})` → `Promise<boolean>`. Esc/Enter handled, body scroll locked.
- Оба смонтированы в `App.vue`.
- **Во всём `src/` не осталось ни одного `alert()` / `confirm()`** — все заменены на toast.error / await confirmStore.ask. Единственный оставшийся `prompt()` — в `detail.vue#doRelease` (ввод комментария при снятии брони).

#### Этап 4 — Clients (`cd3ff1d`)

5 моделей: `ClientStatus` (+color), `ClientGroup`, `Client` (entity phys/jur, `phones: ArrayField(CharField)`, `emails: ArrayField(EmailField)`, inn/oked/pin, birth_date, FK manager (Staff), FK status, M2M groups), `ClientContact` (FK Client с CASCADE, `passport: JSONField`, phones[], is_chief), `Requisite` (FK Client CASCADE, type internal/local, `bank_requisite: JSONField`).

- Serializer денормализует `manager_name` / `status_name` / `contacts_count` / `requisites_count` для избежания N+1 на листинге.
- Soft-валидация: `gender` запрещён для `entity='jur'`, `full_name` обязательно.
- Permission tree: `clients.*` CRUD + `clients.{contacts,requisites,statuses,groups}.*` — роли можно ограничивать поштучно.
- 20 тестов.

**Frontend**:

- `/clients` — таблица с chip-фильтрами (Все/Физ/Юр), select статусов и менеджеров, debounced search по full_name/inn/pin. Создание — **минимальный** модал (entity + name + pin/inn + phones), после успеха → редирект на detail.
- `/clients/:id` — header с chip-статусом (фон = `ClientStatus.color`), менеджер, телефон, email, group-теги. Tab-strip на 4 вкладки:
  - **Контакты** — таблица + модал с секцией «Паспорт» (series/number/issued_by/issued_date/registration_address).
  - **Реквизиты** — таблица с chip-типом + модал (bank/account/mfo/currency).
  - **Заметки** — textarea → PATCH `Client.description`.
  - **Договоры** — stub до Этапа 5.

### Состояние на конец дня

- **Backend: 208/208 тестов зелёные**.
- **Frontend: vue-tsc 0 ошибок**, `npm run build` OK (~12 chunks).
- **Docker-стек** поднят (7 контейнеров: backend, beat, frontend, libreoffice, postgres, redis, worker; `rcrm_postgres_legacy` — отдельный, для миграции).
- **HEAD**: `cd3ff1d` on `origin/main`.

### Технический долг, накопленный за день

- **`seed_default_roles`** management command с базовыми ролями (admin, sales-manager, collector) — нужен был ещё с Этапа 1, сейчас обход через superuser + ручное создание ролей в UI.
- **Planning файлы** для `Building`, `Section`, `Apartment` объявлены как FileField, но в UI не загружаются. Дублирование секции обнуляет эти поля намеренно.
- **Photo upload для `SalesOffice`** — поле есть, upload-хелпера нет.
- **Leaflet-карта** для `SalesOffice` — вообще не реализована (лат/лон есть, но карты нет).
- **`Apartment.recalc` action** гейтится `objects.apartments.edit`, что смешивает «редактировать данные» и «пересчитать прайсинг». Если появится роль, которой можно только пересчитывать — выделить отдельный permission.
- **N+1 на фронте Objects**: `detail.vue` / `shaxmatka.vue` грузят все apartments / sections / floors одним большим запросом. Работает до ~5k квартир на ЖК. Для реального объёма (8k+ в легаси) перейти на lazy load per section.
- **Шахматка — только один срез (building × section)**. Legacy имел кнопку «вся шахматка ЖК» — не реализовано.
- `shaxmatka.vue` делает 4 parallel запроса (buildings/sections/floors/apartments/pp) на mount — при 8k+ apartments нужен pagination или backend endpoint `GET /projects/:id/shaxmatka-data/` с одним payload'ом.
- **Контракты-таб на карточке клиента** — заглушка. Заполнится в Этапе 5.

## Предыдущая сессия — 22 апреля 2026

### Что сделано

**Визуальный рестайл фронта + структурная миграция под Vuexy-layout.** Бэк не трогали — все Этапы 0/1 остались в том виде, в каком были после 21 апреля.

#### Дизайн-система «Smart RC · Yangi Mahalla»

Source of truth: `frontend/design_handoff_smart_rc_extracted/design_handoff_smart_rc/README.md` (распакован из `frontend/YangiMahalla.zip`). Hi-fidelity: токены в oklch, Inter Tight + JetBrains Mono, 8-px grid. Тёмно-зелёный `oklch(0.38 0.10 155)` + лаймовый акцент `oklch(0.72 0.18 130)` из логотипа.

**Реализовано:**

- `src/assets/styles/main.css` — все токены в CSS-переменных (`--primary`, `--primary-soft`, `--primary-accent`, `--success/warning/danger/info` + soft-варианты, `--surface/sunken/line/line-soft/text/muted/subtle`, тени). Компонентные классы: `.btn/.btn-primary/.btn-ghost/.btn-soft/.btn-danger/.btn-sm/.btn-xs/.btn-icon`, `.inp/.inp-sm`, `.card/.card-hover`, `.chip/.chip-success/.chip-warn/.chip-danger/.chip-info/.chip-primary/.chip-ghost`, `.tbl`, `.nav-item/.nav-item.is-active/.nav-header`, `.mono`, `.art-scroll`. Все через `@apply` поверх Tailwind.
- `tailwind.config.ts` — `ym.*` палитра (мапится на CSS-переменные), `shadow-ym-{primary,primary-lg,nav-active,card,float,modal}`, `bg-ym-nav-active` (градиент активного пункта меню), `bg-ym-login-brand` + `bg-ym-login-glow` (градиенты брендовой панели Login), `tracking-tightest`, `ringColor.ym-primary`.
- `index.html` — подключены Google Fonts Inter Tight + JetBrains Mono с preconnect.

#### Рестайл экранов

- **Sidebar** (`src/layouts/components/Sidebar.vue`): 252 px, белый, лого «YM» на `--primary` с лаймовым акцентом, группы из `@/navigation/vertical`, активный пункт через `.is-active` (градиент + 3 px лаймовая полоска слева + shadow), user-card снизу с инициалами.
- **Navbar** (`src/layouts/components/Navbar.vue`): floating (margin 24, radius 14, shadow-float), крошки по имени роута, поиск с `⌘K`, колокольчик, циклический переключатель локали RU/UZ/OZ.
- **Login** (`src/views/Login.vue`): split-экран 2/3 + 1/3. Левая панель (скрыта <lg): brand-градиент, два радиальных glow'а, ghost-шахматка 12×8 под −10° opacity-30, лого на лаймовой плашке, eyebrow + двустрочный H1 + описание, копирайт + версия. Правая форма: eyebrow, H1 «С возвращением», email + password с eye-toggle, remember-me, CTA «Войти →», chip-кнопки смены языка.
- **Dashboard** (`src/views/Home.vue`): eyebrow + H1 проекта + подпись, 4 stat-карточки (Свободно/Бронь/Продано/Выручка) с soft-tinted icon-плашками, 2/3 bar-chart «Динамика договоров» за 6 месяцев (primary-градиент + primary-soft), 1/3 список «Недавние договоры» с аватарами, mono-ID и chip-статусами.
- Админ-экраны `views/modules/Administration/userManagement/{index,roles,roleView}.vue` и `components/PermissionTreeEditor.vue` — переведены на `.btn/.card/.tbl/.chip/.inp`. Модалки пока простые div-оверлеи (тех-долг — PrimeVue Dialog в Этапе 2 при первом реальном справочнике).

#### Структурная миграция `src/` под Vuexy-layout

Причина: разработчики команды знают старую структуру `yangi-mahalla-main/src/` (Vue 2 + Vuexy + Vuex); нужно минимизировать onboarding cost при переходе на Vue 3 + Pinia + TS.

**Изменения:**

| Было (до рестайла) | Стало |
|---|---|
| `src/api/client.ts` + `src/api/endpoints/*.ts` | `src/libs/axios.ts` + `src/api/{auth,administration,permissions}.ts` (flat) |
| `src/plugins/casl.ts`, `src/plugins/primevue.ts` | `src/libs/acl/index.ts`, `src/libs/primevue/index.ts` |
| `src/i18n/*` | `src/libs/i18n/{index.ts, locales/*.json}` |
| `src/components/layout/AppShell.vue/AppSidebar.vue/AppTopbar.vue` | `src/layouts/vertical/LayoutVertical.vue`, `src/layouts/full/LayoutFull.vue`, `src/layouts/components/{Sidebar,Navbar}.vue` |
| меню захардкожено в Sidebar.vue | `src/navigation/vertical/{main,sales,contracts,finance,references,sms_reports_admin,index}.ts` — один файл на домен, агрегатор |
| `src/router/index.ts` (монолит) | `src/router/index.ts` + `src/router/administration.ts` (per-domain) |
| `src/stores/{auth,permissions}.ts` | `src/store/{auth,permissions}.ts` — переименование папки `stores/` → `store/` |
| `src/views/LoginView.vue`, `DashboardView.vue`, `NotFoundView.vue`, `ForbiddenView.vue` | `src/views/Login.vue`, `Home.vue`, `error/Error404.vue`, `error/Forbidden.vue` |
| `src/views/admin/UsersView.vue`, `RolesView.vue`, `RoleEditView.vue` + `src/components/admin/PermissionTreeEditor.vue` | `src/views/modules/Administration/userManagement/{index,roles,roleView}.vue` + `components/PermissionTreeEditor.vue` |

Pinia остаётся **один файл на стор** (не Vuex-паттерн `{state,mutations,actions,getters}` × 4 файла). Это идиома Pinia; объяснено в `frontend/ARCHITECTURE.md`.

**Созданы:**
- `frontend/ARCHITECTURE.md` — карта новой структуры для команды + mapping Vuexy → новое + примеры «Vuex → Pinia» и «Options API → `<script setup>`». Это онбординг-док.

#### Sidebar cleanup (22 апреля, конец сессии)

Убраны disabled-пункты **Канбан лидов** и **Презентация** из `src/navigation/vertical/sales.ts` и i18n-ключи — они в архитектурном списке «дропаем» (пункт 10).

### Что НЕ сделано в эту сессию

Я начал идти по **дизайн-плану** `design_handoff/README.md` (Login → Dashboard → Clients → Shaxmatka → Kanban → Contract), но остановились после Dashboard. **Дальше идём по продуктовому плану — Этап 2 (References)**, а не по дизайн-плану, потому что:

- Clients/Shaxmatka/Kanban/Contract без бэкенда = mock, который будет переписан.
- Kanban вообще дропнут.
- Shaxmatka реализуется естественно в Этапе 3 (Objects), Clients — в Этапе 4, Contract — в Этапе 5.

Дизайн-система уже поверх шелла и компонентных классов — любой новый экран Этапа 2+ сразу получит стили. Нет нужды делать mock-прототипы.

### Технический долг из рестайла

- Ghost-шахматка в Login рендерит 96 div'ов inline. ОК для auth-экрана (редко загружается), но если понадобится — вынести в компонент.
- CSS-переменные в Tailwind config работают через `var(--*)` — это означает, что `ym-*` утилиты **не поддерживают opacity-модификатор** (`bg-ym-primary/50` не сработает). Если понадобится — перевести токены на CSS Color 5 relative syntax (`oklch(from var(--primary) l c h / <alpha-value>)`).
- В `main.css` есть несколько hover-состояний с `oklch(0.93 0.045 155)` хардкодом — это значение hover'а у `.btn-soft`, которое не в токенах. Если понадобится больше — добавить `--primary-softer` в токены.

## Предыдущая сессия — 21 апреля 2026

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

### Этап 2 — References ✅ ЗАКРЫТ 22 апреля

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

### Этап 3 — Objects domain ✅ ЗАКРЫТ 22 апреля (включая Шахматку, duplication, force-delete)

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

### Этап 4 — Clients ✅ ЗАКРЫТ 22 апреля

- `Client`: entity (phys/jur), gender, full_name, phones[] ArrayField, emails[] ArrayField, inn, oked, pin, birth_date (для phys), address, description, FK Staff (manager), FK status, groups M2M
- `ClientContact` (бывший Employee): FK Client, name, role (директор/подписант), is_chief, phones[], `passport` JSONField (серия, номер, кем выдан, дата выдачи, адрес прописки), birth_date, inn, pin
- `Requisite`: FK Client, type (internal/local), bank_requisite JSONField (счёт, банк, MFO)
- Frontend: список + карточка с табами (Договоры / Контакты / Реквизиты / Заметки)

### Этап 5 — Contracts (6-7 дней) — **В РАБОТЕ** (5.1 + 5.2 закрыты 23 апреля)

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
