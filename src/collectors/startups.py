import logging
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


def _parse_date(entry) -> str:
    """Parse date from feedparser entry"""
    for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
        date_tuple = entry.get(date_field)
        if date_tuple:
            try:
                dt = datetime(*date_tuple[:6])
                return dt.strftime('%Y-%m-%d')
            except:
                pass
    return ''


class StartupsCollector(BaseCollector):
    """AI Startups新闻采集 - 广泛的AI创业公司来源"""

    name = 'startups'

    # ProductHunt/Hacker News 过滤关键词（标题或摘要必须包含至少一个）
    FILTER_KEYWORDS = [
        'ai', 'gpt', 'llm', 'agent', 'chatbot', 'copilot',
        'machine learning', 'startup', 'launch', 'funding',
        'saas', 'automation', 'assistant', 'generator',
        'neural', 'deep learning', 'nlp', 'computer vision',
        'series a', 'series b', 'series c', 'seed', 'raise',
    ]

    async def collect(self) -> list[CollectedItem]:
        items = []

        # 广泛的AI创业公司来源
        feeds = [
            ('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI', False),
            ('https://www.newcomer.co/feed', 'Newcomer', False),
            ('https://www.producthunt.com/feed', 'ProductHunt', True),  # 需要关键词过滤
            ('https://venturebeat.com/category/ai/feed/', 'VentureBeat AI', False),
            ('https://www.ycombinator.com/blog/feed', 'Y Combinator', True),  # 需要关键词过滤
        ]

        for feed_url, source, needs_filter in feeds:
            try:
                response = await self.client.get(feed_url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:50]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')
                    summary = BeautifulSoup(summary, 'lxml').get_text(strip=True)
                    if len(summary) > 300:
                        summary = summary[:300] + '...'

                    # ProductHunt 需要关键词过滤
                    if needs_filter:
                        text = (title + ' ' + summary).lower()
                        if not any(kw in text for kw in self.FILTER_KEYWORDS):
                            continue

                    items.append(CollectedItem(
                        title=title,
                        summary=summary,
                        url=link,
                        source=source,
                        category='startups',
                        published_date=_parse_date(entry),
                    ))

                logger.info(f'{source}: 采集到 {len(feed.entries)} 条')

            except Exception as e:
                logger.error(f'{source} 采集失败: {e}')

        return items
