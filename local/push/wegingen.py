"""
{
    'last_change': '2023-01-01T00:00:00',
    'data': [
        {
            'systeem_id': int,
            'volgnummer': int,
            'kenteken': str,
            'datum_str': str,
            'datum_ms': int,
            'tijd_str': str,
            'tijd_ms': int,
            'weekdag_ma1': int,
            'fractie': str,
            'eerste_weging': int,
            'tweede_weging': int,
            'netto_gewicht': int,
            'lon': float,
            'lat': float,
            'afstand': float,
            'containers': [str, ...],
            'containervolume': float,
            'afvalvolume': float,
            'cluster': str,
            'adres': str,
            'buurt': str,
            'wijk': str,
            'stadsdeel': str,
        },
        ...
    ],
}
"""
import logging
from collections.abc import Callable, Iterable, Iterator, Sequence
from datetime import datetime, timedelta
from operator import itemgetter
from typing import Any

import numpy as np
from matplotlib.path import Path
from sklearn.neighbors import BallTree

from local.backup import load
from .containers import ContainersJSON
from .gebieden import GebiedenJSON
from .jsontools import CompressedJSON, IndexOrder
from .tools import group_by

logger = logging.getLogger(__name__)

JSON = dict[str, Any]

# Maximale afstand, in meters, van een weging tot de dichtstbijzijnde container.
# Wegingen met een grotere afstand krijgen geen gebieden, containervolume, etc.
# toegekend.
MAX_AFSTAND = 35


clusterfractie = itemgetter('cluster_id', 'fractie')


def clusterfractie_info(containers: Iterable[JSON]) -> dict[int, JSON]:
    def persfactor(c: JSON) -> float:
        return 2.5 if c['persend'] else 1

    adres = itemgetter('adres')
    cluster = itemgetter('cluster')
    code = itemgetter('code')
    volume = itemgetter('volume')

    grouped = group_by(clusterfractie, containers)
    return {
        cf: {
            'containers': list(map(code, cc)),
            'containervolume': sum(map(volume, cc)),
            'afvalvolume': sum(persfactor(c) * volume(c) for c in cc),
            'cluster': cluster(cc[0]),
            'adres': adres(cc[0]),
        }
        for cf, cc in grouped.items()
    }


def dichtstbijzijnde_container(containers: Sequence[JSON],
                               wegingen: Sequence[JSON],
                               ) -> Iterator[tuple[float, JSON]]:
    """Geeft voor elke weging de afstand en dichtstbijzijnde container.
    """
    def lat_lon_rad(items: Sequence[JSON]) -> np.ndarray:
        return np.deg2rad(np.array(list(map(lat_lon, items)), dtype=float))
    
    fractie = itemgetter('fractie')
    lat_lon = itemgetter('lat', 'lon')
    has_lat = itemgetter('lat')

    containers_per_fractie = group_by(fractie, list(filter(has_lat, containers)))
    tree_per_fractie = {f: BallTree(lat_lon_rad(cc), metric='haversine')
                        for f, cc in containers_per_fractie.items()}

    # The Earth radius at sea level in Amsterdam, in metres.
    # See: https://rechneronline.de/earth-radius/
    earth_radius = 6_364_763

    for w, ll in zip(wegingen, lat_lon_rad(wegingen)):
        try:
            f = fractie(w)
            d, ix = tree_per_fractie[f].query(ll.reshape(1, -1), k=1, sort_results=False)
        except (KeyError, ValueError):
            yield None, None
        else:
            yield d.item() * earth_radius, containers_per_fractie[f][ix.item()]


def datum_format(datum: datetime) -> str:
    dagen = ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo']
    maanden = ['jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
    return f'{dagen[datum.weekday()]} {datum.day} {maanden[datum.month - 1]}. \'{datum.year % 100}'


def datum_ms(datum: datetime) -> int:
    return int(datum.timestamp() * 1000)
    

def gewicht(w: str | None) -> int | None:
    try:
        return int(w)
    except ValueError:
        # e.g. weegsysteem 407 op 1 maart 2023. Weging met volgnummer 48451.
        # -> NetWeight = 52.3895. Dit klopt niet. Dat is een GPS coordinaat.
        # Datapunt neemt de waarde wel over (https://api.data.amsterdam.nl/v1/huishoudelijkafval/weging/?datumWeging=2023-03-01&volgnummer=48451)
        # Is een keuze.
        return None


def tijd_format(datum: datetime) -> str:
    return f'{datum.hour}:{datum.minute:02d}'


def tijd_ms(datum: datetime) -> int:
    return datum_ms(datum) % (24 * 60 * 60 * 1000)


def weekdag_ma1(datum: datetime) -> str:
    # str is nodig voor de UIX.
    return str((datum.weekday() + 1) % 7)


def weging_datum(weging: JSON) -> datetime:
    return datetime.fromisoformat(f'{weging["Date"]}T{weging["Time"]}Z')


class Polylabel:
    @classmethod
    def _group(cls, gebieden: Sequence[JSON], points: np.ndarray, indices: np.ndarray,
               callback: Callable[[JSON, np.ndarray], Any]) -> None:
        """Roept `callback(gebied, indices)` aan voor elke polygoon zonder kinderen.
        De indices zijn van de punten die in het polygoon liggen.

        `gebieden` is een lijst met dicts. Elk dict heeft een sleutel 'poly' met
        coordinaten van een polygoon. Het dict mag ook een sleutel '_children'
        hebben, welke dan een lijst met nieuwe van zulke objecten geeft.
        Zodoende kan gebieden een boomstructuur geven, maar het kan dus ook een
        platte lijst zijn alnaargelang wat de toepassing vergt.
        """
        for gebied in gebieden:
            poly = Path(list(zip(gebied['lon'], gebied['lat'])))
            contained = poly.contains_points(points)
            contained_indices = indices[contained]

            if '_children' in gebied and len(gebied['_children']):
                cls._group(gebied['_children'], points[contained],
                           contained_indices, callback)
            else:
                callback(gebied, contained_indices)

            points = points[~contained]
            indices = indices[~contained]

    @staticmethod
    def gebieden_topo(gebieden: JSON) -> list[JSON]:
        stadsdelen = gebieden['stadsdelen']
        wijken = gebieden['wijken']
        buurten = gebieden['buurten']

        for w in wijken:
            w['_children'] = [b for b in buurten if b['ligt_in'] == w['naam']]
        for s in stadsdelen:
            s['_children'] = [w for w in wijken if w['ligt_in'] == s['naam']]
            for w in s['_children']:
                for b in w['_children']:
                    b['ligt_in_stadsdeel'] = s['naam']

        return stadsdelen

    @classmethod
    def label_containers(cls, topo: Sequence[JSON], containers: Sequence[JSON]) -> list[JSON]:
        """Geeft voor elke container het kleinste omsluitende gebied (buurt).
        """
        def label(buurt: JSON, indices: np.array) -> None:
            for ix in indices:
                labels[ix] = buurt

        n = len(containers)
        labels = [{} for _ in range(n)]

        lon_lat = list(map(itemgetter('lon', 'lat'), containers))
        lon_lat = np.array(lon_lat, dtype=float)
        indices = np.flatnonzero(~(lon_lat[:, 0] == None))

        cls._group(topo, lon_lat, indices, label)
        return labels


class WegingenJSON(CompressedJSON):
    sort_order = ('systeem_id', 'datum_ms')
    transforms = {
        'data': {
            'systeem_id': ['i', 'r'],               # UNSORTED
            'kenteken': ['i', 'r'],                 # UNSORTED
            'fractie': ['i', 'r'],                  # UNSORTED
            'volgnummer': ['d', 'r'],
            'lat': ['m', 1_000_000, 'd'],
            'lon': ['m', 1_000_000, 'd'],
            'datum_ms': ['m', 1.0 / 1_000, 'd'],
            'tijd_ms': ['m', 1.0 / 1_000, 'd'],
            'datum_str': ['i', 'r'],                # ASCENDING
            'tijd_str': ['i', 'd'],                 # ASCENDING
            'weekdag_ma1': ['i', 'r'],
            'eerste_weging': ['i'],                 # FREQUENCY
            'tweede_weging': ['i'],                 # FREQUENCY
            'netto_gewicht': ['i'],                 # FREQUENCY
            'afstand': ['m', 10],
            'containers': ['j>', ',', 'i', 'd'],    # UNSORTED
            'containervolume': ['i', 'r'],          # FREQUENCY
            'afvalvolume': ['i', 'r'],              # FREQUENCY
            'cluster': ['i', 'd'],                  # UNSORTED
            'adres': ['i', 'd'],                    # UNSORTED
            'buurt': ['i', 'r'],                    # UNSORTED
            'wijk': ['i', 'r'],                     # UNSORTED
            'stadsdeel': ['i', 'r'],                # UNSORTED
        },
        'raw': {
            'kenteken': ['j', '@'],
            # 'fractie': ['j', '@'],
            'datum_str': ['j', '@'],
            'tijd_str': ['j', '@'],
            # 'weekdag_ma1': ['j', '@'],
            'containers': ['j', '@'],
            'cluster': ['j', '@'],
            'adres': ['j', '@'],
            'buurt': ['j', '@'],
            'wijk': ['j', '@'],
            'stadsdeel': ['j', '@'],
        },
    }
    index_order = {
        'systeem_id': IndexOrder.UNSORTED,
        'kenteken': IndexOrder.UNSORTED,
        'fractie': IndexOrder.UNSORTED,
        'datum_str': IndexOrder.ASCENDING,
        'tijd_str': IndexOrder.ASCENDING,
        'weekdag_ma1': IndexOrder.ASCENDING,
        'eerste_weging': IndexOrder.FREQUENCY,
        'tweede_weging': IndexOrder.FREQUENCY,
        'netto_gewicht': IndexOrder.FREQUENCY,
        'containers': IndexOrder.UNSORTED,          # FREQUENCY?
        'containervolume': IndexOrder.FREQUENCY,
        'afvalvolume': IndexOrder.FREQUENCY,
        'cluster': IndexOrder.UNSORTED,
        'adres': IndexOrder.UNSORTED,
        'buurt': IndexOrder.UNSORTED,
        'wijk': IndexOrder.UNSORTED,
        'stadsdeel': IndexOrder.UNSORTED,
    }


def push(file_out: str, delta_file_out: str, data_files: dict[str, str],
         web_files: dict[str, str], after: datetime = None) -> None:
    logger.debug('wegingen...')

    # SystemId, VehicleReg, LatestWeighDate
    # Seq, Date, Time, FractionId, FirstWeight, SecondWeight, NetWeight, Latitude, Longitude, SystemId
    input_wagens = load(data_files['wagens'])
    input_wegingen = load(data_files['wegingen'])
    output_wegingen = WegingenJSON.load(file_out)

    if input_wegingen['last_change'] == output_wegingen['last_change']:
        logger.debug(' - skip. Geen veranderingen sinds laatste keer.')
        return

    containers = ContainersJSON.load(web_files['containers'])['data']
    gebieden = GebiedenJSON.load(web_files['gebieden'])
    topo = Polylabel.gebieden_topo(gebieden)
    container_buurt = Polylabel.label_containers(topo, containers)
    cf_info = clusterfractie_info(containers)

    for c, b in zip(containers, container_buurt):
        c['_buurt'] = b
        c['_cf'] = cf_info[clusterfractie(c)]

    # - pak alleen nieuwe input wegingen
    # - match wegingen <-> containers
    # - apply container data
    # - save.

    kenteken = {
        w['SystemId']: w['VehicleReg']
        for w in input_wagens['data']
    }

    def input_weging_key(w: JSON) -> tuple[int, int]:
        return w['SystemId'], int(w['Seq'])
    
    def is_recent() -> Callable[[datetime], bool]:
        if after:
            def is_after(v: datetime) -> bool:
                return v >= after
            return is_after
        else:
            def just_true(_: datetime) -> bool:
                return True
            return just_true

    # input_weging_key = itemgetter('SystemId', 'Seq')
    output_weging_key = itemgetter('systeem_id', 'volgnummer')
    bekend = set(map(output_weging_key, output_wegingen['data']))
    recent = is_recent()
    nieuwe_wegingen = [
        {
            'systeem_id': w['SystemId'],
            'volgnummer': int(w['Seq']),
            'kenteken': kenteken.get(w['SystemId'], ''),
            'datum_str': datum_format(dt),
            'datum_ms': datum_ms(dt),
            'tijd_str': tijd_format(dt),
            'tijd_ms': tijd_ms(dt),
            'weekdag_ma1': weekdag_ma1(dt),
            'fractie': w['FractionId'],
            'eerste_weging': gewicht(w['FirstWeight']),
            'tweede_weging': gewicht(w['SecondWeight']),
            'netto_gewicht': gewicht(w['NetWeight']),
            'lon': float(w['Longitude']) if w['Longitude'] else None,
            'lat': float(w['Latitude']) if w['Latitude'] else None,
        }
        for dt, w in (
            (weging_datum(w), w)
            for w in input_wegingen['data']
            if input_weging_key(w) not in bekend
        )
        if recent(dt)
    ]

    matching_containers = dichtstbijzijnde_container(containers, nieuwe_wegingen)

    for w, (d, c) in zip(nieuwe_wegingen, matching_containers):
        w.update({
            'afstand': d,
            'containers': [],   # c['_cf']['containers'] if c else [],
            'containervolume': None,
            'afvalvolume': None,
            'cluster': '',
            'adres': '',
            'buurt': '',
            'wijk': '',
            'stadsdeel': '',
        } if d is None or d > MAX_AFSTAND else {
            'afstand': d,
            'containers': c['_cf']['containers'],
            'containervolume': c['_cf']['containervolume'],
            'afvalvolume': c['_cf']['afvalvolume'],
            'cluster': c['_cf']['cluster'],
            'adres': c['_cf']['adres'],
            'buurt': c['_buurt']['naam'],
            'wijk': c['_buurt']['ligt_in'],
            'stadsdeel': c['_buurt']['ligt_in_stadsdeel'],
        })
    
    kale_wegingen = [w for w in nieuwe_wegingen if w['stadsdeel'] == '']
    weging_buurt = Polylabel.label_containers(topo, kale_wegingen)

    for w, b in zip(kale_wegingen, weging_buurt):
        if b:
            w['buurt'] = b['naam']
            w['wijk'] = b['ligt_in']
            w['stadsdeel'] = b['ligt_in_stadsdeel']

    WegingenJSON.save(delta_file_out, {
        'last_change': input_wegingen['last_change'],
        'data': nieuwe_wegingen,
    }, last_delta=output_wegingen['last_change'])

    output_wegingen['data'].extend(nieuwe_wegingen)
    output_wegingen['last_change'] = input_wegingen['last_change']

    if after:
        theta = datum_ms(after)
        output_wegingen['data'] = [w for w in output_wegingen['data']
                                   if w['datum_ms'] > theta]

    WegingenJSON.save(file_out, output_wegingen)
    logger.debug(' - done.')


# def filter_wegingen(file_out: str, file_in: str, delta: timedelta) -> None:
#     logger.debug('filter wegingen')

#     current = WegingenJSON.load(file_in)
#     previous = WegingenJSON.load(file_out)

#     if current['last_change'] == previous['last_change']:
#         logger.debug(' - skip. Geen verandering sinds laatste keer.')
#         return

#     last_change = datetime.fromisoformat(current['last_change'])
#     include_after = last_change - delta
#     theta = datum_ms(include_after)

#     current['data'] = [w for w in current['data'] if w['datum_ms'] > theta]

#     WegingenJSON.save(file_out, current)
#     logger.debug(' - done.')