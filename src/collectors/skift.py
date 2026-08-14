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


async def _extract_date_from_url(client, url: str) -> str:
    """Visit article page and extract published date"""
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return ''
        soup = BeautifulSoup(response.text, 'lxml')

        # Check time tag
        time_el = soup.find('time')
        if time_el:
            datetime_str = time_el.get('datetime')
            if datetime_str:
                try:
                    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass

        # Check meta tags
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '').lower()
            if 'date' in prop or 'time' in prop:
                content = meta.get('content', '')
                if content and len(content) >= 10:
                    try:
                        dt = datetime.fromisoformat(content.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d')
                    except:
                        pass

        # Extract from page text
        import re
        text = soup.get_text()
        date_patterns = [
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})',
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    if '-' in date_str:
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                    elif ',' in date_str:
                        dt = datetime.strptime(date_str, '%B %d, %Y')
                    else:
                        dt = datetime.strptime(date_str, '%d %B %Y')
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass
    except Exception:
        pass
    return ''


class SkiftCollector(BaseCollector):
    """Skift 旅游行业新闻采集"""

    name = 'skift'

    async def collect(self) -> list[CollectedItem]:
        items = []

        # Try RSS feed first
        rss_urls = [
            'https://skift.com/feed/',
            'https://skift.com/rss/',
        ]

        for rss_url in rss_urls:
            try:
                response = await self.client.get(rss_url)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:50]:
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
                            source='Skift',
                            category='news',
                            published_date=_parse_date(entry),
                        ))
                    logger.info(f'Skift RSS: 采集到 {len(items)} 条新闻')
                    return items
            except Exception as e:
                logger.debug(f'Skift RSS {rss_url} 失败: {e}')

        # Fallback: HTML scraping
        try:
            response = await self.client.get('https://skift.com/')
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            for article in soup.select('article, .post, [class*="article"]')[:50]:
                link_el = article.select_one('a[href]')
                if not link_el:
                    continue

                title = link_el.get_text(strip=True)
                if len(title) < 10:
                    continue

                link = link_el.get('href', '')
                if not link.startswith('http'):
                    link = f'https://skift.com{link}'

                summary_el = article.select_one('p, .excerpt, .summary')
                summary = summary_el.get_text(strip=True) if summary_el else ''
                if len(summary) > 300:
                    summary = summary[:300] + '...'

                # Extract published_date from article page
                published_date = await _extract_date_from_url(self.client, link)

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='Skift',
                    category='news',
                    published_date=published_date,
                ))

            logger.info(f'Skift HTML: 采集到 {len(items)} 条新闻')
        except Exception as e:
            logger.error(f'Skift 采集失败: {e}')

        return items
