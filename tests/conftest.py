import pytest


@pytest.fixture
def password():
    return "strong-pass-123"


@pytest.fixture
def create_user(django_user_model, password):
    def _create(username):
        return django_user_model.objects.create_user(username=username, password=password)

    return _create
