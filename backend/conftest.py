"""Root pytest conftest — shared fixtures live here."""
import pytest


@pytest.fixture
def api_client():
    """DRF test client."""
    from rest_framework.test import APIClient

    return APIClient()
