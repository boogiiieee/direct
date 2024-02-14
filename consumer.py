import asyncio
import random
from typing import Optional

import sentry_sdk
from aiohttp import ClientConnectorError, ClientResponseError
from api.schemas import DataBloggerWithGeneratedMessages
from configs import SENTRY_DSN
from loguru import logger
from manager import DirectManager

sentry_sdk.init(
    dsn=SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


async def main():
    while True:
        manager = DirectManager()
        try:
            logger.debug("Trying to get messages for publishing")
            bloggers_with_messages_for_publishing: list[
                Optional[DataBloggerWithGeneratedMessages]
            ] = await manager.get_messages_for_publishing()
        except (ClientResponseError, ClientConnectorError) as e:
            logger.error("Error for getting messages for publishing")
            logger.error(str(e))
            await asyncio.sleep(60)
            continue

        logger.debug(f"Count bloggers with messages for publishing: {len(bloggers_with_messages_for_publishing)}")

        for blogger_with_messages_for_publishing in bloggers_with_messages_for_publishing:
            for message_for_publishing in blogger_with_messages_for_publishing.messages:
                logger.debug(
                    f"Trying send message from instagram login '{blogger_with_messages_for_publishing.instagram_login}'"
                    f" to username '{message_for_publishing.recipient_instagram_username}'"
                )
                try:
                    await manager.send_message(message_for_publishing, blogger_with_messages_for_publishing)
                    await manager.update_message_status(message_for_publishing, status="sent")
                    logger.debug(
                        f"Message from instagram login '{blogger_with_messages_for_publishing.instagram_login}'"
                        f" to username '{message_for_publishing.recipient_instagram_username}' was successfully sent"
                    )
                except Exception as e:
                    await manager.update_message_status(message_for_publishing, status="error", error=str(e))
                    logger.debug(
                        f"Message from instagram login '{blogger_with_messages_for_publishing.instagram_login}'"
                        f" to username '{message_for_publishing.recipient_instagram_username}' wasn't sent"
                    )
                    logger.error(str(e))
                await asyncio.sleep(random.randint(3, 10))
            await asyncio.sleep(60)
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
