import logging
import asyncio
from typing import List, Dict, Any
from models import Destination, Keyword, Session as DbSession, Post
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pyrogram.errors import FloodWait, RPCError

logger = logging.getLogger(__name__)

class RulesEngine:
    def __init__(self):
        self.keywords_include = []
        self.keywords_exclude = []
        self.telegram_manager = None   # سيتم تعيينه من gui

    def set_telegram_manager(self, manager):
        self.telegram_manager = manager

    async def load_keywords(self):
        async with DbSession() as db:
            keywords = db.query(Keyword).all()
            self.keywords_include = [(kw.text, kw.priority) for kw in keywords if kw.is_include]
            self.keywords_exclude = [kw.text for kw in keywords if not kw.is_include]

    async def evaluate_post(self, post: Post, post_text: str) -> Dict[str, Any]:
        result = {
            "should_send": True,
            "priority": 0,
            "matched_keywords": [],
            "urgent": post.is_urgent,
            "importance": post.ai_importance,
            "category": post.ai_category,
        }
        text_lower = post_text.lower()
        for kw in self.keywords_exclude:
            if kw.lower() in text_lower:
                result["should_send"] = False
                return result
        max_priority = 0
        for kw, prio in self.keywords_include:
            if kw.lower() in text_lower:
                result["matched_keywords"].append(kw)
                if prio > max_priority:
                    max_priority = prio
        result["priority"] = max_priority
        if post.is_urgent:
            result["priority"] = max(result["priority"], 8)
        return result

    async def route_to_destinations(self, post: Post, evaluation: Dict, destinations: List[Destination]):
        destinations_to_send = []
        for dest in destinations:
            rules = dest.get_rules()
            if not rules:
                destinations_to_send.append(dest)
                continue
            send = True
            if "categories" in rules and evaluation["category"] not in rules["categories"]:
                send = False
            if "min_importance" in rules and evaluation["importance"] < rules["min_importance"]:
                send = False
            if "only_urgent" in rules and rules["only_urgent"] and not evaluation["urgent"]:
                send = False
            if send:
                destinations_to_send.append(dest)
        return destinations_to_send

    async def send_to_destination(self, dest: Destination, post: Post, from_chat_id: int, message_id: int):
        """إرسال المنشور إلى الوجهة حسب طريقة الإرسال المحددة"""
        if not self.telegram_manager:
            logger.error("TelegramManager not set")
            return False
        method = dest.send_method
        try:
            if method == "forward":
                # تحويل مباشر (أسرع)
                return await self.telegram_manager.forward_to_destination(dest, from_chat_id, message_id)
            elif method == "copy":
                # نسخ (يمكن تعديل النص لاحقاً)
                caption = post.translated_text if post.translated_text else post.text
                return await self.telegram_manager.copy_to_destination(dest, from_chat_id, message_id, caption)
            elif method == "text_only":
                # إرسال نص فقط (بدون وسائط)
                text = post.translated_text if post.translated_text else post.text
                return await self.telegram_manager.send_text_to_destination(dest, text)
            else:
                logger.warning(f"Unknown send_method {method} for {dest.name}")
                return False
        except FloodWait as e:
            logger.warning(f"Flood wait {e.x} seconds for {dest.identifier}")
            await asyncio.sleep(e.x)
            return await self.send_to_destination(dest, post, from_chat_id, message_id)  # retry
        except Exception as e:
            logger.error(f"Send error to {dest.identifier}: {e}")
            return False

rules_engine = RulesEngine()
