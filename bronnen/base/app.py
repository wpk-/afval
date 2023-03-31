import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from functools import wraps
from inspect import isgeneratorfunction
from typing import Any, TypeVar

from requests import HTTPError, Session

logger = logging.getLogger(__name__)

JSON = dict[str, Any]
T = TypeVar('T')


class API(ABC):
    def __init__(self, session: Session) -> None:
        """Maakt de API interface.

        De sessie wordt gebruikt voor alle communicatie naar de server. Zo is
        het ook eenvoudig om authenticatie op te zetten en te hergebruiken.
        """
        self.session = session

    @classmethod
    @abstractmethod
    def url(cls, path: str) -> str:
        """Geeft de volledige URL voor een gegeven pad.
        """

    @abstractmethod
    def fetch(self, path: str, query: JSON = None) -> Iterator[JSON]:
        """Itereert over de volledige lijst met waardes van de server.
        Waardes zijn ruwe JSON items.
        """


class Authenticated(API):
    def __init__(self, *args, auth: tuple[str, str] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.auth = auth

    @abstractmethod
    def login(self) -> bool:
        """Logt de gebruiker in en geeft aan of dit succesvol was.
        """

    @staticmethod
    def method(method):
        @wraps(method)
        def wrapped(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except HTTPError as err:
                if (err.response.status_code == 401 or (
                    # Patch necessary for Welvaarts. UGH!
                    err.response.status_code == 404 and
                    err.response.url.startswith('https://www.kilogram.nl')
                )):
                    logger.debug(f'Log in, then retry method {method.__name__!r}.')
                    if self.login():
                        return method(self, *args, **kwargs)
                raise err
        
        @wraps(method)
        def wrapped_gen(self, *args, **kwargs):
            gen = method(self, *args, **kwargs)
            try:
                return (yield from gen)
            except HTTPError as err:
                if (err.response.status_code == 401 or (
                    # Patch necessary for Welvaarts. UGH!
                    err.response.status_code == 404 and
                    err.response.url.startswith('https://www.kilogram.nl')
                )):
                    logger.debug(f'Log in, then retry method {method.__name__!r}.')
                    if self.login():
                        return (yield from method(self, *args, **kwargs))
                raise err

        if isgeneratorfunction(method):
            return wrapped_gen
        else:
            return wrapped
