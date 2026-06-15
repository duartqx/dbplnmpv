#!/usr/bin/env python
from argparse import ArgumentParser, Namespace
from pathlib import Path
from sqlite3 import Connection
from typing import Final
import asyncio

from api.controllers import create, index
from application import bootstrap
from domain.entities import Anime
from repository.anime import AnimeRepository

Filename = str

DATABASE: Final[Path] = Path.home() / "Media" / "Videos" / "playlists.db"
BASEPATH: Final[Path] = Path.home() / "Media" / "Videos"


class DbMpvArgs(Namespace):
    create: list[Filename]


async def main() -> None | int:
    parser = ArgumentParser(prog="DbMpv-cli")

    parser.add_argument(
        "-c",
        "--create",
        help="Create anime entry with the argument passed as title",
        action="store",
        nargs="*",
    )

    args = parser.parse_args(namespace=DbMpvArgs())

    with Connection(DATABASE) as conn, bootstrap(AnimeRepository(conn)):
        if args.create:
            for title in args.create:
                create(Anime(title=title, path=BASEPATH / title))

            return None

        return index()


if __name__ == "__main__":
    asyncio.run(main())
