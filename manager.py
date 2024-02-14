import asyncio
from typing import Optional

import aiohttp
from api.schemas import (
    DataBlogger,
    DataBloggerWithGeneratedMessages,
    DataGeneratedMessage,
    DataThread,
    DataThreadRequest,
)
from backends.facebook import FacebookBackend
from backends.instagrapi import InstagrapiBackend
from base.exceptions import APIException, ErrorCode
from configs import AUTH_SERVICE_HOST, ML_SERVICE_HOST, WRAPPER_SERVICE_HOST
from fastapi import status
from instagrapi.exceptions import ChallengeRequired
from loguru import logger


class DirectManager:
    @staticmethod
    async def get_instagram_backend(
        blogger: DataBlogger,
    ) -> InstagrapiBackend | FacebookBackend:
        if blogger.can_use_official_graph_api:
            return FacebookBackend(
                access_token=blogger.facebook_page_access_token,
                page_id=blogger.facebook_page_id,
            )
        else:
            return InstagrapiBackend(
                session_url=f"{AUTH_SERVICE_HOST}/api/v1/session",
                instagram_login=blogger.instagram_login,
            )

    @staticmethod
    async def get_active_bloggers() -> list[Optional[DataBlogger]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WRAPPER_SERVICE_HOST}/v1/api/blogger/get-active-bloggers") as response:
                response = await response.json()

        return [DataBlogger(**item) for item in response["data"]]

    async def get_threads_and_save_by_blogger(self, blogger: DataBlogger) -> Optional[list[Optional[DataThread]]]:
        logger.debug(f"Trying get thread for instagram login: {blogger.instagram_login}")
        try:
            threads: list[Optional[DataThreadRequest]] = await self.get_raw_threads_by_blogger(blogger)
        except RuntimeError:
            return
        except ChallengeRequired as e:
            logger.error(f"Error while getting threads for instagram login: {blogger.instagram_login}")
            logger.error(str(e))
            return

        logger.debug(f"Count threads for saving: {len(threads)}. Blogger: {blogger.instagram_login}")
        if threads:
            threads_for_save: list[dict] = await self.format_raw_threads(threads)
            logger.debug(f"Trying save threads. Blogger: {blogger.instagram_login}")
            result: list[Optional[DataThread]] = await self.save_threads_by_blogger(blogger, threads_for_save)
            logger.debug(f"Threads were successfully saved. Blogger: {blogger.instagram_login}")
            return result

        logger.debug(f"No threads for saving. Blogger: {blogger.instagram_login}")

    async def get_raw_threads_by_blogger(self, blogger: DataBlogger) -> list[Optional[DataThreadRequest]]:
        instagram_backend = await self.get_instagram_backend(blogger)
        logger.debug(f"Blogger: '{blogger.instagram_login}' uses {instagram_backend.__class__.__name__}")
        threads = await instagram_backend.get_all_threads()
        return threads

    @staticmethod
    async def save_threads_by_blogger(blogger: DataBlogger, threads_for_save: list[dict]) -> list[Optional[DataThread]]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WRAPPER_SERVICE_HOST}/v1/api/direct/threads",
                json={"blogger_id": blogger.id, "threads": threads_for_save},
            ) as response:
                response.raise_for_status()
                response = await response.json()
                return [DataThread(**item) for item in response["data"]]

    @staticmethod
    async def format_raw_threads(threads: list[DataThreadRequest]) -> list[dict]:
        threads_for_save = []
        for thread in threads:
            threads_for_save.append(thread.dict())

        return threads_for_save

    async def get_generated_answer_based_on_blogger_threads_and_save(
        self, blogger_threads: DataThread
    ) -> Optional[list[DataGeneratedMessage]]:
        results: Optional[list[DataGeneratedMessage]] = await asyncio.gather(
            *(self.get_generated_answer_based_on_thread_and_save(thread) for thread in blogger_threads)
        )
        return [result for result in results if result is not None]

    async def get_generated_answer_based_on_thread_and_save(
        self, thread: DataThread
    ) -> Optional[list[DataGeneratedMessage]]:
        logger.debug(f"Trying get generated answer for thread id: '{thread.id}'")

        formatted_thread = await self.format_messages_for_getting_generated_answer(thread)
        if formatted_thread:
            generated_message: str = await self.get_generated_answer_based_on_thread(formatted_thread)
            if generated_message:
                logger.debug(f"Got generated message for thread id: '{thread.id}'")
                logger.debug("Trying save generated message")
                result: Optional[DataGeneratedMessage] = await self.save_generated_answer(generated_message, thread.id)
                logger.debug(
                    "Generated message was successfully saved"
                    if result
                    else f"Thread with id '{thread.id}' already has unsent generated message"
                )
                return result

    @staticmethod
    async def get_generated_answer_based_on_thread(data) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ML_SERVICE_HOST}/predict", json=data) as response:
                response.raise_for_status()
                response = await response.json()
        texts = response.get("texts")
        if texts:
            return texts[0]

        raise APIException(
            error_code=ErrorCode.ml_service_getting_generated_text,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="ML service didn't give generated text",
        )

    @staticmethod
    async def save_generated_answer(message: str, thread_id: int) -> Optional[DataGeneratedMessage]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WRAPPER_SERVICE_HOST}/v1/api/direct/threads/generated-message",
                json={"thread_id": thread_id, "message": message},
            ) as response:
                response.raise_for_status()
                response = await response.json()
                data = response.get("data")
                if data:
                    return DataGeneratedMessage(**data)

    @staticmethod
    async def format_messages_for_getting_generated_answer(thread: DataThread):
        sorted_messages = sorted(thread.messages, key=lambda item: item.created_at)
        if sorted_messages:
            last_message_text = sorted_messages[-1].text
            if last_message_text and sorted_messages[-1].sender != "blogger":
                other_messages = sorted_messages[:-1]

                dialog_history = []
                for message in other_messages:
                    if not message.text:
                        continue
                    dialog = {}
                    if message.sender == "blogger":
                        dialog["bot"] = message.text
                        dialog["user"] = ""
                    else:
                        dialog["bot"] = ""
                        dialog["user"] = message.text
                    dialog_history.append(dialog)

                return {
                    "data": {
                        "dialogs": [
                            {
                                "user": last_message_text,
                                "dialog_history": dialog_history,
                            }
                        ]
                    },
                    "config": {
                        "generation_settings": {
                            "temperature": 0.7,
                            "max_tokens": 1000,
                            "top_p": 1,
                            "frequency_penalty": 0,
                            "presence_penalty": 0,
                        }
                    },
                }

    @staticmethod
    async def get_messages_for_publishing() -> list[Optional[DataBloggerWithGeneratedMessages]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WRAPPER_SERVICE_HOST}/v1/api/direct/threads/generated-messages") as response:
                response.raise_for_status()
                response = await response.json()
                return [DataBloggerWithGeneratedMessages(**item) for item in response["data"]]

    async def send_message(self, message: DataGeneratedMessage, blogger: DataBloggerWithGeneratedMessages) -> None:
        instagram_backend = await self.get_instagram_backend(blogger)
        logger.debug(f"Blogger: '{blogger.instagram_login}' uses {instagram_backend.__class__.__name__}")
        return await instagram_backend.send_message(message)

    @staticmethod
    async def update_message_status(
        message: DataGeneratedMessage, status: str, error: Optional[str] = None
    ) -> DataGeneratedMessage:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{WRAPPER_SERVICE_HOST}/v1/api/direct/threads/generated-messages",
                json={"id": message.id, "status": status, "error": error},
            ) as response:
                response.raise_for_status()
                response = await response.json()
                return DataGeneratedMessage(**response["data"])
