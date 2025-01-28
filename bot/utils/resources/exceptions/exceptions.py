class PlaceholderMissingError(ValueError):
    """
    Исключение, которое возникает, если отсутствует заполнитель в kwargs
    для форматирования строки.
    """

    def __init__(self, phrase_id, missing_key):
        message = f"Missing placeholder in kwargs for phrase '{phrase_id}': {missing_key}"
        super().__init__(message)
        self.phrase_id = phrase_id
        self.missing_key = missing_key


class CalculationError(Exception):
    """
    Базовое исключение для всех ошибок, возникающих в процессе вычислений.
    """
    def __init__(self, detail: str):
        message = f"Ошибка вычисления: {detail}"
        super().__init__(message)
        self.detail = detail


class TimeOutError(TimeoutError):
    """
    Базовое исключение для всех ошибок, возникающих в процессе вычислений.
    """
    def __init__(self, detail: str):
        message = f"Ошибка времени ожидания: {detail}"
        super().__init__(message)
        self.detail = detail


class ExceptionError(Exception):
    """
    Базовое исключение для всех ошибок, возникающих в процессе вычислений.
    """
    def __init__(self, detail: str):
        message = f"Общая ошибка: {detail}"
        super().__init__(message)
        self.detail = detail


class AttributeAccessError(AttributeError):
    """
    Исключение для ошибок доступа к атрибутам.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка доступа к атрибутам: {detail}")


class MissingKeyError(KeyError):
    """
    Исключение для отсутствующих ключей в данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка при извлечении данных: отсутствует ключ {detail}")


class DataTypeError(TypeError):
    """
    Исключение для ошибок типа данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка типов данных: {detail}")


class ValueProcessingError(ValueError):
    """
    Исключение для ошибок обработки значений.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка обработки значений: {detail}")


class DatabaseError(Exception):
    """
    Базовое исключение для ошибок базы данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка базы данных: {detail}")
        self.detail = detail


class DatabaseFetchError(DatabaseError):
    """
    Исключение для ошибок извлечения данных из базы данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка извлечения данных: {detail}")


class DatabaseSaveError(DatabaseError):
    """
    Исключение для ошибок сохранения данных в базе данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка сохранения данных: {detail}")


class DatabaseCreationError(DatabaseError):
    """
    Исключение для ошибок создания записей в базе данных.
    """
    def __init__(self, detail: str):
        super().__init__(f"Ошибка создания записи: {detail}")
