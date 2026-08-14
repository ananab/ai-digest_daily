import logging
from datetime import datetime
import feedparser
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


class RedditMLCollector(BaseCollector):
    """Reddit r/MachineLearning RSS 采集"""

    name = 'reddit_ml'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            response = await self.client.get(
                'https://www.reddit.com/r/MachineLearning/.rss',
                headers={'User-Agent': 'AI-Daily-Digest/1.0 (educational)'},
            )
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '')

                # 清理 HTML 标签
                from bs4 import BeautifulSoup
                summary = BeautifulSoup(summary, 'lxml').get_text(strip=True)
                if len(summary) > 300:
                    summary = summary[:300] + '...'

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='Reddit r/ML',
                    category='discussion',
                    published_date=_parse_date(entry),
                ))

            logger.info(f'Reddit r/ML: 采集到 {len(items)} 条讨论')
        except Exception as e:
            logger.error(f'Reddit r/ML 采集失败: {e}')

        return items
