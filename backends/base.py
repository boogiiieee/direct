from abc import ABC, abstractmethod
from typing import Optional

from instagrapi.types import DirectMessage, DirectThread


class BaseDirectBackend(ABC):
    @abstractmethod
    async def get_all_threads(self) -> list[Optional[DirectThread]]:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message) -> DirectMessage:
        raise NotImplementedError
