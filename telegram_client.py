import asyncio
import logging
from pyrogram import Client, errors
from pyrogram.types import Message, Chat
from typing import Dict, List, Callable, Optional
import os
from config import API_ID, API_HASH, SESSIONS_DIR, PRIMARY_ACCOUNT_PHONE
from models import Session as DbSession, Account as DbAccount, Channel as DbChannel
import threading

logger = logging.getLogger(__name__)

class TelegramAccount:
    def __init__(self, phone: str, session_name: str):
        self.phone = phone
        self.session_name = session_name
        self.client = None
        self.is_running = False
        self.loop = None
        self.thread = None
        self.handler_callback = None

    async def start(self, callback: Callable):
        self.handler_callback = callback
        self.client = Client(
            self.session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=SESSIONS_DIR,
            in_memory=False
        )
        await self.client.start()
        self.is_running = True

        @self.client.on_message()
        async def message_handler(client, message: Message):
            async with DbSession() as db:
                channel = db.query(DbChannel).filter(
                    DbChannel.telegram_id == message.chat.id,
                    DbChannel.is_monitored == True
                ).first()
                if channel:
                    await self.handler_callback(self, message, channel)

        logger.info(f"Account {self.phone} started")
        await asyncio.Event().wait()

    async def stop(self):
        if self.client:
            await self.client.stop()
            self.is_running = False
            logger.info(f"Account {self.phone} stopped")

    def run_in_thread(self, callback):
        def _run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start(callback))
        self.thread = threading.Thread(target=_run, daemon=True)
        self.thread.start()

    # دوال الإرسال المباشر
    async def forward_message(self, chat_id: int, from_chat_id: int, message_id: int):
        try:
            await self.client.forward_messages(chat_id, from_chat_id, message_id)
            return True
        except Exception as e:
            logger.error(f"Forward error: {e}")
            return False

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int, caption: str = None):
        try:
            await self.client.copy_message(chat_id, from_chat_id, message_id, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Copy error: {e}")
            return False

    async def send_text(self, chat_id: int, text: str):
        try:
            await self.client.send_message(chat_id, text)
            return True
        except Exception as e:
            logger.error(f"Send text error: {e}")
            return False


class TelegramManager:
    def __init__(self):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.message_handler = None

    def set_message_handler(self, handler):
        self.message_handler = handler

    async def add_account(self, phone: str, session_name: str, is_primary=False):
        if phone in self.accounts:
            return False
        account = TelegramAccount(phone, session_name)
        self.accounts[phone] = account
        account.run_in_thread(self._on_message)
        async with DbSession() as db:
            existing = db.query(DbAccount).filter(DbAccount.phone == phone).first()
            if not existing:
                new_account = DbAccount(phone=phone, session_name=session_name, is_primary=is_primary)
                db.add(new_account)
                await db.commit()
        return True

    async def _on_message(self, account: TelegramAccount, message: Message, channel: DbChannel):
        if self.message_handler:
            await self.message_handler(account, message, channel)

    async def stop_all(self):
        for acc in self.accounts.values():
            await acc.stop()

    async def get_primary_account(self) -> Optional[TelegramAccount]:
        async with DbSession() as db:
            primary_db = db.query(DbAccount).filter(DbAccount.is_primary == True).first()
            if primary_db and primary_db.phone in self.accounts:
                return self.accounts[primary_db.phone]
        if self.accounts:
            return list(self.accounts.values())[0]
        return None

    async def get_channels_for_account(self, account: TelegramAccount) -> List[Chat]:
        if not account.client:
            return []
        dialogs = []
        async for dialog in account.client.get_dialogs():
            if dialog.chat.type in ["channel", "supergroup"]:
                dialogs.append(dialog.chat)
        return dialogs

    async def join_channel(self, account: TelegramAccount, username: str):
        try:
            await account.client.join_chat(username)
            return True
        except Exception as e:
            logger.error(f"Join error: {e}")
            return False

    # دوال الإرسال إلى الوجهات (تستخدم الحساب الرئيسي)
    async def forward_to_destination(self, dest, from_chat_id: int, message_id: int):
        account = await self.get_primary_account()
        if account:
            return await account.forward_message(dest.identifier, from_chat_id, message_id)
        return False

    async def copy_to_destination(self, dest, from_chat_id: int, message_id: int, caption: str = None):
        account = await self.get_primary_account()
        if account:
            return await account.copy_message(dest.identifier, from_chat_id, message_id, caption)
        return False

    async def send_text_to_destination(self, dest, text: str):
        account = await self.get_primary_account()
        if account:
            return await account.send_text(dest.identifier, text)
        return False
