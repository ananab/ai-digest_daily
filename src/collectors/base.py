import httpx
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal
from src.config import config

logger = logging.getLogger(__name__)


@dataclass
class CollectedItem:
    """统一采集数据结构"""
    title: str
    summary: str = ''
    url: str = ''
    source: str = ''
    category: Literal['news', 'paper', 'repo', 'discussion'] = 'news'
    metadata: dict = field(default_factory=dict)


class BaseCollector(ABC):
    """采集器基类"""

    name: str = 'base'

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=config.request_timeout,
            headers={'User-Agent': config.user_agent},
            follow_redirects=True,
        )

    @abstractmethod
    async def collect(self) -> list[CollectedItem]:
        """采集数据，返回 CollectedItem 列表"""
        ...

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
