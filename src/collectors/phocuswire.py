import logging
import feedparser
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class PhocusWireCollector(BaseCollector):
    """PhocusWire 旅游科技新闻采集"""

    name = 'phocuswire'

    async def collect(self) -> list[CollectedItem]:
        items = []

        # Try RSS feed
        rss_urls = [
            'https://www.phocuswire.com/rss',
            'https://www.phocuswire.com/feed',
        ]

        for rss_url in rss_urls:
            try:
                response = await self.client.get(rss_url)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:15]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        summary = entry.get('summary', '')
                        summary = BeautifulSoup(summary, 'lxml').get_text(strip=True)
                        if len(summary) > 300:
                            summary = summary[:300] + '...'

                        items.append(CollectedItem(
                            title=title,
                            summary=summary,
                            url=link,
                            source='PhocusWire',
                            category='news',
                        ))
                    logger.info(f'PhocusWire RSS: 采集到 {len(items)} 条新闻')
                    return items
            except Exception as e:
                logger.debug(f'PhocusWire RSS {rss_url} 失败: {e}')

        # Fallback: HTML scraping
        try:
            response = await self.client.get('https://www.phocuswire.com/')
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            for article in soup.select('article, .article, [class*="news"]')[:15]:
                link_el = article.select_one('a[href]')
                if not link_el:
                    continue

                title = link_el.get_text(strip=True)
                if len(title) < 10:
                    continue

                link = link_el.get('href', '')
                if not link.startswith('http'):
                    link = f'https://www.phocuswire.com{link}'

                summary_el = article.select_one('p, .summary, .excerpt')
                summary = summary_el.get_text(strip=True) if summary_el else ''
                if len(summary) > 300:
                    summary = summary[:300] + '...'

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='PhocusWire',
                    category='news',
                ))

            logger.info(f'PhocusWire HTML: 采集到 {len(items)} 条新闻')
        except Exception as e:
            logger.error(f'PhocusWire 采集失败: {e}')

        return items
