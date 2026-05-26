from queue import Queue
from typing import Optional, Self

from application.registry import registry, Registry
from application.listeners import *
from domain.events import Event
from repository import Repository


class MessageBus:
    def __init__(self, repository: Repository, registry: Registry = registry) -> None:
        self.repository = repository
        self.registry = registry
        self.queue: Queue[Event] = Queue()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        while self.queue.qsize():
            event = self.queue.get()
            self.handle(event)

    def add(self, event: Event) -> Self:
        self.queue.put(event)
        return self

    def handle(self, event: Event):
        for listener in self.registry.get(event.__class__):
            listener(event)


bus: Optional[MessageBus] = None


def bootstrap(repository: Optional[Repository] = None) -> MessageBus:
    global bus

    if bus is None:

        assert repository is not None, "Repository is required"

        bus = MessageBus(repository=repository)

    return bus
