from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

H = TypeVar('H', bound=Hashable)
T = TypeVar('T')
JSON = dict[str, Any]


def group_by(key: Callable[[T], H], items: Iterable[T]) -> dict[H, list[T]]:
    h = defaultdict(list)
    for item in items:
        h[key(item)].append(item)
    return dict(h)


def last_monday(n_weeks_back: int = 0) -> datetime:
    today = datetime.now(tz=timezone.utc)
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=n_weeks_back)


# def mono(values: list[int]) -> list[int]:
#     def diff(a: int, b: int, n: int) -> int:
#         d1 = (b - a) % n
#         d2 = -((a - b) % n)
#         if d1 < 0:
#             return d1 if -10 * d1 < d2 else d2
#         else:
#             return d2 if -10 * d2 < d1 else d1

#     l = [-1]
#     p = 0
#     # n = len(values)
#     for v in values:
#         if v == p:
#             l.append(0)
#             p += 1
#         else:
#             # v < p
#             l.append(diff(v, p, p))
#             # l.append(diff(v, p, n))
#             # l.append(p - v)
#             # l.append(v + 1)
#     return l
