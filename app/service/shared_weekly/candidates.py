"""Bounded, process-local, one-shot confirmation state. Never persisted."""

from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from app.service.academic_identity.contracts import IdentityRejected


@dataclass(frozen=True, slots=True)
class Ticket:
    owner: object
    value: object
    expires: float


class CandidateStore:
    def __init__(self, ttl=300, capacity=256):
        self.ttl = ttl
        self.capacity = capacity
        self._items = {}

    def put(self, owner, value):
        now = monotonic()
        self._items = {k: v for k, v in self._items.items() if v.expires > now}
        if len(self._items) >= self.capacity:
            raise IdentityRejected("candidate_capacity")
        key = str(uuid4())
        self._items[key] = Ticket(owner, value, now + self.ttl)
        return key

    def take(self, owner, key):
        item = self._items.get(key)
        if item is None or item.owner != owner:
            raise IdentityRejected("candidate_unavailable")
        del self._items[key]
        if monotonic() >= item.expires:
            raise IdentityRejected("candidate_expired")
        return item.value

    def cancel(self, owner, key):
        self.take(owner, key)
