"""Query result cache with a fixed capacity.

Policy: least-recently-used. Reading or writing an entry makes it the most
recently used; when the cache is full, the entry unused for the longest time
is evicted. Implemented as a hash map over a doubly linked list.
"""

from __future__ import annotations


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None) -> None:
        self.key = key
        self.value = value
        self.prev: _Node | None = None
        self.next: _Node | None = None


class LRUCache:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._map: dict[str, _Node] = {}
        self._head = _Node()  # sentinel: head.next is the most recently used
        self._tail = _Node()  # sentinel: tail.prev is the least recently used
        self._head.next = self._tail
        self._tail.prev = self._head
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def __len__(self) -> int:
        return len(self._map)

    def _unlink(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _push_front(self, node: _Node) -> None:
        node.next = self._head.next
        node.prev = self._head
        self._head.next.prev = node
        self._head.next = node

    def _touch(self, node: _Node) -> None:
        self._unlink(node)
        self._push_front(node)

    def get(self, key: str):
        node = self._map.get(key)
        if node is None:
            self.misses += 1
            return None
        self.hits += 1
        return node.value

    def put(self, key: str, value) -> None:
        node = self._map.get(key)
        if node is not None:
            node.value = value
            self._touch(node)
            return
        node = _Node(key, value)
        self._map[key] = node
        self._push_front(node)
        if len(self._map) > self.capacity:
            victim = self._tail.prev
            self._unlink(victim)
            del self._map[victim.key]
            self.evictions += 1

    def keys(self) -> list[str]:
        """Keys from most to least recently used."""
        out, node = [], self._head.next
        while node is not self._tail:
            out.append(node.key)
            node = node.next
        return out

    def clear(self) -> None:
        self._map.clear()
        self._head.next = self._tail
        self._tail.prev = self._head

    def to_dict(self) -> dict:
        entries, node = [], self._head.next
        while node is not self._tail:
            entries.append([node.key, node.value])
            node = node.next
        return {
            "capacity": self.capacity,
            "entries": entries,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
        }

    @classmethod
    def from_dict(cls, raw: dict, capacity: int) -> "LRUCache":
        cache = cls(capacity)
        # Entries are stored most-recent first; re-insert oldest first.
        for key, value in reversed(raw.get("entries", [])[:capacity]):
            node = _Node(key, value)
            cache._map[key] = node
            cache._push_front(node)
        cache.hits = raw.get("hits", 0)
        cache.misses = raw.get("misses", 0)
        cache.evictions = raw.get("evictions", 0)
        return cache
