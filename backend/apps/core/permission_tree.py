"""Hardcoded permission tree — source of truth for what roles can be granted.

The tree is a list of top-level modules; each module may have up to 3 more
levels of children. Every leaf (and every inner node) has a dotted `key` that
roles reference in their `permissions` JSONField.

Shape of a node:

    {
        "key": "clients",
        "label": {"ru": "...", "uz": "...", "oz": "..."},
        "children": [...],     # optional
    }

Two helpers:
    - `all_permission_keys()` — flat list of every valid key in the tree
    - `default_permissions(value=False)` — a full `{key: value}` dict (used to
      seed a new role with all perms off).

The tree is exposed to the frontend at `GET /api/v1/permissions/tree/` so the
role editor can render exactly the same structure.
"""
from __future__ import annotations

from typing import TypedDict


class I18nLabel(TypedDict):
    ru: str
    uz: str
    oz: str


class PermissionNode(TypedDict, total=False):
    key: str
    label: I18nLabel
    children: list["PermissionNode"]


def _label(ru: str, uz: str, oz: str) -> I18nLabel:
    return {"ru": ru, "uz": uz, "oz": oz}


def _crud(base: str, ru: str, uz: str, oz: str) -> list[PermissionNode]:
    """Helper: standard view/create/edit/delete children under a module."""
    return [
        {"key": f"{base}.view", "label": _label(f"Просмотр {ru}", f"{uz} ko'rish", f"{oz} кўриш")},
        {"key": f"{base}.create", "label": _label(f"Создать {ru}", f"{uz} yaratish", f"{oz} яратиш")},
        {"key": f"{base}.edit", "label": _label(f"Редактировать {ru}", f"{uz} tahrirlash", f"{oz} таҳрирлаш")},
        {"key": f"{base}.delete", "label": _label(f"Удалить {ru}", f"{uz} o'chirish", f"{oz} ўчириш")},
    ]


PERMISSION_TREE: list[PermissionNode] = [
    # --- ПРОДАЖА / CLIENTS ---
    {
        "key": "clients",
        "label": _label("Клиенты", "Mijozlar", "Мижозлар"),
        "children": [
            *_crud("clients", "клиента", "Mijoz", "Мижоз"),
            {
                "key": "clients.contacts",
                "label": _label("Контакты клиента", "Mijoz kontaktlari", "Мижоз контактлари"),
                "children": _crud("clients.contacts", "контакт", "Kontakt", "Контакт"),
            },
            {
                "key": "clients.requisites",
                "label": _label("Реквизиты клиента", "Mijoz rekvizitlari", "Мижоз реквизитлари"),
                "children": _crud("clients.requisites", "реквизит", "Rekvizit", "Реквизит"),
            },
            {
                "key": "clients.statuses",
                "label": _label("Статусы клиентов", "Mijoz statuslari", "Мижоз ҳолатлари"),
                "children": _crud("clients.statuses", "статус", "Status", "Ҳолат"),
            },
            {
                "key": "clients.groups",
                "label": _label("Группы клиентов", "Mijoz guruhlari", "Мижоз гуруҳлари"),
                "children": _crud("clients.groups", "группу", "Guruh", "Гуруҳ"),
            },
        ],
    },
    # --- ДОГОВОРЫ ---
    {
        "key": "contracts",
        "label": _label("Договоры", "Shartnomalar", "Шартномалар"),
        "children": [
            {
                "key": "contracts.unsigned",
                "label": _label("Неподписанные", "Imzolanmagan", "Имзоланмаган"),
                "children": [
                    {"key": "contracts.unsigned.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
                    {"key": "contracts.unsigned.create", "label": _label("Создать", "Yaratish", "Яратиш")},
                    {"key": "contracts.unsigned.edit", "label": _label("Редактировать", "Tahrirlash", "Таҳрирлаш")},
                    {"key": "contracts.unsigned.delete", "label": _label("Удалить", "O'chirish", "Ўчириш")},
                    {"key": "contracts.unsigned.send_to_wait", "label": _label("Отправить на согласование", "Kelishuvga yuborish", "Келишувга юбориш")},
                    {"key": "contracts.unsigned.approve", "label": _label("Утвердить", "Tasdiqlash", "Тасдиқлаш")},
                    {"key": "contracts.unsigned.sign", "label": _label("Подписать", "Imzolash", "Имзолаш")},
                    {"key": "contracts.unsigned.request_edit", "label": _label("Вернуть на доработку", "Qaytarib yuborish", "Қайтариб юбориш")},
                    {"key": "contracts.unsigned.generate_schedule", "label": _label("Сгенерировать график", "Jadvalni yaratish", "Жадвални яратиш")},
                    {"key": "contracts.unsigned.generate_pdf", "label": _label("Сгенерировать PDF", "PDF yaratish", "PDF яратиш")},
                ],
            },
            {
                "key": "contracts.signed",
                "label": _label("Подписанные", "Imzolangan", "Имзоланган"),
                "children": [
                    {"key": "contracts.signed.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
                    {"key": "contracts.signed.download", "label": _label("Скачать PDF", "PDF yuklash", "PDF юклаш")},
                    {"key": "contracts.signed.cancel", "label": _label("Отменить", "Bekor qilish", "Бекор қилиш")},
                ],
            },
            {
                "key": "contracts.edit_requests",
                "label": _label("Запросы на редактирование", "Tahrirlash so'rovlari", "Таҳрирлаш сўровлари"),
                "children": [
                    {"key": "contracts.edit_requests.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
                    {"key": "contracts.edit_requests.approve", "label": _label("Одобрить", "Ma'qullash", "Маъқуллаш")},
                    {"key": "contracts.edit_requests.reject", "label": _label("Отклонить", "Rad etish", "Рад этиш")},
                ],
            },
        ],
    },
    # --- ФИНАНСЫ ---
    {
        "key": "finance",
        "label": _label("Финансы", "Moliya", "Молия"),
        "children": [
            {"key": "finance.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
            {"key": "finance.create_income", "label": _label("Добавить поступление", "Kirim qo'shish", "Кирим қўшиш")},
            {"key": "finance.create_refund", "label": _label("Оформить возврат", "Qaytarish", "Қайтариш")},
            {"key": "finance.export", "label": _label("Экспорт", "Eksport", "Экспорт")},
            {"key": "finance.import", "label": _label("Импорт", "Import", "Импорт")},
            {"key": "finance.charts", "label": _label("Показатели / графики", "Ko'rsatkichlar", "Кўрсаткичлар")},
            {
                "key": "finance.payment_types",
                "label": _label("Разрешённые типы оплаты", "Ruxsat etilgan to'lov turlari", "Рухсат этилган тўлов турлари"),
                "children": [
                    {"key": "finance.payment_types.bank", "label": _label("Банк", "Bank", "Банк")},
                    {"key": "finance.payment_types.cash", "label": _label("Наличные", "Naqd", "Нақд")},
                    {"key": "finance.payment_types.barter", "label": _label("Бартер", "Barter", "Бартер")},
                ],
            },
        ],
    },
    # --- ОБЪЕКТЫ (УЧЁТ) ---
    {
        "key": "objects",
        "label": _label("Объекты (учёт)", "Obyektlar (hisobot)", "Объектлар (ҳисобот)"),
        "children": [
            {
                "key": "objects.projects",
                "label": _label("Жилые комплексы", "Turar-joy majmualari", "Турар-жой мажмуалари"),
                "children": _crud("objects.projects", "ЖК", "JK", "ЖК"),
            },
            {
                "key": "objects.buildings",
                "label": _label("Корпуса", "Binolar", "Бинолар"),
                "children": _crud("objects.buildings", "корпус", "Bino", "Бино"),
            },
            {
                "key": "objects.sections",
                "label": _label("Подъезды", "Podyezdlar", "Подъездлар"),
                "children": _crud("objects.sections", "подъезд", "Podyezd", "Подъезд"),
            },
            {
                "key": "objects.floors",
                "label": _label("Этажи", "Qavatlar", "Қаватлар"),
                "children": [
                    *_crud("objects.floors", "этаж", "Qavat", "Қават"),
                    {"key": "objects.floors.edit_price", "label": _label("Менять цену за м²", "m² narxini o'zgartirish", "м² нархини ўзгартириш")},
                ],
            },
            {
                "key": "objects.apartments",
                "label": _label("Квартиры", "Kvartiralar", "Квартиралар"),
                "children": [
                    {"key": "objects.apartments.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
                    {"key": "objects.apartments.edit", "label": _label("Редактировать", "Tahrirlash", "Таҳрирлаш")},
                    {"key": "objects.apartments.book", "label": _label("Бронировать", "Band qilish", "Банд қилиш")},
                    {"key": "objects.apartments.book_vip", "label": _label("Бронь руководство", "Rahbariyat brony", "Раҳбарият брони")},
                    {"key": "objects.apartments.change_status", "label": _label("Менять статус", "Holatni o'zgartirish", "Ҳолатни ўзгартириш")},
                ],
            },
            {
                "key": "objects.discounts",
                "label": _label("Скидки", "Chegirmalar", "Чегирмалар"),
                "children": _crud(
                    "objects.discounts", "правило скидок",
                    "Chegirma qoidasi", "Чегирма қоидаси",
                ),
            },
            {
                "key": "objects.payment_plans",
                "label": _label("Планы оплаты", "To'lov rejalari", "Тўлов режалари"),
                "children": _crud(
                    "objects.payment_plans", "план оплаты",
                    "To'lov rejasi", "Тўлов режаси",
                ),
            },
            {
                "key": "objects.calculations",
                "label": _label("Расчёты по квартирам", "Kvartira hisob-kitoblari", "Квартира ҳисоб-китоблари"),
                "children": _crud(
                    "objects.calculations", "расчёт",
                    "Hisob-kitob", "Ҳисоб-китоб",
                ),
            },
        ],
    },
    # --- СПРАВОЧНИКИ ---
    {
        "key": "references",
        "label": _label("Справочники", "Ma'lumotnomalar", "Маълумотномалар"),
        "children": [
            {"key": "references.offices", "label": _label("Отделы продаж", "Savdo ofislari", "Савдо офислари"), "children": _crud("references.offices", "офис", "Ofis", "Офис")},
            {"key": "references.developers", "label": _label("Застройщики", "Quruvchilar", "Қурувчилар"), "children": _crud("references.developers", "застройщик", "Quruvchi", "Қурувчи")},
            {"key": "references.currencies", "label": _label("Валюты", "Valyutalar", "Валюталар"), "children": _crud("references.currencies", "валюту", "Valyuta", "Валюта")},
            {
                "key": "references.templates",
                "label": _label("Шаблоны договоров", "Shartnoma shablonlari", "Шартнома шаблонлари"),
                "children": [
                    *_crud("references.templates", "шаблон", "Shablon", "Шаблон"),
                    {
                        "key": "references.templates.manage_global",
                        "label": _label(
                            "Управлять глобальными шаблонами",
                            "Global shablonlar boshqaruvi",
                            "Глобал шаблонлар бошқаруви",
                        ),
                    },
                ],
            },
            # NB: 13 simple lookups (ApartmentType, RoomType, ConstructionStage,
            # Decoration, PremisesDecoration, HomeMaterial, OutputWindows,
            # OccupiedBy, Badge, PaymentMethod, PaymentInPercent, Region,
            # Location) share a single permission bundle for sanity.
            {"key": "references.lookups", "label": _label("Классификаторы", "Tasniflagichlar", "Таснифлагичлар"), "children": _crud("references.lookups", "классификатор", "Tasniflagich", "Таснифлагич")},
        ],
    },
    # --- SMS ---
    {
        "key": "sms",
        "label": _label("SMS рассылка", "SMS yuborish", "СМС юбориш"),
        "children": [
            {"key": "sms.templates", "label": _label("Шаблоны", "Shablonlar", "Шаблонлар"), "children": _crud("sms.templates", "шаблон", "Shablon", "Шаблон")},
            {"key": "sms.manual", "label": _label("Ручная отправка", "Qo'lda yuborish", "Қўлда юбориш"), "children": [
                {"key": "sms.manual.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
                {"key": "sms.manual.send", "label": _label("Отправить", "Yuborish", "Юбориш")},
            ]},
            {"key": "sms.auto", "label": _label("Авторассылка", "Avtomatik yuborish", "Автоматик юбориш"), "children": [
                *_crud("sms.auto", "правило", "Qoida", "Қоида"),
                {"key": "sms.auto.toggle", "label": _label("Вкл/выкл", "Yoqish/o'chirish", "Ёқиш/ўчириш")},
            ]},
        ],
    },
    # --- АДМИНИСТРАЦИЯ ---
    {
        "key": "administration",
        "label": _label("Администрация", "Boshqaruv", "Бошқарув"),
        "children": [
            {"key": "administration.users", "label": _label("Пользователи", "Foydalanuvchilar", "Фойдаланувчилар"), "children": _crud("administration.users", "пользователь", "Foydalanuvchi", "Фойдаланувчи")},
            {"key": "administration.roles", "label": _label("Роли и разрешения", "Rollar va huquqlar", "Роллар ва ҳуқуқлар"), "children": [
                *_crud("administration.roles", "роль", "Rol", "Рол"),
                {"key": "administration.roles.permissions", "label": _label("Редактор разрешений", "Huquq muharriri", "Ҳуқуқ муҳаррири")},
            ]},
        ],
    },
    # --- ОТЧЁТЫ ---
    {
        "key": "reports",
        "label": _label("Отчёты", "Hisobotlar", "Ҳисоботлар"),
        "children": [
            {"key": "reports.view", "label": _label("Просмотр", "Ko'rish", "Кўриш")},
        ],
    },
]


def all_permission_keys() -> list[str]:
    """Flatten the tree and return every dotted key in declaration order."""
    out: list[str] = []

    def walk(nodes: list[PermissionNode]) -> None:
        for n in nodes:
            out.append(n["key"])
            for child in n.get("children", []):
                walk([child])

    walk(PERMISSION_TREE)
    return out


def default_permissions(value: bool = False) -> dict[str, bool]:
    """Build a full `{key: value}` dict for seeding a new role."""
    return {k: value for k in all_permission_keys()}
