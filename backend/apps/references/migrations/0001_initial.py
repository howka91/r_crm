# Generated manually (Phase 2.1) — matches models in apps.references.models
# at the time of writing. Run `python manage.py makemigrations references`
# after first containerized run to confirm no drift; it should be a no-op.

import apps.core.fields
from decimal import Decimal

import django.core.validators
from django.db import migrations, models

import apps.references.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Изменено')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('code', models.CharField(help_text='ISO 4217: UZS, USD, EUR, RUB, …', max_length=3, unique=True, verbose_name='Код')),
                ('symbol', models.CharField(blank=True, max_length=4, verbose_name='Символ')),
                ('name', apps.core.fields.I18nField(default=apps.core.fields.empty_i18n, validators=[apps.core.fields.validate_i18n], verbose_name='Название')),
                ('rate', models.DecimalField(decimal_places=4, default=Decimal('1.0000'), help_text='1 единица валюты = N UZS', max_digits=14, verbose_name='Курс к UZS')),
            ],
            options={
                'verbose_name': 'Валюта',
                'verbose_name_plural': 'Валюты',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Developer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Изменено')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('name', apps.core.fields.I18nField(default=apps.core.fields.empty_i18n, validators=[apps.core.fields.validate_i18n], verbose_name='Название')),
                ('director', models.CharField(blank=True, max_length=255, verbose_name='Директор')),
                ('address', models.CharField(blank=True, max_length=512, verbose_name='Адрес')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=13, validators=[apps.references.models.phone_validator], verbose_name='Телефон')),
                ('bank_name', models.CharField(blank=True, max_length=255, verbose_name='Название банка')),
                ('bank_account', models.CharField(blank=True, max_length=32, verbose_name='Расчётный счёт')),
                ('inn', models.CharField(blank=True, db_index=True, max_length=16, verbose_name='ИНН')),
                ('nds', models.CharField(blank=True, max_length=32, verbose_name='Регистрация НДС')),
                ('oked', models.CharField(blank=True, max_length=16, verbose_name='ОКЭД')),
                ('extra', models.JSONField(blank=True, default=dict, verbose_name='Доп. данные')),
            ],
            options={
                'verbose_name': 'Застройщик',
                'verbose_name_plural': 'Застройщики',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SalesOffice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Изменено')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('name', apps.core.fields.I18nField(default=apps.core.fields.empty_i18n, validators=[apps.core.fields.validate_i18n], verbose_name='Название')),
                ('address', models.CharField(blank=True, max_length=512, verbose_name='Адрес')),
                ('latitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-90')), django.core.validators.MaxValueValidator(Decimal('90'))], verbose_name='Широта')),
                ('longitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-180')), django.core.validators.MaxValueValidator(Decimal('180'))], verbose_name='Долгота')),
                ('work_start', models.TimeField(blank=True, null=True, verbose_name='Начало работы')),
                ('work_end', models.TimeField(blank=True, null=True, verbose_name='Конец работы')),
                ('phone', models.CharField(blank=True, max_length=13, validators=[apps.references.models.phone_validator], verbose_name='Телефон')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='references/sales_offices/', verbose_name='Фото')),
            ],
            options={
                'verbose_name': 'Отдел продаж',
                'verbose_name_plural': 'Отделы продаж',
                'ordering': ['id'],
            },
        ),
    ]
