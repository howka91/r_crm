"""Tests for the hardcoded permission tree."""
from apps.core.permission_tree import (
    PERMISSION_TREE,
    all_permission_keys,
    default_permissions,
)


class TestTree:
    def test_non_empty(self):
        assert len(PERMISSION_TREE) > 0

    def test_every_node_has_key_and_label(self):
        def walk(nodes):
            for n in nodes:
                assert "key" in n
                assert isinstance(n["key"], str) and n["key"]
                assert "label" in n
                assert set(n["label"].keys()) == {"ru", "uz", "oz"}
                for child in n.get("children", []):
                    walk([child])

        walk(PERMISSION_TREE)

    def test_keys_are_unique(self):
        keys = all_permission_keys()
        assert len(keys) == len(set(keys)), "duplicate permission keys"

    def test_child_keys_start_with_parent_key(self):
        def walk(nodes):
            for n in nodes:
                for child in n.get("children", []):
                    assert child["key"].startswith(n["key"] + "."), (
                        f"{child['key']} must start with {n['key']}."
                    )
                    walk([child])

        walk(PERMISSION_TREE)

    def test_default_permissions_all_false(self):
        perms = default_permissions(False)
        assert all(v is False for v in perms.values())
        assert len(perms) == len(all_permission_keys())

    def test_default_permissions_all_true(self):
        perms = default_permissions(True)
        assert all(v is True for v in perms.values())

    def test_expected_top_level_modules(self):
        top_keys = [n["key"] for n in PERMISSION_TREE]
        for expected in ("clients", "contracts", "finance", "objects", "references", "sms", "administration", "reports"):
            assert expected in top_keys
