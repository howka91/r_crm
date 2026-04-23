"""factory-boy factories for users."""
import factory
from factory.django import DjangoModelFactory

from apps.core.permission_tree import default_permissions
from apps.users.models import Role, Staff


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    code = factory.Sequence(lambda n: f"role-{n}")
    name = {"ru": "Тест", "uz": "Test", "oz": "Тест"}
    permissions = factory.LazyFunction(lambda: default_permissions(False))
    allowed_payment_types = factory.LazyFunction(list)


class StaffFactory(DjangoModelFactory):
    class Meta:
        model = Staff

    login = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    is_active = True
    language = "ru"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pass12345")
        obj = model_class.objects.create_user(password=password, **kwargs)
        return obj
