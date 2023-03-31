from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from logging import getLogger
from operator import itemgetter
from typing import Any

from local.backup import load, merge, save
from bronnen import Bammens

logger = getLogger(__name__)

JSON = dict[str, Any]


tracked_key = itemgetter('id', 'modifiedAt')
tracked_date = itemgetter('modifiedAt')
untracked_key = itemgetter('id', 'name')


def untracked_update(local: JSON, fetch: Callable[..., Iterable[JSON]],
                     start_time: datetime = None) -> JSON:
    """Haalt alle waardes op van een endpoint en bekijkt wat veranderd is.
    Als key(item) niet voorkomt in de oude data dan is het item nieuw.
    Oude waardes, die in de nieuwe data niet meer voorkomen, blijven bewaard.
    Dat is omdat er in andere data nog best referenties kunnen bestaan.
    """
    t0 = datetime.now(tz=timezone.utc)
    start_time = start_time or t0

    key = untracked_key

    known = set(map(key, local['data']))
    update = [item for item in fetch() if key(item) not in known]

    last_change = start_time.isoformat()    # Aangezien de data toch geen datum heeft.
    last_sync = start_time.isoformat()

    logger.debug(f' - update = {len(update)} items zonder datum.')
    logger.debug(f' - tijd: {datetime.now(tz=timezone.utc) - t0}')
    return {
        'last_change': last_change,
        'last_sync': last_sync,
        'data': update,
    }


def tracked_update(local: JSON, fetch: Callable[..., Iterable[JSON]],
                   start_time: datetime = None) -> JSON:
    """Haalt alle nieuwe waardes op van een endpoint met tracking.
    Met tracking betekent dat alle items een datumveld modifiedAt hebben.
    """
    t0 = datetime.now(tz=timezone.utc)
    start_time = start_time or t0

    key = tracked_key
    item_date = tracked_date

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


def pull(bammens: Bammens, filenames: dict[str, str],
         rate_limit: timedelta = timedelta()) -> None:
    """Werkt alle lokale bestanden bij met gegevens van Bammens.

    bammens is een bron interface voor Bammens (bammensservice.nl).
    filenames is een dict met entries 'fracties' en 'clusters',
        'container_types', 'containers' en 'putten'.
    """
    start_time = datetime.now(tz=timezone.utc)
    ref_time = start_time - rate_limit

    updates = {
        'fracties': (untracked_update, bammens.fracties),
        'container_types': (tracked_update, bammens.container_types),
        'putten': (tracked_update, bammens.putten),
        'containers': (tracked_update, bammens.containers),
        'clusters': (tracked_update, bammens.clusters),
    }

    for name, (update_func, fetch) in updates.items():
        logger.debug(f'{name}...')
        filename = filenames[name]
        items = load(filename)
        if not items['last_sync'] or datetime.fromisoformat(items['last_sync']) < ref_time:
            update = update_func(items, fetch, start_time)
            items = merge(items, update, key=itemgetter('id'))
            save(filename, items)
        else:
            logger.debug(f' - skip. Recent nog bijgewerkt.')

    logger.debug('done.')
