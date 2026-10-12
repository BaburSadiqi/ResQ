import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_requires_asyncpg() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://localhost/resq")
