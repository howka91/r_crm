# Архитектура r_crm

Полный документ: [`r_crm_architecture.docx`](../_old/r_crm_architecture.docx) (исходник).

Эта страница — краткий навигатор + отклонения, принятые при переписывании.

## 9 Django apps

| App | Содержимое |
|---|---|
| `core` | `BaseModel`, `I18nField`, `MoneyField`, `AuditLog`, общие миксины |
| `users` | `Staff`, `Role`, `PermissionTree` (hardcoded), JWT |
| `references` | `Developer`, `SalesOffice`, `Currency`, справочники (типы квартир, отделка и т.д.) |
| `objects` | `Project → Building → Section → Floor → Apartment`, `DiscountRule`, `Calculation`, `PaymentPlan`, `ApartmentStatusLog`, `PriceHistory` |
| `clients` | `Client`, `ClientContact` (с паспортом/ИНН), `Requisite` |
| `contracts` | `Contract` (workflow `request/wait/edit/approve/sign_in`), `ContractTemplate`, `PaymentSchedule`, `Payment` |
| `finance` | `FinanceRecord`, ПКО (reportlab + QR) |
| `notifications` | `SmsTemplate`, `ManualSms`, `AutoSms`, `NotificationLog`, Eskiz-клиент |
| `reports` | определяются позже |

## Отклонения от исходной архитектуры (r_crm_architecture.docx)

Зафиксировано с пользователем перед началом рефакторинга:

### Расширено (взято из старого кода)

1. **Иерархия объектов — 6 уровней вместо 4**. Добавлены `Building` (корпус) и `Section` (подъезд) между `Project` и `Floor`. Обоснование: ЖК может иметь несколько корпусов, в корпусе несколько подъездов.
2. **Цена на уровне этажа** (`Floor.price_per_sqm`). У квартиры рассчитываемый `total_price`.
3. **Система скидок** `DiscountRule` (диапазон площади + процент оплаты + флаг дуплекса) и `Calculation` (авто-матрица для каждой квартиры × каждого процента оплаты).
4. **`ClientContact` с паспортом/ИНН** (был `Employee` в старом коде) — представитель клиента для B2B-сделок.
5. **Contract.action workflow** `request/wait/edit/approve/sign_in` (не упрощён до `draft/active/signed/cancelled`).
6. **Экран «Запросы на редактирование»** сохраняется.

### Убрано

1. `MortgageCurrency` и вся ипотечная арифметика.
2. `Task` (внутренний таск-трекер).
3. `Attachment`/`Comment` через `GenericForeignKey` — файлы теперь хранятся напрямую в полях моделей.
4. `SalesBPM`, `SaleOrder`, `KnowledgeBase`, `BotSite`, `News`, Kanban, «Презентация», «Над проектами работали».

### i18n

- Коды: `ru`, `uz` (латиница), `oz` (кириллица) — все три.
- Мультиязычные поля в БД: `JSONField` формата `{"ru": "...", "uz": "...", "oz": "..."}`.
- API отдаёт полный объект, фронт выбирает язык.

## Принципы

- **Бизнес-логика в `services/*.py`**, не в моделях/сигналах.
- **Явный пересчёт цен** через сервисы (не сигналы).
- **`Decimal` для денег** (никогда `Float`).
- **`select_for_update` для брони** в транзакции.
- **Soft delete** через `is_active=False` + кастомный менеджер.
- **Timezone**: `Asia/Tashkent`.
