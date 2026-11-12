"""Исключения пакета etl.

Все ошибки пайплайна наследуются от EtlError, поэтому main.py ловит один класс.
Сторонние ошибки (gdown, pandas, SQLAlchemy, sqlite3) модули оборачивают в свои.
"""


class EtlError(Exception):
    """Базовая ошибка ETL: пайплайн остановлен с понятным сообщением."""


class ExtractError(EtlError):
    """Не удалось получить или прочитать сырой датасет."""


class CredsError(EtlError):
    """Не удалось получить доступы к базе."""


class ValidationError(EtlError):
    """Данные не прошли проверку."""


class LoadError(EtlError):
    """Не удалось сохранить результат или записать его в базу."""
