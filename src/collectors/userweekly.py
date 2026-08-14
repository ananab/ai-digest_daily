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


class UserWeeklyCollector(BaseCollector):
    """User Weekly 用户研究新闻采集"""

    name = 'userweekly'

    async def collect(self) -> list[CollectedItem]:
        items = []

        # Try RSS feed
        rss_urls = [
            'https://userweekly.com/feed/',
            'https://userweekly.com/rss/',
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
                            source='User Weekly',
                            category='news',
                            published_date=_parse_date(entry),
                        ))
                    logger.info(f'UserWeekly RSS: 采集到 {len(items)} 条新闻')
                    return items
            except Exception as e:
                logger.debug(f'UserWeekly RSS {rss_url} 失败: {e}')

        # Fallback: HTML scraping with article page visit
        try:
            response = await self.client.get('https://userweekly.com/')
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            for article in soup.select('article, .post, .entry, [class*="article"]')[:15]:
                link_el = article.select_one('a[href]')
                if not link_el:
                    continue

                title = link_el.get_text(strip=True)
                if len(title) < 10:
                    continue

                link = link_el.get('href', '')
                if not link.startswith('http'):
                    link = f'https://userweekly.com{link}'

                summary_el = article.select_one('p, .summary, .excerpt, .entry-content')
                summary = summary_el.get_text(strip=True) if summary_el else ''
                if len(summary) > 300:
                    summary = summary[:300] + '...'

                # 访问文章页面提取日期
                published_date = ''
                try:
                    article_response = await self.client.get(link)
                    if article_response.status_code == 200:
                        article_soup = BeautifulSoup(article_response.text, 'lxml')

                        # 查找 time 标签
                        time_el = article_soup.find('time')
                        if time_el:
                            datetime_str = time_el.get('datetime')
                            if datetime_str:
                                try:
                                    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                                    published_date = dt.strftime('%Y-%m-%d')
                                except:
                                    pass

                        # 查找 meta 标签
                        if not published_date:
                            for meta in article_soup.find_all('meta'):
                                prop = meta.get('property', '').lower()
                                if 'date' in prop or 'time' in prop:
                                    content = meta.get('content', '')
                                    if content and len(content) >= 10:
                                        try:
                                            dt = datetime.fromisoformat(content.replace('Z', '+00:00'))
                                            published_date = dt.strftime('%Y-%m-%d')
                                            break
                                        except:
                                            pass

                        # 从页面文本提取日期
                        if not published_date:
                            import re
                            text = article_soup.get_text()
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
                                        published_date = dt.strftime('%Y-%m-%d')
                                        break
                                    except:
                                        pass
                except Exception as e:
                    logger.debug(f'UserWeekly 访问文章页面失败: {link}, 错误: {e}')

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='User Weekly',
                    category='news',
                    published_date=published_date,
                ))

            logger.info(f'UserWeekly HTML: 采集到 {len(items)} 条新闻')
        except Exception as e:
            logger.error(f'UserWeekly 采集失败: {e}')

        return items
