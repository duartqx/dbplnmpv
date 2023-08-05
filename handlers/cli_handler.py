import os
import subprocess

from argparse import Namespace
from pathlib import Path
from typing import TypeAlias

from persistence.dbplmpv import DbPlMpv
from service import (
    read_all,
    read_filtered,
    update,
)

Rows: TypeAlias = dict[str, dict[str, str | int]]


async def execute_dmenu(
    input_string: str, cmd: tuple[str, ...] = ("dmenu", "-i", "-l", "20")
) -> str:
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    output, _ = process.communicate(input=input_string.rstrip("\n").encode())
    return output.decode().rstrip("\n")


async def play_on_mpv(path: str) -> None:
    subprocess.run(("mpv", "--osc", "--fs", path.strip("\n")))


async def notify_send(msg: str) -> None:
    subprocess.run(("notify-send", msg))


async def choose_play_and_maybe_update(
    db: DbPlMpv, rows: Rows, upd: bool = True
) -> None:
    chosen: str = await execute_dmenu("\n".join(rows))
    chosen_row: dict[str, str | int] = rows.get(chosen, {})
    if not chosen_row:
        return
    await play_on_mpv(str(chosen_row["path"]))
    if upd:
        await update(db, ctx=Namespace(**chosen_row))


async def choose_and_update(db: DbPlMpv, rows: Rows) -> None:
    chosen: str = await execute_dmenu("\n".join(rows))
    chosen_row: dict[str, str | int] = rows.get(chosen, {})
    if not chosen_row:
        return
    await update(db, ctx=Namespace(**chosen_row))
    await notify_send(f"Updated watched status for {chosen}")


async def choose_and_delete(db: DbPlMpv, rows: Rows) -> None:
    chosen: str = await execute_dmenu("\n".join(rows))
    chosen_row: dict[str, str | int] = rows.get(chosen, {})

    if not chosen_row:
        return

    ask_confirmation_of_deletion: str = await execute_dmenu(
        "Yes\nNo",
        cmd=(
            "dmenu",
            "-i",
            "-p",
            f"Continue and DELETE '{chosen_row['title']}'?",
        ),
    )

    if ask_confirmation_of_deletion == "No":
        return

    try:
        os.remove(str(chosen_row["path"]))
        db.delete((int(chosen_row["id"]),))
        await notify_send(
            f"'{chosen_row['title']}' has been successfully deleted."
        )
    except (FileNotFoundError, PermissionError):
        await notify_send(f"'{chosen_row['title']}' could not be deleted.")


async def cli_handler(db: DbPlMpv, args: Namespace) -> None:
    # Checks if the video file still exists in the playlist folder, if not
    # then updates its row to deleted=1
    if args.read or args.readall:
        db.delete(
            tuple(
                (
                    int(row["id"])
                    for row in db.read_all()
                    if not Path(f"{row['path']}").is_file()
                )
            )
        )

    if args.read:
        rows: Rows = await read_filtered(db, ctx=args)
        await choose_play_and_maybe_update(db, rows, upd=True)
    elif args.readall and args.update:
        rows: Rows = await read_all(db, ctx=args)
        await choose_and_update(db, rows)
    elif args.readall and args.delete:
        rows: Rows = await read_all(db, ctx=args)
        await choose_and_delete(db, rows)
    elif args.readall:
        rows: Rows = await read_all(db, ctx=args)
        await choose_play_and_maybe_update(db, rows, upd=False)
    elif args.update:
        await update(db, ctx=args)
    elif args.create:
        db.create(
            entry=args.create,
            collection=args.collection,
            watched=args.watched,
        )
