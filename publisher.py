import asyncio
from typing import Optional

import sentry_sdk
from aiohttp import ClientConnectorError, ClientResponseError
from api.schemas import DataBlogger, DataGeneratedMessage, DataThread
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
            logger.debug("Trying to get active bloggers for save their threads")
            bloggers: list[Optional[DataBlogger]] = await manager.get_active_bloggers()
        except (ClientResponseError, ClientConnectorError) as e:
            logger.error("Error for getting active bloggers")
            logger.error(str(e))
            await asyncio.sleep(60)
            continue

        try:
            logger.debug(f"Count bloggers for saving threads: {len(bloggers)}")
            bloggers_threads: Optional[list[Optional[DataThread]]] = await asyncio.gather(
                *(manager.get_threads_and_save_by_blogger(blogger) for blogger in bloggers)
            )
        except ClientResponseError as e:
            logger.error("Error for getting and saving thread for bloggers")
            logger.error(str(e))
            await asyncio.sleep(60)
            continue

        try:
            bloggers_with_new_messages: Optional[list[DataGeneratedMessage]] = await asyncio.gather(
                *(
                    manager.get_generated_answer_based_on_blogger_threads_and_save(blogger_threads)
                    for blogger_threads in bloggers_threads
                    if blogger_threads is not None
                )
            )
            result = []
            for blogger_with_new_messages in bloggers_with_new_messages:
                result.extend([item for item in blogger_with_new_messages if item])

            logger.debug(f"Count new messages for answering: {len(result)}")
        except ClientResponseError as e:
            logger.error("Error for getting and saving new generated answers")
            logger.error(str(e))
            await asyncio.sleep(60)
            continue

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
