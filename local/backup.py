"""
Een structuur voor het bijhouden van datalijstjes in JSON.

De datastructuur is als volgt:
{
    'last_change': datum,
    'last_sync': datum,
    'data': [
        {...},
        ...
    ]
}

last_sync is een timestamp gegenereerd op deze machine.
last_change is het timestamp van het meest recente item in data. Dit timestamp
    is dus gegenereerd op de server en hoeft niet in dezelfde tijdzone te staan
    als last_sync. Ook kan de klok verschillen dus de twee tijden zijn niet
    vergelijkbaar.
"""
from collections.abc import Callable, Hashable
from itertools import chain
from typing import Any

from orjson import dumps, loads

JSON = dict[str, Any]


def load(filename: str) -> JSON:
    try:
        with open(filename, 'rb') as f:
            return loads(f.read())
    except FileNotFoundError:
        return {
            'last_change': None,
            'last_sync': None,
            'data': [],
        }


def save(filename: str, obj: JSON) -> None:
    with open(filename, 'wb') as f:
        f.write(dumps(obj))


def merge(local: JSON, update: JSON, *, key: Callable[[JSON], Hashable]) -> JSON:
    """Voegt twee datasets samen: local en update.
    
    Twee items met dezelfde key(item) zijn hetzelfde object. In dat geval zal
    het item uit update het item uit local overschrijven.
    """
    if len(update['data']):
        last_change = update['last_change']
        last_sync = update['last_sync']
        items = list({
            key(item): item
            for item in chain(local['data'], update['data'])
        }.values())
    else:
        last_change = local['last_change']
        last_sync = update['last_sync'] # After all, we did sync.
        items = local['data']

    return {
        'last_change': last_change,
        'last_sync': last_sync,
        'data': items,
    }
