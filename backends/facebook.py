from datetime import datetime

from api.schemas import (
    DataGeneratedMessage,
    DataThreadMessageRequest,
    DataThreadRequest,
)
from backends.base import BaseDirectBackend
from pyfacebook import GraphAPI


class FacebookBackend(BaseDirectBackend):
    def __init__(self, access_token: str, page_id: str) -> None:
        self.page_id: str = page_id
        self.access_token: str = access_token
        self.client: GraphAPI = self._get_client()

    def _get_client(self):
        return GraphAPI(access_token=self.access_token)

    async def get_raw_conversations(self) -> list[dict]:
        """
        Docs for response from Facebook is here:
        https://developers.facebook.com/docs/graph-api/reference/page/conversations/
        """
        conversations = self.client.get_connection(self.page_id, "conversations", platform="instagram")["data"]
        return conversations

    async def get_all_threads(self) -> list[DataThreadRequest]:
        raw_conversations = await self.get_raw_conversations()
        threads = await self.format_raw_conversations_to_threads(raw_conversations)
        return threads

    async def send_message(self, message: DataGeneratedMessage) -> None:
        """
        Docs for response from Facebook is here:
        https://developers.facebook.com/docs/graph-api/reference/page/messages/
        """
        self.client.post_object(
            object_id=self.page_id,
            connection="messages",
            data={
                "recipient": f'{{"id": "{message.recipient_instagram_id_from_official_graph_api}"}}',
                "message": '{"text": "%s"}' % message.text.replace('"', "'").replace("\n", ""),
            },
        )

    async def get_raw_messages_by_conversation(self, conversation: dict) -> list[dict]:
        """
        Docs for response from Facebook is here:
        https://developers.facebook.com/docs/graph-api/reference/page/messages/
        """
        messages = []
        for raw_message in conversation["messages"]["data"]:
            message_data = self.client.get(
                raw_message["id"],
                {"fields": "id, message, to, created_time, from, thread_id"},
            )
            messages.append(message_data)
        return messages

    async def format_raw_conversations_to_threads(self, raw_conversations: list[dict]) -> list[DataThreadRequest]:
        threads = []
        for raw_conversation in raw_conversations:
            conversation = self.client.get(
                raw_conversation["id"],
                {"fields": "messages, participants, scoped_thread_key"},
            )

            raw_messages = await self.get_raw_messages_by_conversation(conversation)
            messages = await self.format_raw_messages(raw_messages, conversation["participants"]["data"][0]["username"])

            thread = DataThreadRequest(
                instagram_id_from_official_graph_api=conversation["id"],
                thread_to_user_id_from_official_graph_api=conversation["participants"]["data"][1]["id"],
                thread_to_username=conversation["participants"]["data"][1]["username"],
                messages=messages,
            )
            threads.append(thread)
        return threads

    @staticmethod
    async def format_raw_messages(
        raw_messages: list[dict], thread_owner_username: str
    ) -> list[DataThreadMessageRequest]:
        messages = []
        for raw_message in raw_messages:
            if not raw_message["message"]:
                continue

            message = DataThreadMessageRequest(
                instagram_id_from_official_graph_api=raw_message["id"],
                created_at=datetime.fromisoformat(raw_message["created_time"]).timestamp(),
                sender=("blogger" if raw_message["from"]["username"] == thread_owner_username else "external_user"),
                instagram_user_id_official_graph_api=raw_message["to"]["data"][0]["id"],
                item_type="text",
                text=raw_message["message"],
                link=None,
            )
            messages.append(message)
        return messages
