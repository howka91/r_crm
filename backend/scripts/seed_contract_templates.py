"""One-off seeder for three contract templates — used for manual UX
testing of the Phase 5.4 frontend.

Run inside the backend container via manage.py shell so the Django
settings module is on sys.path:

    docker compose exec backend python manage.py shell \\
        -c "exec(open('scripts/seed_contract_templates.py').read())"

Idempotent-ish: deletes templates whose title starts with a known
prefix, then re-creates them. Safe to re-run.
"""
from __future__ import annotations

from apps.contracts.models import ContractTemplate
from apps.objects.models import Project


# Shared trilingual placeholder declarations. `key` is what the
# admin writes in {{...}}; `path` is resolved against Contract context
# (apps.contracts.services.snapshot.build_context).
COMMON_PLACEHOLDERS = [
    {"key": "contract_number", "path": "contract.contract_number", "label": "Номер договора"},
    {"key": "contract_date", "path": "contract.date", "label": "Дата договора"},
    {"key": "total_price", "path": "contract.total_amount", "label": "Сумма договора"},
    {"key": "down_payment", "path": "contract.down_payment", "label": "Первый взнос"},
    {"key": "client_name", "path": "client.full_name", "label": "ФИО клиента"},
    {"key": "client_inn", "path": "client.inn", "label": "ИНН клиента"},
    {"key": "client_address", "path": "client.address", "label": "Адрес клиента"},
    {"key": "client_phone", "path": "client.phones.0", "label": "Телефон клиента"},
    {"key": "signer_name", "path": "signer.full_name", "label": "ФИО подписанта"},
    {"key": "signer_role", "path": "signer.role", "label": "Должность подписанта"},
    {"key": "passport_series", "path": "signer.passport.series", "label": "Серия паспорта"},
    {"key": "passport_number", "path": "signer.passport.number", "label": "Номер паспорта"},
    {"key": "passport_issued_by", "path": "signer.passport.issued_by", "label": "Кем выдан"},
    {"key": "passport_issued_date", "path": "signer.passport.issued_date", "label": "Дата выдачи"},
    {"key": "apt_number", "path": "apartment.number", "label": "Номер квартиры"},
    {"key": "apt_rooms", "path": "apartment.rooms_count", "label": "Комнат"},
    {"key": "apt_area", "path": "apartment.area", "label": "Площадь"},
    {"key": "apt_total_price", "path": "apartment.total_price", "label": "Цена квартиры"},
    {"key": "apt_floor", "path": "apartment.floor.number", "label": "Этаж"},
    {"key": "project_title", "path": "project.title.ru", "label": "Название ЖК"},
    {"key": "project_address", "path": "project.address", "label": "Адрес ЖК"},
    {"key": "dev_name", "path": "developer.name.ru", "label": "Застройщик"},
    {"key": "dev_director", "path": "developer.director", "label": "Директор"},
    {"key": "dev_inn", "path": "developer.inn", "label": "ИНН застройщика"},
    {"key": "dev_bank_name", "path": "developer.bank_name", "label": "Банк"},
    {"key": "dev_bank_account", "path": "developer.bank_account", "label": "Расчётный счёт"},
]


# --- Template bodies -----------------------------------------------------

STANDARD_SALE_BODY = """\
<h1 style="text-align:center;">ДОГОВОР КУПЛИ-ПРОДАЖИ № {{contract_number}}</h1>
<p style="text-align:center;color:#555;">г. Ташкент, {{contract_date}}</p>

<p>
  <strong>{{dev_name}}</strong> (ИНН {{dev_inn}}), в лице директора
  <strong>{{dev_director}}</strong>, действующего на основании Устава,
  именуемое в дальнейшем «Продавец», с одной стороны, и
  <strong>{{client_name}}</strong> (ИНН {{client_inn}}), в лице
  {{signer_role}} <strong>{{signer_name}}</strong>, паспорт серии
  {{passport_series}} № {{passport_number}}, выдан
  {{passport_issued_by}} {{passport_issued_date}}, именуемый в дальнейшем
  «Покупатель», с другой стороны, совместно именуемые «Стороны»,
  заключили настоящий Договор о нижеследующем.
</p>

<h2>1. Предмет договора</h2>
<p>
  1.1. Продавец обязуется передать в собственность Покупателя, а
  Покупатель обязуется принять и оплатить квартиру № <strong>{{apt_number}}</strong>,
  расположенную на {{apt_floor}} этаже, в жилом комплексе
  <strong>«{{project_title}}»</strong> по адресу: {{project_address}}.
</p>
<p>
  1.2. Квартира состоит из {{apt_rooms}} комнат, общая площадь —
  {{apt_area}} м².
</p>

<h2>2. Цена договора и порядок расчётов</h2>
<p>2.1. Цена Договора составляет <strong>{{total_price}}</strong> сум.</p>
<p>2.2. Первоначальный взнос: <strong>{{down_payment}}</strong> сум.</p>
<p>2.3. Оставшаяся сумма уплачивается согласно графику платежей.</p>

<h2>3. Реквизиты Продавца</h2>
<p>
  {{dev_name}}<br>
  ИНН: {{dev_inn}}<br>
  Банк: {{dev_bank_name}}<br>
  Р/с: {{dev_bank_account}}
</p>

<h2>4. Реквизиты Покупателя</h2>
<p>
  {{client_name}} (ИНН {{client_inn}})<br>
  Адрес: {{client_address}}<br>
  Телефон: {{client_phone}}
</p>

<div style="margin-top:40px;">
  <table style="width:100%;">
    <tr>
      <td style="width:50%;vertical-align:top;">
        <strong>Продавец:</strong><br>
        {{dev_director}}<br><br>
        _______________________
      </td>
      <td style="width:50%;vertical-align:top;text-align:right;">
        <strong>Покупатель:</strong><br>
        {{signer_name}}<br><br>
        _______________________
      </td>
    </tr>
  </table>
</div>

<p style="text-align:right;margin-top:24px;">
  <img src="{{__qr__}}" width="120" height="120" alt="QR">
</p>
"""


MORTGAGE_SALE_BODY = """\
<h1 style="text-align:center;">ДОГОВОР КУПЛИ-ПРОДАЖИ С ИПОТЕКОЙ № {{contract_number}}</h1>
<p style="text-align:center;color:#555;">г. Ташкент, {{contract_date}}</p>

<p>
  <strong>{{dev_name}}</strong>, ИНН {{dev_inn}}, в лице директора
  <strong>{{dev_director}}</strong>, именуемое «Продавец», и
  <strong>{{client_name}}</strong>, ИНН {{client_inn}}, в лице
  {{signer_role}} <strong>{{signer_name}}</strong>
  (паспорт {{passport_series}} № {{passport_number}}, выдан
  {{passport_issued_by}} {{passport_issued_date}}), именуемый
  «Покупатель», заключили настоящий Договор.
</p>

<h2>1. Предмет договора</h2>
<p>
  Продавец передаёт в собственность Покупателя с использованием
  ипотечного кредитования квартиру
  № <strong>{{apt_number}}</strong> ({{apt_rooms}}-комн., {{apt_area}} м²,
  этаж {{apt_floor}}) в ЖК «<strong>{{project_title}}</strong>»,
  адрес: {{project_address}}.
</p>

<h2>2. Цена и условия оплаты</h2>
<p>2.1. Общая сумма договора: <strong>{{total_price}}</strong> сум.</p>
<p>
  2.2. Первоначальный взнос в размере <strong>{{down_payment}}</strong> сум
  Покупатель уплачивает за счёт собственных средств до подписания настоящего
  Договора.
</p>
<p>
  2.3. Оставшаяся часть оплачивается за счёт кредитных средств,
  предоставляемых банком-кредитором на условиях, предусмотренных
  кредитным договором. График платежей прилагается к настоящему
  Договору как неотъемлемая часть.
</p>

<h2>3. Обременение</h2>
<p>
  3.1. Квартира, являющаяся предметом настоящего Договора, с момента
  её государственной регистрации на имя Покупателя находится в залоге
  у банка-кредитора в обеспечение исполнения обязательств Покупателя
  по кредитному договору.
</p>

<h2>4. Банковские реквизиты Продавца</h2>
<p>
  {{dev_name}}<br>
  ИНН: {{dev_inn}}<br>
  Банк: {{dev_bank_name}}<br>
  Р/с: {{dev_bank_account}}
</p>

<h2>5. Контакты Покупателя</h2>
<p>
  {{client_name}} (ИНН {{client_inn}})<br>
  Адрес: {{client_address}}<br>
  Телефон: {{client_phone}}
</p>

<div style="margin-top:40px;">
  <table style="width:100%;">
    <tr>
      <td style="width:50%;vertical-align:top;">
        <strong>Продавец:</strong><br>
        {{dev_director}}<br><br>
        _______________________
      </td>
      <td style="width:50%;vertical-align:top;text-align:right;">
        <strong>Покупатель:</strong><br>
        {{signer_name}}<br><br>
        _______________________
      </td>
    </tr>
  </table>
</div>

<p style="text-align:right;margin-top:24px;">
  <img src="{{__qr__}}" width="120" height="120" alt="QR">
</p>
"""


PRELIMINARY_BODY = """\
<h1 style="text-align:center;">ПРЕДВАРИТЕЛЬНЫЙ ДОГОВОР № {{contract_number}}</h1>
<p style="text-align:center;color:#555;">г. Ташкент, {{contract_date}}</p>

<p>
  Настоящий предварительный договор заключён между
  <strong>{{dev_name}}</strong> («Застройщик») в лице {{dev_director}}
  и <strong>{{client_name}}</strong> («Клиент») в лице {{signer_name}}
  (паспорт {{passport_series}} № {{passport_number}}) в подтверждение
  намерения Сторон заключить в будущем основной договор
  купли-продажи квартиры.
</p>

<h2>Параметры квартиры</h2>
<ul>
  <li>ЖК: «{{project_title}}», {{project_address}}</li>
  <li>Номер: <strong>{{apt_number}}</strong></li>
  <li>Этаж: {{apt_floor}}, комнат: {{apt_rooms}}, площадь: {{apt_area}} м²</li>
  <li>Сумма: <strong>{{total_price}}</strong> сум</li>
  <li>Задаток (первый взнос): <strong>{{down_payment}}</strong> сум</li>
</ul>

<h2>Обязательства сторон</h2>
<p>
  1. Клиент вносит задаток в размере {{down_payment}} сум в счёт будущего
  платежа по основному договору.
</p>
<p>
  2. Застройщик обязуется не заключать договоров с иными лицами в
  отношении указанной квартиры в течение 14 календарных дней с даты
  подписания настоящего договора.
</p>
<p>
  3. В случае отказа Клиента от заключения основного договора задаток
  не возвращается. В случае отказа Застройщика задаток возвращается в
  двойном размере.
</p>

<h2>Контакты</h2>
<table style="width:100%;border-collapse:collapse;">
  <tr>
    <td style="width:50%;padding:8px;border:1px solid #ddd;vertical-align:top;">
      <strong>Застройщик</strong><br>
      {{dev_name}}<br>
      ИНН: {{dev_inn}}<br>
      Банк: {{dev_bank_name}}<br>
      Р/с: {{dev_bank_account}}
    </td>
    <td style="width:50%;padding:8px;border:1px solid #ddd;vertical-align:top;">
      <strong>Клиент</strong><br>
      {{client_name}} (ИНН {{client_inn}})<br>
      Адрес: {{client_address}}<br>
      Телефон: {{client_phone}}
    </td>
  </tr>
</table>

<div style="margin-top:32px;">
  <table style="width:100%;">
    <tr>
      <td style="width:50%;">{{dev_director}} / _____________</td>
      <td style="width:50%;text-align:right;">{{signer_name}} / _____________</td>
    </tr>
  </table>
</div>

<p style="text-align:right;margin-top:24px;">
  <img src="{{__qr__}}" width="110" height="110" alt="QR">
</p>
"""


# --- Seeder --------------------------------------------------------------

def seed() -> None:
    # Idempotent: wipe whatever was previously seeded (by title prefix).
    stale = ContractTemplate.all_objects.filter(title__startswith="[Demo] ")
    if stale.exists():
        count = stale.count()
        stale.delete()
        print(f"Removed {count} previously-seeded templates.")

    projects = list(Project.objects.order_by("id"))
    if len(projects) < 2:
        print(
            "WARNING: expected at least 2 Project rows for the per-project "
            "templates. Continuing with what's available.",
        )

    targets = [
        {
            "title": "[Demo] Стандартный ДКП (глобальный)",
            "body": STANDARD_SALE_BODY,
            "placeholders": COMMON_PLACEHOLDERS,
            "project": None,  # global
            "is_active": True,
        },
        {
            "title": "[Demo] ДКП с ипотекой — ЖК 1",
            "body": MORTGAGE_SALE_BODY,
            "placeholders": COMMON_PLACEHOLDERS,
            "project": projects[0] if projects else None,
            "is_active": True,
        },
        {
            "title": "[Demo] Предварительный договор — ЖК 2",
            "body": PRELIMINARY_BODY,
            "placeholders": COMMON_PLACEHOLDERS,
            "project": projects[1] if len(projects) > 1 else None,
            "is_active": True,
        },
    ]

    for spec in targets:
        tpl = ContractTemplate.objects.create(**spec)
        scope = f"project={spec['project'].id}" if spec["project"] else "GLOBAL"
        print(f"  created #{tpl.id:3d}  {scope:14s}  {tpl.title}")

    print(f"\nDone. Total ContractTemplate rows: {ContractTemplate.objects.count()}")


# Always run when the file is exec()'d by manage.py shell.
seed()
