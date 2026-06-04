import asyncio
import os
from typing import cast

import telegram
from dotenv import load_dotenv
from telegram import Bot, BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()


class TelegramBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(os.getenv('TELEGRAM_TOKEN')).build()
        self.bot = cast(Bot, self.application.bot)

        force_start_handler = CommandHandler('force_start', self.force_start)
        self.application.add_handler(force_start_handler)

        self.application.post_init = self.setup_bot
        self.application.run_polling()

    async def setup_bot(self, app):
        await self.bot.set_my_commands(
            [
                BotCommand('force_start', 'ластовенькє урокє'),
            ]
        )

    async def force_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) and (context.args[0] not in ['l', 'w'] or context.args[1] not in ['0', '1']):
            await update.message.reply_text(
                'Usage: /force_start <device(l/w)> <recording(0/1)>\nDefault: linux with no recording'
            )
            return

        recording = bool(int(context.args[1])) if len(context.args) else False
        self.bus.emit('force-start-last-lesson', recording)
        await update.message.reply_text(
            f'Force starting lesson on a <b>Windows {"w recording 🎥" if recording else ""}</b>',
            parse_mode=telegram.constants.ParseMode.HTML,
        )

    def send_message(self, text):
        asyncio.run(
            self.bot.sendMessage(os.getenv('TELEGRAM_CHAT_ID'), text, parse_mode=telegram.constants.ParseMode.HTML)
        )
