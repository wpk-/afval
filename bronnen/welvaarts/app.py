from collections.abc import Iterator
from datetime import date, datetime
from logging import getLogger
from re import findall, search
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bronnen.base import API, Authenticated

logger = getLogger(__name__)

JSON = dict[str, Any]


def toisodate(s: str) -> str:
    return '-'.join(reversed(s.split('-')))


def toisodatetime(s: str) -> str:
    return f'{toisodate(s[:10])}T{s[11:]}' if s else ''


class Welvaarts(Authenticated, API):
    api_root = 'https://www.kilogram.nl'
    api_version = 'v3_6'

    @classmethod
    def url(cls, path: str = '') -> str:
        """Geeft de volledige URL voor een gegeven pad.
        """
        if path:
            return urljoin(cls.api_root, f'/{cls.api_version}{path}')
        else:
            return cls.api_root

    def login(self) -> bool:
        """Logt in op kilogram.nl.
        Geeft een waarde True terug als het inloggen gelukt is, anders False.
        """
        # Parse the login form with an re for simplicity (sorry).
        url = self.url()
        html = self.session.get(url).text
        parts = urlparse(search(r'action="([^"]+)"', html).group(1))
        hidden = dict(findall(r'type="hidden"\s+name="([^"]+)"\s+value="([^"]+)"', html))

        url = urljoin(url, parts.path)
        params = parse_qs(parts.query)
        username, password = self.auth
        data = {
            'username': username,
            'password': password,
            **hidden
        }
        res = self.session.post(url, data, params=params)
        return res.history[-1].url.endswith('/profile')

    def logout(self) -> None:
        """Logt uit van kilogram.nl.
        """
        url = self.url('/LogOut.php')
        data = {'bRemote': False}
        self.session.post(url, data)

    @Authenticated.method
    def fetch(self, path: str, query: JSON = None, page_size: int = 500
              ) -> Iterator[JSON]:
        """Itereert over de volledige lijst met waardes van de server.
        Waardes zijn ruwe JSON items.
        """
        url = self.url(path)
        data = {
            **(query or {}),
            'iDisplayStart': -1,
            'iDisplayLength': page_size,
        }

        keys = query['aNames[]']

        while True:
            data['iDisplayStart'] += 1
            res = self.session.post(url, data)

            # BAD: Welvaarts redirects unauthenticated requests.
            # BAD+: It redirects to a non-existing page (/var/www/...).
            # BAD++: So the error is a "302" redirect to a "404 Not Found"
            #        instead of the proper response: "401 Unauthorized".
            res.raise_for_status()
            json = res.json()
            items = json['aaData']

            for row in items:
                yield dict(zip(keys, row))
            
            if page_size is None or page_size < 1 or len(items) < page_size:
                break

    def wagens(self, *, page_size: int = 500, **kwargs) -> Iterator[JSON]:
        path = '/Vehicles/VehiclesProcess.php'
        query = {
            'sSearch': '',
            'aiSortCol[]': 1,
            'asSortDir[]': 'asc',
            'aNames[]': ['SystemId', 'VehicleReg', 'LatestWeighDate'],
            'aTypes[]': ['text', 'text', 'datetime'],
            'aColumns[]': ['SystemId', 'VehicleReg', 'LatestWeighDate'],
            **kwargs,
        }

        # The LatestWeighDate field is returned "DD-MM-YYYY HH:MM:SS". That is
        # SO annoying I just can't not fix that.
        def fixdatetime(o: JSON) -> JSON:
            o['LatestWeighDate'] = toisodatetime(o['LatestWeighDate'])
            return o

        return map(fixdatetime,
                   self.fetch(path, query, page_size=page_size))

    def wegingen(self, systeem_id: int, *, page_size: int = 5000,
                 sinds: datetime | str = None, **kwargs) -> Iterator[JSON]:
        path = '/Weigh/WeighProcess.php'
        query = {
            'sSearch': '',
            'aaSelectionFieldSystems[FractionId][]': systeem_id,
            'aiSortCol[]': [1, 2],
            'asSortDir[]': ['desc', 'desc'],
            'aSystems[]': systeem_id,
            'aNames[]': ['Seq', 'Date', 'Time', 'FractionId', 'FirstWeight',
                         'SecondWeight', 'NetWeight', 'Latitude', 'Longitude'],
            'aTypes[]': ['number', 'date', 'time', 'select', 'number',
                         'number', 'number', 'gps', 'gps'],
            'aiTable[]': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'aTableNames[]': ['weigh'],
            'aTablePrimKeys[]': ['Seq'],
            'aColumns[]': ['Seq', 'Date', 'Time', 'FractionId', 'FirstWeight',
                           'SecondWeight', 'NetWeight', 'Latitude', 'Longitude'],
            'sTabLabel': 'VehicleReg',
            **kwargs
        }

        if sinds:
            try:
                sinds = sinds.date().isoformat()
            except AttributeError:
                # 'str' object has no attribute 'date'.
                sinds = sinds.split('T')[0]
            query.update({
                'StartDate': sinds,
                'EndDate': date.today().isoformat(),
            })

        # The Date field is returned "DD-MM-YYYY". That is so annoying to
        # everything and anything that I just can't not fix that.
        def fixdate(o: JSON) -> JSON:
            o['Date'] = toisodate(o['Date'])
            return o
        
        # Add SystemId which is needed in every possible context.
        def addsystem(o: JSON) -> JSON:
            o['SystemId'] = systeem_id
            return o

        return map(addsystem, map(fixdate,
                   self.fetch(path, query, page_size=page_size)))
