import base64
import json
import zlib
from typing import Optional

import aiohttp
from api.schemas import (
    DataGeneratedMessage,
    DataThreadMessageRequest,
    DataThreadRequest,
)
from backends.base import BaseDirectBackend
from instagrapi import Client
from instagrapi.types import DirectMessage, DirectThread
from loguru import logger


class InstagrapiBackend(BaseDirectBackend):
    def __init__(self, session_url: str, instagram_login: str) -> None:
        self._session_url = session_url
        self.instagram_login = instagram_login
        self.client = None

    @staticmethod
    def _unpack_session(packed_session: str) -> dict:
        """Unpacks a session that has been packed using base64 encoding and zlib compression.

        Args:
            packed_session (str): The packed session string.

        Returns:
            dict: The unpacked session as a dictionary.

        Raises:
            RuntimeError: If the session fails to unpack.
        """
        try:
            decoded_session = base64.b64decode(packed_session)
            decompressed_session = zlib.decompress(decoded_session)
            return json.loads(decompressed_session)
        except Exception as e:
            logger.error("Failed to unpack session")
            logger.error(str(e))
            raise RuntimeError(f"Failed to unpack session: {e}")

    async def _get_client(self) -> Client:
        """
        Retrieves a Client object for the specified Instagram login.

        Returns:
            Client: The Client object with the specified settings and optional proxy.

        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self._session_url}/{self.instagram_login}") as response:
                response.raise_for_status()
                response = await response.json()
        session = self._unpack_session(response["session"])

        return Client(settings=session, proxy=response.get("proxy"))

    async def get_all_threads(self) -> list[Optional[DataThreadRequest]]:
        self.client = await self._get_client()
        raw_threads_from_requests_mailbox = self.client.direct_pending_inbox()
        raw_threads = self.client.direct_threads()

        threads = await self.format_raw_threads(raw_threads + raw_threads_from_requests_mailbox)
        return threads

    async def send_message(self, message: DataGeneratedMessage) -> None:
        self.client = await self._get_client()
        self.client.direct_send(text=message.text, thread_ids=[message.thread_instagram_id_from_instagrapi])

    async def format_raw_threads(self, raw_threads: list[DirectThread]) -> list[DataThreadRequest]:
        threads = []
        for raw_thread in raw_threads:
            messages = await self.format_raw_messages(raw_thread.messages, raw_thread.users[0].pk)
            thread = DataThreadRequest(
                instagram_id_from_instagrapi=raw_thread.id,
                thread_to_user_id_from_instagrapi=raw_thread.users[0].pk,
                thread_to_username=raw_thread.users[0].username,
                messages=messages,
            )
            threads.append(thread)
        return threads

    @staticmethod
    async def format_raw_messages(
        raw_messages: list[DirectMessage], recipient_pk: str
    ) -> list[DataThreadMessageRequest]:
        messages = []
        for raw_message in raw_messages:
            message = DataThreadMessageRequest(
                instagram_id_from_instagrapi=raw_message.id,
                created_at=raw_message.timestamp.timestamp(),
                sender="blogger" if raw_message.user_id != recipient_pk else "external_user",
                instagram_user_id_from_instagrapi=raw_message.user_id,
                item_type=raw_message.item_type,
                text=raw_message.text,
                link=raw_message.link,
            )
            messages.append(message)
        return messages
