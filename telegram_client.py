    async def forward_message(self, chat_id: int, from_chat_id: int, message_id: int):
        """إعادة توجيه رسالة مباشرة دون حفظ الوسائط"""
        try:
            await self.client.forward_messages(chat_id, from_chat_id, message_id)
            return True
        except Exception as e:
            logger.error(f"Forward error: {e}")
            return False

    async def copy_message(self, chat_id: int, from_chat_id: int, message_id: int, caption: str = None):
        """نسخ الرسالة مع إمكانية تعديل النص"""
        try:
            await self.client.copy_message(chat_id, from_chat_id, message_id, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Copy error: {e}")
            return False

    async def send_text(self, chat_id: int, text: str):
        """إرسال نص فقط"""
        try:
            await self.client.send_message(chat_id, text)
            return True
        except Exception as e:
            logger.error(f"Send text error: {e}")
            return False
