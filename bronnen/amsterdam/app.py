from collections.abc import Callable, Iterator
from datetime import datetime
from functools import partialmethod
from logging import getLogger
from typing import Any, TypeVar
from urllib.parse import urljoin

from bronnen.base import API

logger = getLogger(__name__)

JSON = dict[str, Any]
T = TypeVar('T')


class Amsterdam(API):
    api_root = 'https://api.data.amsterdam.nl'
    api_version = 'v1'

    def __init__(self, *args, **kwargs) -> None:
        """Maakt een CMS API interface object.
        Geef een sessie object op waarover alle communicatie loopt.
        """
        super().__init__(*args, **kwargs)
        self.session.headers.update({
            'Accept': 'application/geo+json',
            'Accept-Crs': 'EPSG:4326',
        })

    @classmethod
    def url(cls, path: str = '') -> str:
        """Geeft de volledige URL voor een gegeven pad.
        """
        return urljoin(cls.api_root, f'/{cls.api_version}{path}')

    def fetch(self, path: str, query: JSON = None, sinds: datetime | str = None,
              ) -> Iterator[JSON]:
        """Itereert over de volledige lijst met waardes van de server.
        Waardes zijn ruwe JSON items.
        """
        # GeoJSON verzoeken krijgen alle data in 1 request.
        # (Dus zonder paginering.)
        url = self.url(path)
        params = {
            **(query or {}),
            '_format': 'geojson',
        }

        if sinds:
            # NB. Specific to "gebieden".
            try:
                params['registratiedatum[gt]'] = sinds.isoformat()
            except AttributeError:
                # 'str' object has no attribute 'isoformat'.
                params['registratiedatum[gt]'] = sinds

        res = self.session.get(url, params=params)

        res.raise_for_status()
        json = res.json()
        items = json['features']

        for item in items:
            yield item

    # Laadt de lijst met buurten.
    # {
    #   'type': 'Feature',
    #   'id': str,
    #   'geometry': {
    #       'type': 'Polygon',
    #       'coordinates': [[[float, float],[ ... ],[float, float]]]
    #   },
    #   'properties': {
    #       'id': str,
    #       'registratiedatum': str (datetime),
    #       'naam': str,
    #       'code': str,
    #       'beginGeldigheid': str (datetime),
    #       'eindGeldigheid': null,
    #       'documentdatum': str (date),
    #       'documentnummer': str,
    #       'cbsCode': str,
    #       'ligtInWijkId': str,
    #       'ligtInGgpgebiedId': null,
    #       'ligtInGgwgebiedId': null,
    #   }
    # }  # (19 jan 2023)
    buurten: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/gebieden/buurten/')

    # Laadt de lijst met GGP-gebieden.
    ggp_gebieden: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/gebieden/ggpgebieden/')

    # Laadt de lijst met GGW-gebieden.
    ggw_gebieden: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/gebieden/ggwgebieden/')

    # Laadt de lijst met stadsdelen.
    stadsdelen: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/gebieden/stadsdelen/')

    # Laadt de lijst met wijken.
    wijken: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/gebieden/wijken/')
