import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


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


class LyssnaCollector(BaseCollector):
    """Lyssna 用户研究平台博客采集"""

    name = 'lyssna'
    base_url = 'https://lyssna.com/blog'

    def __init__(self):
        super().__init__()
        # Use base User-Agent

    async def collect(self) -> list[CollectedItem]:
        """采集 Lyssna 博客内容"""
        items = []

        try:
            response = await self.client.get(self.base_url)
            if response.status_code != 200:
                logger.warning(f'{self.name}: HTTP {response.status_code}')
                return items

            html = response.text

            # 解析文章列表
            patterns = [
                r'<article[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'class="blog[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<a[^>]*href="([^"]+)"',
                r'<a[^>]*href="([^"]+)"[^>]*>\s*<h[23][^>]*>(.*?)</h[23]>',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if matches:
                    for match in matches[:20]:
                        if len(match) == 2:
                            if match[0].startswith('http'):
                                url, title = match
                            else:
                                title, url = match
                        else:
                            continue

                        title = re.sub(r'<[^>]+>', '', title).strip()
                        if not url.startswith('http'):
                            url = f'https://lyssna.com{url}'

                        # Extract published_date from article page
                        published_date = await _extract_date_from_url(self.client, url)

                        items.append(CollectedItem(
                            title=title,
                            summary='',
                            url=url,
                            source=self.name,
                            category='news',
                            published_date=published_date
                        ))
                    break

            logger.info(f'{self.name}: 采集到 {len(items)} 条')

        except Exception as e:
            logger.error(f'{self.name}: 采集失败 - {e}')

        return items
