import logging
from collections import Counter, defaultdict
from collections.abc import Hashable, Iterable, Sequence
from enum import Enum
from itertools import accumulate, chain, count, pairwise
from operator import itemgetter
from typing import Any, TypeVar

from orjson import dumps, loads

from local.push.tools import group_by

logger = logging.getLogger(__name__)

JSON = dict[str, Any]
H = TypeVar('H', bound=Hashable)
T = TypeVar('T')


class IndexOrder(Enum):
    UNSORTED = 0
    ASCENDING = 1
    FREQUENCY = 2


class DataJSON:
    """
    {
        "last_change": "2023-01-01T00:00:00",
        "data": [
            {...},
            ...
        ]
    }
    """
    @classmethod
    def load(cls, filename: str) -> JSON:
        try:
            with open(filename, 'rb') as f:
                return loads(f.read())
        except FileNotFoundError:
            return {
                'last_change': None,
                'data': [],
            }
    
    @classmethod
    def save(cls, filename: str, obj: JSON) -> None:
        with open(filename, 'wb') as f:
            f.write(dumps(obj))


class CompressedJSON(DataJSON):
    """
    {
        "last_change": "2023-01-01T00:00:00",
        "data": {
            "field": [...],
            ...
        }
        "raw": {
            "field": [...],
            ...
        },
        "transform": {
            "field": [...],
            ...
        }
    }
    """
    sort_order: tuple[str, ...]
    transforms: dict[str, dict[str, Sequence]] = {
        'data': {},
        'raw': {},
    }
    index_order: dict[str, IndexOrder]

    @classmethod
    def load(cls, filename: str) -> JSON:
        try:
            with open(filename, 'rb') as f:
                transformed = loads(f.read())
        except FileNotFoundError:
            return {
                'last_change': None,
                'data': [],
            }
        else:
            return cls.untransform(transformed)

    @classmethod
    def save(cls, filename: str, obj: JSON, **kwds) -> None:
        transformed = cls.transform(obj)
        kwds.update(transformed)
        with open(filename, 'wb') as f:
            f.write(dumps(kwds))
    
    @classmethod
    def transform(cls, obj: JSON) -> JSON:
        """Transformeert het data object obj naar een compacter formaat.

        obj is het JSON object met velden 'data' en 'last_change'.

        Het resultaat is een dict met velden 'last_change' (zelfde waarde als
        de input), 'data' (getransformeerde data), 'raw' (indexen) en
        'transform' (de definitie van de toegepaste transformatie).
        """
        data = combine(obj, field=cls.transforms.get('group', None))
        if cls.sort_order:
            data = sorted(data, key=itemgetter(*cls.sort_order))
        data = transpose(data)

        transformed = {
            'last_change': obj['last_change'],
            'data': data,
            'raw': {},
            'transform': cls.transforms,
        }
        indexes = transformed['raw']

        for channel in ('data', 'raw'):
            for field, transforms in cls.transforms[channel].items():
                data = transformed[channel][field]

                for i, method in enumerate(transforms):
                    if method in ('d', 'd>'):
                        fun, args = delta, ()
                    elif method == 'i':
                        data, indexes[field] = index(data, cls.index_order[field])
                        continue
                    elif method in ('j', 'j>'):
                        fun, args = join, (transforms[i + 1],)
                    elif method in ('m', 'm>'):
                        fun, args = multiply, (transforms[i + 1],)
                    elif method in ('r', 'r>'):
                        fun, args = unrepeat, ()
                    elif method in ('s', 's>'):
                        fun, args = stack, ()
                    elif method in ('x', 'x>'):
                        fun, args = crossindex, (indexes[transforms[i + 1]],)
                    else:
                        continue

                    if method.endswith('>'):
                        data = [fun(v, *args) for v in data]
                    else:
                        data = fun(data, *args)
            
                transformed[channel][field] = data
        return transformed
    
    @classmethod
    def untransform(cls, transformed: JSON) -> JSON:
        """Omgekeerde transformatie. Geeft het originele object.
        """
        obj = {
            'data': {},
            'raw': transformed['raw'].copy(),
        }
        indexes = obj['raw']

        for channel in ('raw', 'data'):
            for field, transforms in reversed(cls.transforms[channel].items()):
                data = transformed[channel][field]
                transforms = transforms[::-1]

                for i, method in enumerate(transforms):
                    if method in ('d', 'd>'):
                        fun, args = cumulative, ()
                    elif method == 'i':
                        fun, args = lookup, (indexes[field],)
                    elif method in ('j', 'j>'):
                        fun, args = split, (transforms[i - 1],)
                    elif method in ('m', 'm>'):
                        fun, args = divide, (transforms[i - 1],)
                    elif method in ('r', 'r>'):
                        fun, args = repeat, ()
                    elif method in ('s', 's>'):
                        fun, args = tear, ()
                    elif method in ('x', 'x>'):
                        fun, args = lookup, (indexes[transforms[i - 1]],)
                    else:
                        continue

                    if method.endswith('>'):
                        data = [fun(v, *args) for v in data]
                    else:
                        data = fun(data, *args)
            
                obj[channel][field] = data

        data = untranspose(obj['data'])
        data = separate(data, field=cls.transforms.get('group', None))

        kwds = {
            k: v
            for k, v in transformed.items()
            if k not in ('raw', 'data', 'transform')
        }
        kwds.update(data)
        return kwds


def combine(obj: JSON, field: str = None) -> list[JSON]:
    if field:
        return [
            {field: channel, **row}
            for channel, rows in obj.items()
            if channel != 'last_change'
            for row in rows
        ]
    else:
        return obj['data']


def crossindex(values: Sequence[H], reference: Sequence[H]) -> list[int]:
    """ [a, c, c, d, b], [a, b, c, d] -> [0, 2, 2, 3, 1] """
    index = {r: i for i, r in enumerate(reference)}
    return list(map(index.__getitem__, values))


def cumulative(values: Sequence[int]) -> list[int | None]:
    """ [4, 0, 2, 1, 2, 1, 2, 4, 3, 0] -> [2, 3, 1, 2, 0, None, 3, 3] """
    window, low = values[:2]
    a = 0
    return [
        (a := (a + d) % window) + low
        if d < window else None
        for d in values[2:]
    ]


def delta(values: Sequence[int | None]) -> list[int]:
    """ [2, 3, 1, 2, 0, None, 3, 3] -> [4, 0, 2, 1, 2, 1, 2, 4, 3, 0]
    [] -> []
    """
    try:
        low = min(v for v in values if v is not None)
        high = max(v for v in values if v is not None)
        window = high + 1 - low
    except ValueError as err:
        if len(values) == 0:
            return []
        raise err

    out = [window, low]
    a = low

    for b in values:
        if b is None:
            d = window
        else:
            d1 = (b - a) % window
            d2 = d1 - window
            d = d2 if -10 * d2 < d1 else d1
            a = b
        out.append(d)

    return out


def divide(values: list[int], factor: int) -> list[float]:
    """ [123, 7, 900] -> [12.3, 0.7, 90] """
    def f(v: int) -> float:
        try:
            return v * inv_factor
        except TypeError:
            return None
    inv_factor = 1.0 / factor
    return list(map(f, values))


def index(values: Sequence[H], order: IndexOrder = IndexOrder.UNSORTED) -> tuple[list[int], list[H]]:
    """ [a, c, a, d, b] -> [0, 1, 0, 2, 3], [a, c, d, b, None] """
    if order == IndexOrder.FREQUENCY:
        counter = Counter(values)
        mapping = {v: i for i, (v, _) in enumerate(counter.most_common())}
    elif order == IndexOrder.ASCENDING:
        mapping = {v: i for i, v in enumerate(sorted(set(values)))}
    else:
        counter = count()
        mapping = defaultdict(counter.__next__)

    ix = list(map(mapping.__getitem__, values))
    unique = list(mapping.keys())

    return ix, unique


def join(values: Sequence[str], symbol: str) -> str:
    """ ['a', 'b', 'c'] -> 'a,b,c' """
    v = symbol.join(values)
    # Accept values = [], at the cost of rejecting values = ['']
    assert not (len(values)==1 and values[0]=='')
    # assert len(v.split(symbol)) == len(values)
    return v


def lookup(values: Iterable[int], reference: Sequence[T]) -> list[T]:
    """ [0, 1, 0, 2, 3], [a, c, d, b] -> [a, c, a, d, b] """
    return [reference[i] for i in values]


def multiply(values: Sequence[float], factor: int) -> list[int]:
    """ [12.345, 0.678, 90] -> [123, 7, 900] """
    def f(v: float) -> int:
        try:
            return round(v * factor)
        except TypeError:   # unsupported operand type(s) for *: 'NoneType' and 'int'
            return None
    return list(map(f, values))


def repeat(values: tuple[Sequence[T], Sequence[int]]) -> list[T]:
    """ ([a, b, c, a], [2, 5, 1, 1]) -> [a, a, b, b, b, b, b, c, a]
    """
    tokens = chain.from_iterable([t] * c for t, c in zip(*values))
    return list(tokens)


def separate(rows: Iterable[JSON], field: str = None) -> JSON:
    def strip_field(row: JSON) -> None:
        del row[field]

    if field:
        grouped = group_by(itemgetter(field), rows)
        for _, rows in grouped.items():
            list(map(strip_field, rows))
        return grouped
    else:
        return {'data': rows}


def split(values: str, symbol: str) -> list[str]:
    """ 'a,b,c' -> ['a', 'b', 'c'] """
    if values == '':
        return []
    else:
        return values.split(symbol)


def stack(values: Sequence[Iterable[T]]) -> tuple[list[int], list[T]]:
    """ [[a, b, c], [d, e]] -> [[3, 2], [a, b, c, d, e]] """
    return (
        list(map(len, values)),
        list(chain(*values)),
    )


def tear(stacked: Sequence[Sequence[int], Sequence[T]]) -> list[T]:
    """ [[3, 2], [a, b, c, d, e]] -> [[a, b, c], [d, e]] """
    sizes, values = stacked
    positions = accumulate(sizes, initial=0)
    return [values[a:b] for a, b in pairwise(positions)]


def tokenise(values: Sequence[Sequence], symbol: str) -> list[str]:
    """ [[a, b, c], [d, e]] -> ['a,b,c', 'd,e'] """
    return list(map(symbol.join, (map(str, v) for v in values)))


def transpose(data: Sequence[JSON]) -> JSON:
    """ [{a: x, b: y}, {a: u, b: v}] -> {a: [x, u], b: [y, v]} """
    try:
        return {
            k: list(map(itemgetter(k), data))
            for k in data[0].keys()
        }
    except IndexError:
        return {}


def unique(values: Sequence[H], order: IndexOrder) -> list[H]:
    """ [a, c, d, c, b] -> [a, c, d, b]
    or:                    [a, b, c, d]
    or:                    [c, a, d, b]
    """
    if order == IndexOrder.FREQUENCY:
        return list(map(itemgetter(0), Counter(values).most_common()))
    elif order == IndexOrder.ASCENDING:
        return sorted(set(values))
    else:
        return list(set(values))


def unrepeat(values: list[T]) -> tuple[list[T], list[int]]:
    """ [a, a, b, b, b, b, b, c, a] -> ([a, b, c, a], [2, 5, 1, 1]) """
    try:
        last = values[0]
    except IndexError:
        return [[], []]

    count = 0
    repeat_values = [last]
    repeat_count = []

    for value in values:
        if value == last:
            count += 1
        else:
            repeat_count.append(count)
            repeat_values.append(value)
            last = value
            count = 1

    repeat_count.append(count)
    return repeat_values, repeat_count


def untokenise(values: Sequence[str], symbol: str) -> list[list[str]]:
    """ ['a,b,c', 'd,e'] -> [['a', 'b', 'c'], ['d', 'e']] """
    return [t.split(symbol) for t in values]


def untranspose(data: JSON) -> list[JSON]:
    """ {a: [x, u], b: [y, v]} -> [{a: x, b: y}, {a: u, b: v}] """
    keys = data.keys()
    iters = map(iter, data.values())
    return [dict(zip(keys, values)) for values in zip(*iters)]
