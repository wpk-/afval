"""
{
    'last_change': '2023-01-01T00:00:00',
    'data': [
        {
            'code': str,                    containers
            'fractie: str,                  fracties
            'type': str,                    container_types
            'volume': float,                container_types
            'persend': bool,                container_types
            'adres': str,                   clusters
            'cluster': str,                 clusters
            'cluster_id': int,              clusters
            'lon': float,                   putten
            'lat': float,                   putten
        },
        ...
    ],
}
"""
import logging
from operator import itemgetter
from typing import Any

from local.backup import load, save
from .jsontools import CompressedJSON, DataJSON, IndexOrder

logger = logging.getLogger(__name__)

JSON = dict[str, Any]


class ContainersJSON(CompressedJSON):
    sort_order = ('fractie', 'volume', 'type', 'persend', 'cluster_id', 'adres', 'cluster')
    transforms = {
        'data': {
            'fractie': ['i', 'r'],
            'volume': ['i', 'r'],
            'type': ['i', 'r'],
            'persend': ['i', 'r'],
            'cluster_id': ['d'],
            'adres': ['i', 'd'],
            'cluster': ['i', 'd'],
            'code': ['j', '@'],
            'lat': ['m', 1_000_000, 'd'],
            'lon': ['m', 1_000_000, 'd'],
        },
        'raw': {
            'adres': ['j', '@'],
            'cluster': ['j', '@'],
        },
    }
    index_order = {
        'fractie': IndexOrder.FREQUENCY,
        'volume': IndexOrder.FREQUENCY,
        'type': IndexOrder.FREQUENCY,
        'persend': IndexOrder.ASCENDING,
        'adres': IndexOrder.UNSORTED,
        'cluster': IndexOrder.UNSORTED,
    }


def push(file_out: str, filenames: dict[str, str]) -> None:
    logger.debug('containers...')

    clusters = load(filenames['clusters'])
    container_types = load(filenames['container_types'])
    containers = load(filenames['containers'])
    fracties = load(filenames['fracties'])
    putten = load(filenames['putten'])

    # NB. fracties hebben geen datum.
    last_change = max(map(itemgetter('last_change'),
        (clusters, container_types, containers, putten)))

    if load(file_out)['last_change'] == last_change:
        logger.debug(' - skip. Geen veranderingen sinds laatste keer.')
        return

    # Voor de gebruiker is het logischer om op de kaart het adres van het cluster
    # te lezen dan het adres van de put. Op die manier komen de adressen van de
    # wegingen overeen met de adressen van de containers op het cluster.
    clusteradres = {
        w: o['location']['address']
        for o in clusters['data']
        for w in o['wells']
    }
    cluster = {
        w: o['name']
        for o in clusters['data']
        for w in o['wells']
    }
    cluster_id = {
        w: o['id']
        for o in clusters['data']
        for w in o['wells']
    }
    fractie = {
        f'/fractions/{o["id"]}': o['name']
        for o in fracties['data']
    }
    locatie = {
        f'/wells/{o["id"]}': o['location']['geometry']['coordinates']
        for o in putten['data']
    }
    persend = {
        f'/container_types/{o["id"]}': o['compressionContainer'] or 'pers' in o['name'].lower()
        for o in container_types['data']
    }
    typetype = {
        f'/container_types/{o["id"]}': o['containerType']
        for o in container_types['data']
    }
    volume = {
        f'/container_types/{o["id"]}': o['volume']
        for o in container_types['data']
    }

    rows = [
        {
            'code': c['idNumber'],
            'fractie': fractie.get(c['fraction'], ''),
            'type': typetype.get(c['containerType'], ''),
            'volume': volume.get(c['containerType'], None),
            'persend': persend.get(c['containerType'], False),
            'adres': clusteradres.get(c['well'], ''),
            'cluster': cluster.get(c['well'], ''),
            'cluster_id': cluster_id.get(c['well'], -1),
            'lon': locatie.get(c['well'], (None, None))[0],
            'lat': locatie.get(c['well'], (None, None))[1],
        }
        for c in containers['data']
        if c['active'] == 1
    ]

    # Compress the data.
    #  - transpose: 2.583 mB -> 1.400 mB (-45%)
    #  - index: 1.400 mB -> 898 kB (-36%)
    #  - unrepeat: 898 kB -> 793 kB (-12%)
    #  - delta: 793 kB -> 751 kB (-5%)
    #  - join: 751 kB -> 703 kB (-6%)
    #  - separate lat, lon with factor and delta: 703 kB -> 613 kB (-13%)
    # ---> reduced to 24% of original size = factor 4.2 compression.

    ContainersJSON.save(file_out, {
        'last_change': last_change,
        'data': rows
    })
    logger.debug(' - done.')
