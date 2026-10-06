class _TempValue:
    def __init__(self, mapping: dict, key: str, value: object) -> None:
        self._mapping = mapping
        self._key = key
        self._value = value
        self._old_value = ...

    def __enter__(self) -> dict:
        self._old_value = self._mapping.get(self._key, ...)
        self._mapping[self._key] = self._value
        return self._mapping

    def __exit__(self, exc_type, exc_value, traceback):
        if self._old_value is ...:
            self._mapping.pop(self._key, None)
        else:
            self._mapping[self._key] = self._old_value


def temporary_value(mapping: dict, key: str, value: object) -> _TempValue:
    if type(mapping) is not dict:
        raise TypeError(f"mapping must be a dict, got {type(mapping).__name__}")
    if type(key) is not str:
        raise TypeError(f"key must be a str, got {type(key).__name__}")
    return _TempValue(mapping, key, value)