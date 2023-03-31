import json
import pickle
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

from orjson import dumps, loads

JSON = dict[str, Any]
T = TypeVar('T')


@contextmanager
def stored_pickle(filename: str, default: Callable[[], T]) -> Generator[T, None, None]:
    """Contextmanager for a pickle-backed storage.
    """
    obj = load_pickle(filename, default)
    try:
        yield obj
    finally:
        save_pickle(filename, obj)


def load_pickle(filename: str, default: Callable[[], T]) -> T:
    """Restores the data from a pickle.
    """
    try:
        with open(filename, 'rb') as f:
            obj = pickle.load(f)
    except FileNotFoundError:
        obj = default()
    return obj


def save_pickle(filename: str, obj: Any) -> None:
    """Stores the object in a pickle.
    """
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


@contextmanager
def stored_json(filename: str, default: Callable[[], JSON]) -> Generator[JSON, None, None]:
    """Contextmanager for a json-backed storage.
    """
    obj = load_json(filename, default)
    try:
        yield obj
    finally:
        save_json(filename, obj)


def load_json(filename: str, default: Callable[[], JSON], *args, **kwargs) -> JSON:
    """Restores the data from a JSON file.
    """
    try:
        with open(filename, 'rb') as f:
            # obj = json.load(f, *args, **kwargs)
            obj = loads(f.read(), *args, **kwargs)
    except FileNotFoundError:
        obj = default()
    return obj


def save_json(filename: str, obj: JSON, *args, **kwargs) -> None:
    """Stores the object in a JSON file.
    """
    with open(filename, 'wb') as f:
        # json.dump(obj, f, *args, **kwargs)
        f.write(dumps(obj, *args, **kwargs))
