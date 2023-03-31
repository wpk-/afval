from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Any

from bronnen import Amsterdam
from local.backup import load, merge, save

logger = getLogger(__name__)

JSON = dict[str, Any]


def gebied_id(item: JSON) -> str:
    return item['properties']['identificatie']


def gebied_date(item: JSON) -> str:
    return item['properties']['registratiedatum']


def gebied_key(item: JSON) -> tuple[str, str]:
    return gebied_id(item), gebied_date(item)


def source_update(local: JSON, fetch: Callable[..., Iterable[JSON]],
                  start_time: datetime = None) -> JSON:
    """Haalt alle nieuwe gegevens op van een endpoint.
    Elk item heeft een datumveld registratiedatum.
    """
    t0 = datetime.now(tz=timezone.utc)
    start_time = start_time or t0

    key = gebied_key
    item_date = gebied_date

    known = set(map(key, local['data']))
    update = fetch(sinds=local['last_change'])
    update = [item for item in update if key(item) not in known]

    last_change = max(filter(None, map(item_date, update)), default=local['last_change'])
    last_sync = start_time.isoformat()

    logger.debug(f' - update = {len(update)} items, last_change = {last_change}.')
    logger.debug(f' - tijd: {datetime.now(tz=timezone.utc) - t0}')
    return {
        'last_change': last_change,
        'last_sync': last_sync,
        'data': update,
    }


def pull(amsterdam: Amsterdam, filenames: dict[str, str],
         rate_limit: timedelta = timedelta()) -> None:
    start_time = datetime.now(tz=timezone.utc)
    ref_time = start_time - rate_limit
    
    updates = {
        'buurten': amsterdam.buurten,
        'stadsdelen': amsterdam.stadsdelen,
        'wijken': amsterdam.wijken,
    }

    for name, fetch in updates.items():
        logger.debug(f'{name}...')
        filename = filenames[name]
        items = load(filename)
        if not items['last_sync'] or datetime.fromisoformat(items['last_sync']) < ref_time:
            update = source_update(items, fetch, start_time)
            items = merge(items, update, key=gebied_id)
            save(filename, items)
        else:
            logger.debug(f' - skip. Recent nog bijgewerkt.')

    logger.debug('done.')
