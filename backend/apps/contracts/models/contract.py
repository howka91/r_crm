"""Contract — the main sales-document entity.

Links
-----
* `project` (PROTECT) — contract number is unique per project
  (Project.contract_number_index auto-increments).
* `apartment` (PROTECT) — the unit being sold.
* `calculation` (SET_NULL) — snapshot reference to the price-bucket card used
  at signing time. Preserved even after recalcs; `total_amount` / `down_payment`
  on the contract itself are the persistent financial snapshot.
* `signer` (PROTECT) — the **ClientContact** signing on behalf of the client;
  the actual `Client` is reached via `signer.client`. There is no direct FK to
  Client — representation always goes through the contact (matches legacy
  `clients_contract.customer_id -> clients_employee.company_id`).
* `author` (SET_NULL) — Staff who drafted the contract.

Snapshots
---------
* `requisite` — seller-side bank reqs (Developer + Project.banks) at signing.
* `document` — placeholder-filled values that the PDF was rendered from.
* `old` — list of previous `document` versions (written when workflow loops
  through `edit → wait → approve` again).

Workflow lives in `apps.contracts.services.transitions` (Phase 5.2). In this
Phase 5.1 slice we only define the data shape and base CRUD — explicit
transitions are *not* callable via arbitrary PATCH on `action`; that endpoint
will ship in 5.2.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import BaseModel


class Contract(BaseModel):
    class Action(models.TextChoices):
        REQUEST = "request", _("Запрос")
        WAIT = "wait", _("На согласовании")
        EDIT = "edit", _("На редактировании")
        APPROVE = "approve", _("Утверждён")
        SIGN_IN = "sign_in", _("Подписан")

    # --- Links ---
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.PROTECT,
        related_name="contracts",
        verbose_name=_("ЖК"),
    )
    apartment = models.ForeignKey(
        "objects.Apartment",
        on_delete=models.PROTECT,
        related_name="contracts",
        verbose_name=_("Квартира"),
    )
    calculation = models.ForeignKey(
        "objects.Calculation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
        verbose_name=_("Расчёт"),
    )
    signer = models.ForeignKey(
        "clients.ClientContact",
        on_delete=models.PROTECT,
        related_name="signed_contracts",
        verbose_name=_("Подписант (контакт клиента)"),
    )
    author = models.ForeignKey(
        "users.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_contracts",
        verbose_name=_("Автор"),
    )
    template = models.ForeignKey(
        "contracts.ContractTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
        verbose_name=_("Шаблон договора"),
        help_text=_(
            "Используется сервисом docgen для рендера PDF. Если пусто — "
            "PDF сгенерировать нельзя; менеджер обязан выбрать шаблон "
            "(глобальный или для этого ЖК) перед генерацией."
        ),
    )

    # --- Core data ---
    contract_number = models.CharField(
        _("Номер договора"), max_length=50, blank=True, default="", db_index=True,
        help_text=_("Уникален в рамках ЖК. Пусто — черновик без номера."),
    )
    date = models.DateField(_("Дата договора"), default=date_type.today)
    send_date = models.DateTimeField(_("Отправлено клиенту"), null=True, blank=True)
    related_person = models.CharField(
        _("Физлицо-подписант (доп.)"), max_length=255, blank=True,
        help_text=_("Свободный текст; используется, если подписант не заведён как контакт."),
    )
    description = models.TextField(_("Описание"), blank=True)

    # --- Money snapshot ---
    total_amount = MoneyField(
        _("Сумма договора"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    down_payment = MoneyField(
        _("Первый взнос"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # --- Payment methods (M2M — contracts can combine cash + transfer etc.) ---
    payment_methods = models.ManyToManyField(
        "references.PaymentMethod",
        blank=True,
        related_name="contracts",
        verbose_name=_("Способы оплаты"),
    )

    # --- Workflow ---
    action = models.CharField(
        _("Статус workflow"),
        max_length=16,
        choices=Action.choices,
        default=Action.REQUEST,
        db_index=True,
    )
    is_signed = models.BooleanField(_("Подписан"), default=False, db_index=True)
    is_paid = models.BooleanField(_("Оплачен"), default=False)
    is_mortgage = models.BooleanField(_("Ипотека"), default=False)

    # --- Document snapshots ---
    requisite = models.JSONField(
        _("Реквизиты продавца (snapshot)"), default=dict, blank=True,
    )
    document = models.JSONField(
        _("Заполненные поля (snapshot)"), default=dict, blank=True,
    )
    old = models.JSONField(
        _("Предыдущие версии"), default=list, blank=True,
    )

    file = models.FileField(
        _("PDF договора"), upload_to="contracts/pdf/", null=True, blank=True,
    )
    qr = models.ImageField(
        _("QR-код"), upload_to="contracts/qr/", null=True, blank=True,
    )

    class Meta:
        verbose_name = _("Договор")
        verbose_name_plural = _("Договоры")
        ordering = ["-date", "-id"]
        constraints = [
            # Номер уникален в рамках ЖК, но только для заполненных номеров —
            # у черновиков `contract_number` может быть пустым.
            models.UniqueConstraint(
                fields=["project", "contract_number"],
                condition=~Q(contract_number=""),
                name="contracts_contract_unique_project_number",
            ),
        ]
        indexes = [
            models.Index(fields=["action", "is_signed"]),
            models.Index(fields=["-date"]),
        ]

    def __str__(self) -> str:
        return self.contract_number or f"Contract #{self.pk} (draft)"
