"""
{
    'last_change': '2023-01-01T00:00:00',
    'buurten': [
        {
            'naam': str,
            'code': str,
            'ligt_in': str,             # wijk naam.
            'geometrie': [[long, lat], ...],
        },
        ...
    ],
    'wijken': [
        {
            'naam': str,
            'code': str,
            'ligt_in': str,             # stadsdeel naam.
            'geometrie': [[long, lat], ...],
        },
        ...
    ],
    'stadsdelen': [
        {
            'naam': str,
            'code': str,
            'ligt_in': '',
            'geometrie': [[long, lat], ...],
        },
        ...
    ],
}
"""
import logging
from operator import itemgetter
from typing import Any

from local.backup import load
from .jsontools import CompressedJSON, IndexOrder

logger = logging.getLogger(__name__)

JSON = dict[str, Any]


class GebiedenJSON(CompressedJSON):
    sort_order = ('gebied', 'ligt_in')
    transforms = {
        'group': 'gebied',
        'data': {
            'gebied': ['i', 'r'],
            'naam': ['i', 'd', 'r'],
            'code': ['j', '@'],
            'ligt_in': ['x', 'naam', 'r'],
            'lat': ['m>', 1_000_000, 's', 'd>'],
            'lon': ['m>', 1_000_000, 's', 'd>'],
        },
        'raw': {
            'naam': ['j', '@'],
        },
    }
    index_order = {
        'gebied': IndexOrder.UNSORTED,
        'naam': IndexOrder.UNSORTED,
    }


def push(file_out: str, filenames: dict[str, str]) -> None:
    logger.debug('gebieden...')

    buurten = load(filenames['buurten'])
    wijken = load(filenames['wijken'])
    stadsdelen = load(filenames['stadsdelen'])

    # NB. fracties hebben geen datum.
    last_change = max(map(itemgetter('last_change'),
                          (buurten, wijken, stadsdelen)))

    if load(file_out)['last_change'] == last_change:
        logger.debug(' - skip. Geen veranderingen sinds laatste keer.')
        return

    stadsdelen = {
        g['properties']['identificatie']: {
            'naam': g['properties']['naam'],
            'code': g['properties']['code'],
            'lon': list(map(itemgetter(0), g['geometry']['coordinates'][0])),
            'lat': list(map(itemgetter(1), g['geometry']['coordinates'][0])),
            'ligt_in': '',
        }
        for g in stadsdelen['data']
    }
    wijken = {
        g['properties']['identificatie']: {
            'naam': g['properties']['naam'],
            'code': g['properties']['code'],
            'lon': list(map(itemgetter(0), g['geometry']['coordinates'][0])),
            'lat': list(map(itemgetter(1), g['geometry']['coordinates'][0])),
            'ligt_in': stadsdelen[g['properties']['ligtInStadsdeelId']]['naam'],
        }
        for g in wijken['data']
    }
    buurten = {
        g['properties']['identificatie']: {
            'naam': g['properties']['naam'],
            'code': g['properties']['code'],
            'lon': list(map(itemgetter(0), g['geometry']['coordinates'][0])),
            'lat': list(map(itemgetter(1), g['geometry']['coordinates'][0])),
            'ligt_in': wijken[g['properties']['ligtInWijkId']]['naam'],
        }
        for g in buurten['data']
    }

    gebieden = {
        'last_change': last_change,
        '': [{
            'naam': '',
            'code': '',
            'lon': [],
            'lat': [],
            'ligt_in': '',
        }],
        'buurten': list(buurten.values()),
        'wijken': list(wijken.values()),
        'stadsdelen': list(stadsdelen.values()),
    }

    GebiedenJSON.save(file_out, gebieden)
    logger.debug(' - done.')
