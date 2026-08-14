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

        # HTML fallback URLs for each source
        html_sources = {
            'TechCrunch AI': 'https://techcrunch.com/category/artificial-intelligence/',
            'VentureBeat AI': 'https://venturebeat.com/category/ai/',
            'Y Combinator': 'https://www.ycombinator.com/blog',
        }

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

                logger.info(f'{source} RSS: 采集到 {len(feed.entries)} 条')

            except Exception as e:
                logger.error(f'{source} RSS 采集失败: {e}')

                # Fallback: HTML scraping for sources that have mapping
                fallback_url = html_sources.get(source)
                if not fallback_url:
                    continue

                try:
                    response = await self.client.get(fallback_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'lxml')

                    for article in soup.select('article, .post, [class*="article"], [class*="post"]')[:15]:
                        link_el = article.select_one('a[href]')
                        if not link_el:
                            continue

                        title = link_el.get_text(strip=True)
                        if len(title) < 10:
                            continue

                        link = link_el.get('href', '')
                        if not link.startswith('http'):
                            from urllib.parse import urljoin
                            link = urljoin(fallback_url, link)

                        summary_el = article.select_one('p, .summary, .excerpt, .description')
                        summary = summary_el.get_text(strip=True) if summary_el else ''
                        if len(summary) > 300:
                            summary = summary[:300] + '...'

                        # Keyword filter for sources that need it
                        if needs_filter:
                            text = (title + ' ' + summary).lower()
                            if not any(kw in text for kw in self.FILTER_KEYWORDS):
                                continue

                        # Extract published_date from article page
                        published_date = await _extract_date_from_url(self.client, link)

                        items.append(CollectedItem(
                            title=title,
                            summary=summary,
                            url=link,
                            source=source,
                            category='startups',
                            published_date=published_date,
                        ))

                    logger.info(f'{source} HTML: 采集到 {len(items)} 条')

                except Exception as e2:
                    logger.error(f'{source} HTML fallback 也失败: {e2}')

        return items
