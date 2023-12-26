#!/usr/bin/env python
import datetime
import logging
import os
import random
import asyncio
from functools import partial
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import sqlite3

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

main_db_file = "main.db"

conn: sqlite3.Connection = None
cursor: sqlite3.Cursor = None


async def to_thread(f, *args, **kwargs) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(f, *args, **kwargs))


def create_connection(db_file=main_db_file) -> None:
    try:
        global conn
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except sqlite3.Error as e:
        logging.exception("Failed to create connection", exc_info=e)
        return


def check_dick(username: str) -> tuple[str, datetime.date, int]:
    res = conn.execute(
        f'select id, last_update_date, dick_length from dicks where username = "{username}"',
    )
    res = res.fetchone()

    return res


def dick_random() -> int:
    luck = random.randint(1, 20)

    if luck == 20:
        return 20
    if luck == 1:
        return -20

    return random.randint(-8, 10)


def reply_text_for_change(change: int) -> str:
    if change == 0:
        return "твій песюн не виріс :'("
    if change < 0:
        return f"твій песюн зменшився на {abs(change)} см"

    return f"твій песюн збільшився на {change} см"


def update_dick(username: str) -> None:
    reply_text = None
    dick_data = check_dick(username)

    if dick_data is None:
        last_update_date = str(datetime.date.today())
        dick_length = 0
        new_dick = True
        change_dick = True
    else:
        new_dick = False
        dick_id, last_update_date, dick_length = dick_data

        if last_update_date == str(datetime.date.today()):
            reply_text = "ти сьогодні вже грав"
            change_dick = False
        else:
            last_update_date = str(datetime.date.today())
            change_dick = True

    if change_dick:
        change = dick_random()
        dick_length += change
        reply_text = f"{reply_text_for_change(change)} і дорівнює {dick_length} см"

        if new_dick:
            cursor.execute(
                f"""
                insert into dicks (username, last_update_date, dick_length)
                values ("{username}", "{last_update_date}", "{dick_length}");
                """
            )
        else:
            cursor.execute(
                f"""
                update dicks set
                    last_update_date="{last_update_date}",
                    dick_length={dick_length}
                where id = {dick_id}
                """
            )

        conn.commit()

    return reply_text


async def dick_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username

    if username is None:
        reply_text = "Стартани бота, довірся йому"
    else:
        reply_text = await to_thread(update_dick, username)

    user = update.effective_user
    await update.message.reply_html(
        f"{user.mention_html()}, {reply_text}",
        reply_to_message_id=update.message.id,
    )


async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        """Дає рандом довжину пеніса раз в день""",
        reply_to_message_id=update.message.id,
    )

    await to_thread(check_dick, update.message.chat.username)


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def main() -> None:
    create_connection()

    if conn is None:
        print("No db Connection :(( ")
        return

    global cursor

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dicks (
                id integer PRIMARY KEY AUTOINCREMENT,
                username text NOT NULL,
                last_update_date text NOT NULL,
                dick_length integer NOT NULL
            );
            """
        )
        conn.commit()
    except sqlite3.Error as e:
        logging.exception("Failed to start", exc_info=e)
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dick", dick_command))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
