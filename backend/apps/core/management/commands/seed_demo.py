"""Seed the local dev DB with all references + one demo ЖК (5 floors).

Idempotent: every row is keyed by the ru-label (or `code` for Currency) so
re-running just fills in what's missing. Never deletes or overwrites data.

Usage:
    docker compose exec backend python manage.py seed_demo

What it creates
---------------
References:
    * 4 currencies (UZS, USD, EUR, RUB) with example rates
    * 1 Developer ("Yangi Mahalla Qurilish")
    * 1 SalesOffice
    * All 13 LookupModel-based dictionaries with a small but realistic
      set of entries (apartment types, room types, construction stages,
      decoration types, payment methods, payment-in-percent buckets,
      region + location, etc.)

Objects:
    * 1 Project: "ЖК «Yangi Mahalla» · Демо"
    * 1 Building: "Корпус 1"
    * 1 Section: "Подъезд 1"
    * 5 Floors (with a rising base price per m²)
    * 4 apartments per floor = 20 apartments total, with area + total_price
      pre-computed (no discounts — add DiscountRule + Calculation manually
      if testing pricing cascade).
"""
from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.objects.models import Apartment, Building, Floor, Project, Section
from apps.references.models import (
    ApartmentType,
    Badge,
    ConstructionStage,
    Currency,
    Decoration,
    Developer,
    HomeMaterial,
    Location,
    OccupiedBy,
    OutputWindows,
    PaymentInPercent,
    PaymentMethod,
    PremisesDecoration,
    Region,
    RoomType,
    SalesOffice,
)


def _i18n(ru: str, uz: str = "", oz: str = "") -> dict[str, str]:
    """Build an I18nField dict, defaulting uz/oz to ru when omitted."""
    return {"ru": ru, "uz": uz or ru, "oz": oz or ru}


def _get_or_create_lookup(
    model: type, ru: str, uz: str = "", oz: str = "", **extra: Any,
) -> tuple[Any, bool]:
    """Create a LookupModel row keyed by `name.ru`, return (obj, created).

    Django's JSONField equality on a dict isn't reliably usable as a
    get_or_create key; filtering on `name__ru` is more robust across
    re-runs.
    """
    obj = model.objects.filter(name__ru=ru).first()
    if obj is not None:
        return obj, False
    obj = model.objects.create(name=_i18n(ru, uz, oz), **extra)
    return obj, True


class Command(BaseCommand):
    help = "Seed demo references and one project with 5 floors."

    # --- Register console reporting helpers ---

    def _log(self, msg: str) -> None:
        self.stdout.write(msg)

    def _tally(self, label: str, created: int, total: int) -> None:
        if created:
            self._log(
                self.style.SUCCESS(f"  {label:24s} +{created} (итого: {total})")
            )
        else:
            self._log(f"  {label:24s}  0 (итого: {total})")

    # --- Main entry point ---

    def handle(self, *args, **options):
        with transaction.atomic():
            self._log(self.style.MIGRATE_HEADING("\n=== Справочники ==="))
            self._seed_currencies()
            self._seed_developer()
            self._seed_sales_office()
            self._seed_lookups()

            self._log(self.style.MIGRATE_HEADING("\n=== Объекты (ЖК) ==="))
            project, building, section, floors, apartments = self._seed_demo_project()
            self._log(
                self.style.SUCCESS(
                    f"\nГотово: 1 ЖК, {len(floors)} этажей, {len(apartments)} квартир."
                )
            )
            self._log(f"  Project id={project.id} title={project.title['ru']}")
            self._log(f"  Building id={building.id}")
            self._log(f"  Section id={section.id}")

    # --- References ---

    def _seed_currencies(self) -> None:
        # (code, symbol, ru, rate)
        rows = [
            ("UZS", "сум", "Узбекский сум", Decimal("1.0000")),
            ("USD", "$", "Доллар США", Decimal("12600.0000")),
            ("EUR", "€", "Евро", Decimal("13700.0000")),
            ("RUB", "₽", "Российский рубль", Decimal("140.0000")),
        ]
        created = 0
        for code, symbol, ru, rate in rows:
            _, was_new = Currency.objects.get_or_create(
                code=code,
                defaults={
                    "symbol": symbol,
                    "name": _i18n(ru),
                    "rate": rate,
                },
            )
            if was_new:
                created += 1
        self._tally("Currency", created, Currency.objects.count())

    def _seed_developer(self) -> None:
        created = 0
        dev = Developer.objects.filter(name__ru="Yangi Mahalla Qurilish").first()
        if dev is None:
            Developer.objects.create(
                name=_i18n("Yangi Mahalla Qurilish"),
                director="Каримов Б. Т.",
                address="г. Ташкент, ул. Амира Темура, 123",
                email="info@yangimahalla.uz",
                phone="+998712345678",
                bank_name="Hamkorbank",
                bank_account="20208000000000000001",
                inn="301234567",
                nds="302000000000000",
                oked="41200",
            )
            created = 1
        self._tally("Developer", created, Developer.objects.count())

    def _seed_sales_office(self) -> None:
        created = 0
        office = SalesOffice.objects.filter(name__ru="Центральный офис").first()
        if office is None:
            SalesOffice.objects.create(
                name=_i18n("Центральный офис"),
                address="г. Ташкент, пр. Амира Темура, 108",
                latitude=Decimal("41.3111500"),
                longitude=Decimal("69.2797200"),
                work_start=time(9, 0),
                work_end=time(18, 0),
                phone="+998901234567",
            )
            created = 1
        self._tally("SalesOffice", created, SalesOffice.objects.count())

    def _seed_lookups(self) -> None:
        # --- ApartmentType (3)
        created = 0
        for ru in ("Квартира", "Апартамент", "Нежилое помещение"):
            _, new = _get_or_create_lookup(ApartmentType, ru)
            created += int(new)
        self._tally("ApartmentType", created, ApartmentType.objects.count())

        # --- RoomType (6)
        created = 0
        for ru in ("Студия", "1-комн", "2-комн", "3-комн", "4-комн", "5+ комн"):
            _, new = _get_or_create_lookup(RoomType, ru)
            created += int(new)
        self._tally("RoomType", created, RoomType.objects.count())

        # --- ConstructionStage (5)
        created = 0
        for sort, ru in enumerate(
            ("Котлован", "Фундамент", "Каркас", "Внутренняя отделка", "Сдан"),
            start=1,
        ):
            _, new = _get_or_create_lookup(ConstructionStage, ru, sort=sort)
            created += int(new)
        self._tally("ConstructionStage", created, ConstructionStage.objects.count())

        # --- Decoration (4)
        created = 0
        for ru in ("Без отделки", "Предчистовая", "Чистовая", "С ремонтом"):
            _, new = _get_or_create_lookup(Decoration, ru)
            created += int(new)
        self._tally("Decoration", created, Decoration.objects.count())

        # --- PremisesDecoration (3)
        created = 0
        for ru in ("Стандарт", "Бизнес", "Премиум"):
            _, new = _get_or_create_lookup(PremisesDecoration, ru)
            created += int(new)
        self._tally("PremisesDecoration", created, PremisesDecoration.objects.count())

        # --- HomeMaterial (4)
        created = 0
        for ru in ("Кирпич", "Монолит", "Панель", "Каркас"):
            _, new = _get_or_create_lookup(HomeMaterial, ru)
            created += int(new)
        self._tally("HomeMaterial", created, HomeMaterial.objects.count())

        # --- OutputWindows (4)
        created = 0
        for ru in ("Во двор", "На улицу", "На две стороны", "Торцевая"):
            _, new = _get_or_create_lookup(OutputWindows, ru)
            created += int(new)
        self._tally("OutputWindows", created, OutputWindows.objects.count())

        # --- OccupiedBy (3)
        created = 0
        for ru in ("Свободна", "Клиент", "Сотрудник"):
            _, new = _get_or_create_lookup(OccupiedBy, ru)
            created += int(new)
        self._tally("OccupiedBy", created, OccupiedBy.objects.count())

        # --- Badge (5)
        created = 0
        for ru, color in (
            ("Хит продаж", "#ef4444"),
            ("Акция", "#f59e0b"),
            ("Новинка", "#22c55e"),
            ("Последняя", "#8b5cf6"),
            ("VIP", "#0ea5e9"),
        ):
            _, new = _get_or_create_lookup(Badge, ru, color=color)
            created += int(new)
        self._tally("Badge", created, Badge.objects.count())

        # --- PaymentMethod (3)
        created = 0
        for ru in ("100% оплата", "Рассрочка", "Ипотека"):
            _, new = _get_or_create_lookup(PaymentMethod, ru)
            created += int(new)
        self._tally("PaymentMethod", created, PaymentMethod.objects.count())

        # --- PaymentInPercent (4 buckets)
        created = 0
        for percent in (Decimal("25.00"), Decimal("50.00"), Decimal("75.00"), Decimal("100.00")):
            ru = f"{int(percent)}%"
            existing = PaymentInPercent.objects.filter(percent=percent).first()
            if existing is None:
                PaymentInPercent.objects.create(name=_i18n(ru), percent=percent)
                created += 1
        self._tally("PaymentInPercent", created, PaymentInPercent.objects.count())

        # --- Region (4)
        created = 0
        for ru in ("г. Ташкент", "Ташкентская область", "Самаркандская область", "Ферганская область"):
            _, new = _get_or_create_lookup(Region, ru)
            created += int(new)
        self._tally("Region", created, Region.objects.count())

        # --- Location (5) — bound to Region
        tashkent = Region.objects.filter(name__ru="г. Ташкент").first()
        created = 0
        if tashkent is not None:
            for ru in ("Юнусабадский район", "Мирзо-Улугбекский район", "Чиланзарский район", "Мирабадский район", "Яккасарайский район"):
                existing = Location.objects.filter(
                    name__ru=ru, region=tashkent,
                ).first()
                if existing is None:
                    Location.objects.create(name=_i18n(ru), region=tashkent)
                    created += 1
        self._tally("Location", created, Location.objects.count())

    # --- Objects (one demo project) ---

    def _seed_demo_project(
        self,
    ) -> tuple[Project, Building, Section, list[Floor], list[Apartment]]:
        developer = Developer.objects.filter(name__ru="Yangi Mahalla Qurilish").first()
        assert developer is not None, "Застройщик должен быть создан выше"

        project_title_ru = "ЖК «Yangi Mahalla» · Демо"
        project = Project.objects.filter(
            developer=developer, title__ru=project_title_ru,
        ).first()
        project_created = False
        if project is None:
            project = Project.objects.create(
                developer=developer,
                title=_i18n(project_title_ru),
                address="г. Ташкент, Юнусабадский район, ул. Демо, 1",
                description=_i18n(
                    "Демо-ЖК для локального тестирования — 5 этажей, 20 квартир.",
                ),
                contract_number_prefix="ЯМ",
                banks=[
                    {"name": "Hamkorbank", "account": "20208000000000000001"},
                    {"name": "Агробанк", "account": "20208000000000000002"},
                ],
            )
            project_created = True

        building, building_created = Building.objects.get_or_create(
            project=project,
            number="1",
            defaults={
                "title": _i18n("Корпус 1"),
                "cadastral_number": "10:01:0000000:0001",
            },
        )
        section, section_created = Section.objects.get_or_create(
            building=building,
            number=1,
            defaults={"title": _i18n("Подъезд 1")},
        )

        # 5 floors, rising base price by 300_000 UZS/m² per floor starting at
        # 12_000_000 (typical Tashkent new-build ballpark).
        floors: list[Floor] = []
        floors_created = 0
        for i in range(1, 6):
            price = Decimal("12000000.00") + Decimal("300000.00") * (i - 1)
            floor, was_new = Floor.objects.get_or_create(
                section=section,
                number=i,
                defaults={"price_per_sqm": price, "sort": i},
            )
            floors_created += int(was_new)
            floors.append(floor)

        # 4 apartments per floor — 1 studio, 1 one-bed, 1 two-bed, 1 three-bed.
        # Numbering: floor 1 → 101..104, floor 2 → 201..204, etc.
        decoration = Decoration.objects.filter(name__ru="Предчистовая").first()
        apartments: list[Apartment] = []
        apartments_created = 0
        rooms_recipe = [
            (1, Decimal("32.50"), True, False),    # studio
            (1, Decimal("42.75"), False, False),   # 1-комн
            (2, Decimal("58.20"), False, False),   # 2-комн
            (3, Decimal("85.00"), False, True),    # 3-комн euro
        ]
        for floor in floors:
            for idx, (rooms, area, is_studio, is_euro) in enumerate(rooms_recipe, start=1):
                number = f"{floor.number}0{idx}"  # 101, 102, ..., 504
                existing = Apartment.objects.filter(floor=floor, number=number).first()
                if existing is not None:
                    apartments.append(existing)
                    continue
                total = (area * floor.price_per_sqm).quantize(Decimal("0.01"))
                apartments.append(
                    Apartment.objects.create(
                        floor=floor,
                        number=number,
                        rooms_count=rooms,
                        area=area,
                        total_bti_area=area,
                        total_price=total,
                        is_studio=is_studio,
                        is_euro_planning=is_euro,
                        decoration=decoration,
                        status=Apartment.Status.FREE,
                        sort=idx,
                    ),
                )
                apartments_created += 1

        self._tally("Project", int(project_created), Project.objects.count())
        self._tally("Building", int(building_created), Building.objects.count())
        self._tally("Section", int(section_created), Section.objects.count())
        self._tally("Floor", floors_created, Floor.objects.count())
        self._tally("Apartment", apartments_created, Apartment.objects.count())

        return project, building, section, floors, apartments
