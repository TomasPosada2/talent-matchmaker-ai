import pytest

from src import auth


@pytest.fixture(autouse=True)
def reiniciar_intentos_login():
    """El contador de intentos fallidos es global; se aísla entre pruebas."""
    auth.limpiar_intentos_login()
    yield
    auth.limpiar_intentos_login()
