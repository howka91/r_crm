"""Tests for core custom fields."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.core.fields import (
    AreaField,
    I18nField,
    MoneyField,
    PercentField,
    empty_i18n,
    validate_i18n,
)


class TestI18nField:
    def test_empty_default_has_all_langs(self):
        assert empty_i18n() == {"ru": "", "uz": "", "oz": ""}

    def test_validates_missing_lang(self):
        with pytest.raises(ValidationError):
            validate_i18n({"ru": "Hello", "uz": "Salom"})  # missing 'oz'

    def test_validates_non_dict(self):
        with pytest.raises(ValidationError):
            validate_i18n("not a dict")

    def test_validates_non_string_value(self):
        with pytest.raises(ValidationError):
            validate_i18n({"ru": "A", "uz": "B", "oz": 42})

    def test_accepts_valid(self):
        # Should not raise
        validate_i18n({"ru": "Квартира", "uz": "Kvartira", "oz": "Квартира"})

    def test_accepts_none(self):
        # None is allowed (field may be null=True)
        validate_i18n(None)


class TestMoneyField:
    def test_defaults_14_2(self):
        f = MoneyField()
        assert f.max_digits == 14
        assert f.decimal_places == 2
        assert f.default == Decimal("0.00")


class TestAreaField:
    def test_defaults_8_2(self):
        f = AreaField()
        assert f.max_digits == 8
        assert f.decimal_places == 2


class TestPercentField:
    def test_defaults_5_2(self):
        f = PercentField()
        assert f.max_digits == 5
        assert f.decimal_places == 2


class TestI18nFieldDefault:
    def test_default_is_empty_i18n(self):
        f = I18nField()
        # default is a callable returning the dict
        assert callable(f.default)
        assert f.default() == {"ru": "", "uz": "", "oz": ""}
