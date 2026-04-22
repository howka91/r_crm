"""Admin registrations for the clients app."""
from __future__ import annotations

from django.contrib import admin

from apps.clients.models import (
    Client,
    ClientContact,
    ClientGroup,
    ClientStatus,
    Requisite,
)


@admin.register(ClientStatus)
class ClientStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "color", "sort", "is_active")
    list_filter = ("is_active",)
    ordering = ("sort", "id")


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sort", "is_active")
    list_filter = ("is_active",)
    ordering = ("sort", "id")


class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 0
    fields = ("full_name", "role", "is_chief", "email")


class RequisiteInline(admin.TabularInline):
    model = Requisite
    extra = 0
    fields = ("type", "bank_requisite")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "entity", "status", "manager", "is_active")
    list_filter = ("entity", "is_active", "status")
    search_fields = ("full_name", "inn", "pin")
    filter_horizontal = ("groups",)
    inlines = [ClientContactInline, RequisiteInline]


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "client", "role", "is_chief", "is_active")
    list_filter = ("is_active", "is_chief")
    search_fields = ("full_name", "inn", "pin")


@admin.register(Requisite)
class RequisiteAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "type", "is_active")
    list_filter = ("type", "is_active")
