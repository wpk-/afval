from collections.abc import Callable, Iterator
from datetime import datetime
from functools import partialmethod
from logging import getLogger
from typing import Any, TypeVar
from urllib.parse import urljoin

from bronnen.base import API, Authenticated

logger = getLogger(__name__)

JSON = dict[str, Any]
T = TypeVar('T')


class Bammens(Authenticated, API):
    api_root = 'https://bammensservice.nl'

    def __init__(self, *args, **kwargs) -> None:
        """Maakt een CMS API interface object.
        Geef een sessie object op waarover alle communicatie loopt.
        """
        super().__init__(*args, **kwargs)
        self.session.headers.update({
            'Accept': 'application/json',
        })

    @classmethod
    def url(cls, path: str = '') -> str:
        """Geeft de volledige URL voor een gegeven pad.
        """
        return urljoin(cls.api_root, path)

    def login(self) -> bool:
        """Logt de gebruiker in.
        Geeft True terug als het inloggen geslaagd is en anders False.
        """
        url = self.url('/apilogin')
        username, password = self.auth
        data = {'username': username, 'password': password}
        res = self.session.post(url, json=data)
        json = res.json()
        success = json.get('code', 200) == 200

        if success:
            self.session.headers.update({
                'Authorization': f'Bearer {json["token"]}'
            })
            return True
        else:
            return False

    def logout(self) -> None:
        """Verwijdert de authorization header.
        """
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        else:
            logger.debug('No authentication to logout from.')

    @Authenticated.method
    def fetch(self, path: str, query: JSON = None, page_size: int = 500,
              sinds: str | datetime = None) -> Iterator[JSON]:
        """Itereert over de volledige lijst met waardes van de server.
        Waardes zijn ruwe JSON items.
        """
        url = self.url(path)
        params = {
            **(query or {}),
            'page': 0,
            'itemsPerPage': page_size,
        }

        if sinds:
            try:
                params['modifiedAt[strictly_after]'] = sinds.isoformat()
            except AttributeError:
                # 'str' object has no attribute 'isoformat'.
                params['modifiedAt[strictly_after]'] = sinds

        while True:
            params['page'] += 1
            res = self.session.get(url, params=params)

            res.raise_for_status()
            items = res.json()

            for item in items:
                yield item
            
            if not page_size or page_size < 1 or len(items) < page_size:
                break

    # Laadt de lijst met container clusters.
    # {
    #   'id': int,
    #   'startDate': str (datetime),
    #   'outOfServiceDate': str (datetime),
    #   'owner': str,
    #   'wells': list[str],
    #   'comment': str,
    #   'name': str,
    #   'status': str,
    #   'location': {
    #       'point': dict,
    #       'address': str,
    #       'district': str,
    #       'neighbourhood': str,
    #   },
    #   'modifiedAt': str (datetime),
    #   'amsterdamStatus': int,
    # }  # (19 jan 2023)
    clusters: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/clusters', page_size=1000)

    # Laadt de lijst met containertypes.
    # {
    #   'id': int,
    #   'articleCode': str,
    #   'hoistingType': str,
    #   'modifiedAt': str (datetime),
    #   'name': str,
    #   'volume': float,
    #   'weight': int,
    #   'containerType': str,
    #   'compressionContainer': bool,
    #   'compressionfactor': float,
    # }  # (19 jan 2023)
    container_types: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/container_types', page_size=500)

    # Laadt de lijst met afval containers.
    # {
    #   'chipNumber': str,
    #   'unitIdNumber': str,
    #   'color': str,
    #   'containerType': str,
    #   'emptyFrequency': str,
    #   'fraction': str,
    #   'mark': int,
    #   'owner': str,
    #   'replacementDate': str (datetime),
    #   'well': str,
    #   'adoptedContainer': true,
    #   'id': int,
    #   'createdAt': str (datetime),
    #   'deliveryDate': str (datetime),
    #   'idNumber': str,
    #   'modifiedAt': str (datetime),
    #   'operationalDate': str (datetime),
    #   'placingDate': str (datetime),
    #   'serialNumber': str,
    #   'warrantyDate': str (datetime),
    #   'active': int,
    #   'comment': str,
    #   'outOfServiceDate': str (datetime),
    #   'ownership': str,
    #   'amsterdamStatus': int,
    # }  # (19 jan 2023)
    containers: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/containers', page_size=1000)

    # Laadt de lijst met afvalfracties.
    # {
    #   'id': int,
    #   'name': str,
    # }  # (19 jan 2023)
    fracties: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/fractions', page_size=50)

    # Laadt de lijst met containerputten.
    # {
    #   'address': str,
    #   'district': str,
    #   'containers': [str],
    #   'neighbourhood': str,
    #   'owner': str,
    #   'wellType': str,
    #   'id': 0,
    #   'createdAt': str (datetime),
    #   'deliveryDate': str (datetime),
    #   'idNumber': str,
    #   'modifiedAt': str (datetime),
    #   'operationalDate': str (datetime),
    #   'placingDate': str (datetime),
    #   'serialNumber': str,
    #   'warrantyDate': str (datetime),
    #   'active': int,
    #   'comment': str,
    #   'outOfServiceDate': str (datetime),
    #   'ownership': str,
    #   'location': {
    #       'type': 'Feature',
    #       'geometry': {
    #           'type': 'Point',
    #           'coordinates': [float, float],
    #       },
    #       'properties': null,
    #   },
    #   'amsterdamStatus': int,
    # }  # (19 jan 2023)
    putten: Callable[..., Iterator[JSON]] = partialmethod(
        fetch, '/wells', page_size=1000)

    # def clusterfracties(self, clusters: Iterable[JSON] | None = None,
    #                     containers: Iterable[JSON] | None = None,
    #                     container_types: Iterable[JSON] | None = None,
    #                     fracties: Iterable[JSON] | None = None,
    #                     ) -> list[JSON]:
    #     """Combineert alle clusters, containers, types en fracties.
    #     Alle argumenten zijn optioneel. Standaard wordt de data geladen uit de
    #     Bammens API. Dit neemt wel wat tijd, uiteraard.
    #     """
    #     def strid2int(s: str) -> int:
    #         return int(s.split('/')[-1])

    #     clusters = clusters or self.clusters()
    #     containers = containers or self.containers()
    #     container_types = container_types or self.container_types()
    #     fracties = fracties or self.fracties()

    #     fractie_op_id = {f['id']: f for f in fracties}
    #     type_op_id = {t['id']: t for t in container_types}
    #     container_op_put = {strid2int(c['well']): c for c in containers}
    #     # NB. Containers met `well is None` verdwijnen.

    #     clusterfracties = []

    #     for cluster in clusters:
    #         # Containers op fractie -- voor dit cluster.
    #         containers_op_fractie = defaultdict(list)

    #         for put_id in map(strid2int, cluster['wells']):
    #             # Niet alle cluster-putten hebben een container.
    #             # Putten zonder container kunnen we overslaan.
    #             if put_id in container_op_put:
    #                 container = container_op_put[put_id]
    #                 fractie = fractie_op_id[strid2int(container['fraction'])]
    #                 containers_op_fractie[fractie].append(container)

    #         for fractie, f_containers in containers_op_fractie.items():
    #             types = [type_op_id[c.type_id] for c in f_containers]

    #             volume_containers = sum(t.volume for t in types)
    #             volume_afval = sum(t.volume_afval for t in types)
    #             aantal_ondergronds = sum(1 for t in types if t.ondergronds)

    #             clusterfracties.append(ClusterFractie(
    #                 cluster, fractie, tuple(f_containers),
    #                 volume_containers, volume_afval, aantal_ondergronds
    #             ))
        
    #     return clusterfracties