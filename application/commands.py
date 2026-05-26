from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Generic,
    Literal,
    Optional,
    TypeVar,
    cast,
    override,
)

from application import MessageBus, bootstrap
from application.services import dmenu, mpv
from domain.entities import Anime
from domain.events import WasCreated, WasUpdated, WereDeleted
from repository.query import AnimeQuery, AnimeQueryOrder

IndexCommands = Literal["Watch", "Update", "Watched", "Delete", "Purge", ""] | str


class Command[T](ABC):
    bus: MessageBus = field(init=False)

    def __post_init__(self) -> None:
        self.bus = bootstrap()

    @property
    def menu(self):
        return dmenu

    @property
    def player(self):
        return mpv

    @abstractmethod
    def execute(self) -> T: ...


@dataclass
class Index(Command[IndexCommands]):
    choices = ["Watch", "Update", "Watched", "Delete", "Purge"]

    @override
    def execute(self) -> IndexCommands:
        command: IndexCommands = self.menu(
            "\n".join(self.choices).encode(), position="horizontal"
        )
        return command


@dataclass
class ChooseAndWatch(Command[Optional[Anime]]):
    watched: bool
    query: AnimeQuery = field(default_factory=AnimeQuery)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.watched:
            self.query = AnimeQuery(
                watched=True, order=AnimeQueryOrder(direction="DESC")
            )

    @override
    def execute(self) -> Optional[Anime]:
        with self.bus.repository as repository:
            options: dict[str, Anime] = {
                anime.title: anime
                for anime in cast(list[Anime], repository.read(self.query))
            }

        choice = self.menu("\n".join(options.keys()).encode())

        if choice != "" and choice in options:

            anime = options[choice]

            self.player(str(anime.path))

            return anime

        return None


@dataclass
class ChooseWatchAndUpdate(ChooseAndWatch):
    query: AnimeQuery = field(default_factory=lambda: AnimeQuery(watched=False))

    @override
    def execute(self) -> Optional[Anime]:
        anime: Optional[Anime] = super().execute()

        if anime is not None and anime.id is not None:
            with self.bus.repository as repository:

                repository.update(obj=anime)

                self.bus.add(WasUpdated(anime=anime))

        return anime


@dataclass
class ChooseAndUpdate(Command):
    query: AnimeQuery = field(
        default_factory=lambda: AnimeQuery(order=AnimeQueryOrder(direction="DESC"))
    )

    def _title_with_status(self, anime: Anime) -> str:
        status: Literal["", "[WATCHED] "] = ""
        if anime.watched:
            status = "[WATCHED] "
        return "".join([status, anime.title])

    @override
    def execute(self) -> Optional[Anime]:
        with self.bus.repository as repository:
            options: dict[str, Anime] = {
                self._title_with_status(anime): anime
                for anime in cast(list[Anime], repository.read(self.query))
            }

            choice = self.menu("\n".join(options.keys()).encode())

            if choice != "" and choice in options:
                anime = options[choice]

                repository.update(obj=anime)

                self.bus.add(WasUpdated(anime=anime))

                return anime


@dataclass
class Delete(Command):
    query: AnimeQuery = field(
        default_factory=lambda: AnimeQuery(order=AnimeQueryOrder(direction="DESC"))
    )

    @override
    def execute(self) -> None:
        with self.bus.repository as repository:
            options: dict[str, Anime] = {
                anime.title: anime
                for anime in cast(list[Anime], repository.read(self.query))
            }

            choice = self.menu("\n".join(options.keys()).encode())

            if choice != "" and choice in options:
                anime = [options[choice]]

                repository.delete(objs=anime)

                self.bus.add(WereDeleted(animes=anime))


@dataclass
class Purge(Command):
    @override
    def execute(self) -> None:
        with self.bus.repository as repository:

            animes = [
                anime
                for anime in cast(list[Anime], repository.read())
                if anime.path.parent.exists() and not anime.path.exists()
            ]

            repository.delete(objs=animes)

            self.bus.add(WereDeleted(animes=animes))


@dataclass
class Create(Command):
    anime: Anime

    @override
    def execute(self) -> int:
        with self.bus.repository as repository:

            repository.insert(self.anime)

            self.bus.add(WasCreated(anime=self.anime))

        return self.anime.id or 0
