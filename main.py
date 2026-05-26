#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from pathlib import Path
from sqlite3 import Connection
from typing import Any, Final, cast
import asyncio

from api.controllers import create, index
from application import bootstrap
from domain.entities import Anime
from repository.anime import AnimeRepository

Filename = str

DATABASE: Final[Path] = Path.home() / ".local" / "share" / "playlists.db"
BASEPATH: Final[Path] = Path.home() / "Media" / "Videos"


class DbMpvArgs(Namespace):
    create: list[Filename]


def get_options() -> tuple[dict[str, Any], ...]:
    return (
        {
            "arg": ("-c", "--create"),
            "help": "Create anime entry with the argument passed as title",
            "action": "store",
            "nargs": "*",
        },
    )


def get_args() -> DbMpvArgs:
    """
    Builds and returns main's parsed command line arguments

    OPTIONS:
        -c, --create: Filename
    """
    parser = ArgumentParser(prog="DbMpv-cli")

    for arg in get_options():
        parser.add_argument(*arg.pop("arg"), **arg)

    return parser.parse_args(namespace=DbMpvArgs())


async def main() -> None | int:
    args: DbMpvArgs = get_args()

    def create_multiple_anime_entries():
        for title in args.create:
            create(Anime(title=title, path=BASEPATH / title))

    with Connection(DATABASE) as conn, bootstrap(AnimeRepository(conn)):
        if args.create:
            return create_multiple_anime_entries()

        return index()


if __name__ == "__main__":
    asyncio.run(main())
