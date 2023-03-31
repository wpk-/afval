from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from datetime import datetime, timedelta, timezone
from itertools import chain
import logging
from operator import itemgetter
from typing import Any, TypeVar

from bronnen import Welvaarts
from local.backup import load, merge, save

logger = logging.getLogger(__name__)

JSON = dict[str, Any]
T = TypeVar('T')
H = TypeVar('H', bound=Hashable)


def group_by(key: Callable[[T], H], items: Iterable[T]) -> dict[H, list[T]]:
    h = defaultdict(list)
    for item in items:
        h[key(item)].append(item)
    return dict(h)


def wagens_update(welvaarts: Welvaarts, local: JSON) -> JSON:
    """Haalt alle nieuwe wagens op sinds de vorige sync.

    welvaarts is de interface naar Welvaarts (kilogram.nl).
    local bevat de huidige lokaal bekende data. Het is een JSON object met
        velden data, last_change en last_sync.

    Return waarde is een JSON object met alle wagens met nieuwe gegevens. Het
    is van dezelfde structuur als local.
    last_sync staat altijd op het huidige moment.
    last_change neemt de datum en tijd over van de meest recente weging.
    """
    start_time = datetime.now(tz=timezone.utc)

    key = itemgetter('SystemId', 'LatestWeighDate')
    item_date = itemgetter('LatestWeighDate')

    known = set(map(key, local['data']))
    update = welvaarts.wagens()
    update = [item for item in update if key(item) not in known]

    last_change = max(filter(None, map(item_date, update)), default=local['last_change'])
    last_sync = start_time.isoformat()

    logger.debug(f' - update {len(update)} items, last change = {last_change}.')
    logger.debug(f' - tijd: {datetime.now(tz=timezone.utc) - start_time}')
    return {
        'last_change': last_change,
        'last_sync': last_sync,
        'data': update,
    }


def wegingen_update(welvaarts: Welvaarts, local: JSON, wagens: JSON,
                    fetch_period: timedelta = timedelta(days=30)) -> JSON:
    """Haalt alle nieuwe wegingen op sinds de vorige sync.
    
    welvaarts is de interface naar Welvaarts (kilogram.nl).
    local bevat de huidige lokaal bekende data. Het is een JSON object met
        velden data, last_change en last_sync.
    wagens beval de laatste update van de wagens. Het is een JSON object net
        als local, maar dan met wagen objecten in data. Het bevat alleen de
        update, dus alleen de wagens waarvoor nieuwe data beschikbaar is.
    fetch_period geeft een tijdperiode (timedelta) waarover wegingen van de
        server gelezen worden. Verder terug dan dat lezen we niet.

    Return waarde is een JSON object met alle nieuwe wegingen. Het is van
    dezelfde structuur als local.
    last_sync staat altijd op het huidige moment.
    last_change neemt de datum en tijd over van de meest recente weging.
    """
    def local_date(item: JSON) -> str:
        return f'{item["Date"]}T{item["Time"]}'
    
    def local_key(item: JSON) -> tuple[str, str]:
        # Format van de datum komt overeen met wagens.LatestWeighDate.
        return item['SystemId'], local_date(item)

    wagen_key = itemgetter('SystemId', 'LatestWeighDate')

    start_time = datetime.now(tz=timezone.utc)

    known = set(map(local_key, local['data']))
    changed = set(map(wagen_key, wagens['data'])) - known
    since_lowerbound = (start_time - fetch_period).isoformat()
    since = defaultdict(lambda: since_lowerbound, {
        k: max(filter(None, chain(map(itemgetter(1), v), (since_lowerbound,))))
        for k, v in group_by(itemgetter(0), known).items()
    })
    update = [
        weging
        for system_id, _ in changed
        for weging in welvaarts.wegingen(system_id, sinds=since[system_id])
        if local_key(weging) not in known
    ]

    last_change = max(filter(None, map(local_date, update)), default=local['last_change'])
    last_sync = start_time.isoformat() 

    logger.debug(f' - update = {len(update)} items, last change = {last_change}.')
    logger.debug(f' - tijd: {datetime.now(tz=timezone.utc) - start_time}')
    return {
        'last_change': last_change,
        'last_sync': last_sync,
        'data': update,
    }


def pull(welvaarts: Welvaarts, filenames: dict[str, str],
         rate_limit: timedelta = timedelta()) -> None:
    """Werkt alle lokale bestanden bij met gegevens van Welvaarts.

    welvaarts is een bron interface voor Welvaarts (kilogram.nl).
    filenames is een dict met entries 'wagens' en 'wegingen'.
    """
    start_time = datetime.now(tz=timezone.utc)
    ref_time = start_time - rate_limit
    
    logger.debug('wagens...')
    filename = filenames['wagens']          # './data/welvaarts-wagens.json'
    wagens = load(filename)
    if not wagens['last_sync'] or datetime.fromisoformat(wagens['last_sync']) < ref_time:
        update = wagens_update(welvaarts, wagens)
        wagens = merge(wagens, update, key=itemgetter('SystemId'))
        save(filename, wagens)
    else:
        logger.debug(' - skip. Recent nog bijgewerkt.')
        return

    logger.debug('wegingen...')
    if len(update['data']):
        filename = filenames['wegingen']    # './data/welvaarts-wegingen.json'
        wegingen = load(filename)
        update = wegingen_update(welvaarts, wegingen, update)
        wegingen = merge(wegingen, update, key=itemgetter('SystemId', 'Seq'))
        save(filename, wegingen)
    else:
        logger.debug(' - skip. Geen wagens met nieuwe data.')

    logger.debug('done.')
