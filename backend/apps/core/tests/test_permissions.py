"""Tests for permission-check helper."""
from apps.core.permissions import check


class TestCheck:
    def test_leaf_true(self):
        perms = {"clients": True, "clients.view": True}
        assert check(perms, "clients.view") is True

    def test_leaf_false(self):
        perms = {"clients": True, "clients.view": False}
        assert check(perms, "clients.view") is False

    def test_parent_off_disables_children(self):
        # Even if the leaf is True, a False ancestor kills access.
        perms = {"clients": False, "clients.view": True}
        assert check(perms, "clients.view") is False

    def test_missing_key_is_denied(self):
        perms = {"clients": True}
        assert check(perms, "clients.delete") is False

    def test_deep_nesting(self):
        perms = {
            "objects": True,
            "objects.apartments": True,
            "objects.apartments.book": True,
        }
        assert check(perms, "objects.apartments.book") is True

    def test_deep_nesting_broken_middle(self):
        perms = {
            "objects": True,
            "objects.apartments": False,
            "objects.apartments.book": True,
        }
        assert check(perms, "objects.apartments.book") is False

    def test_empty_perms(self):
        assert check({}, "anything") is False
        assert check(None, "anything") is False

    def test_single_level(self):
        assert check({"reports": True}, "reports") is True
        assert check({"reports": False}, "reports") is False
