import logging
import re
from datetime import datetime
from .base import BaseCollector, CollectedItem
import feedparser

logger = logging.getLogger(__name__)


class CondensCollector(BaseCollector):
    """Condens 用户研究平台博客采集"""

    name = 'condens'
    base_url = 'https://condens.io/blog'
    rss_url = 'https://condens.io/blog/rss.xml'

    def __init__(self):
        super().__init__()
        # Use base User-Agent

    async def collect(self) -> list[CollectedItem]:
        """采集 Condens 博客内容"""
        items = []

        # 优先尝试 RSS
        try:
            response = await self.client.get(self.rss_url)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                for entry in feed.entries[:20]:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '').strip()
                    summary = entry.get('summary', '').strip()
                    pub_date = entry.get('published', entry.get('updated', ''))

                    # 解析发布时间
                    published_date = datetime.now().strftime('%Y-%m-%d')
                    if pub_date:
                        try:
                            # RSS 时间格式通常是 RFC 822
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date)
                            published_date = dt.strftime('%Y-%m-%d')
                        except:
                            pass

                    if title and link:
                        items.append(CollectedItem(
                            title=title,
                            summary=summary[:300] if summary else '',
                            url=link,
                            source=self.name,
                            category='news',
                            published_date=published_date
                        ))

                if items:
                    logger.info(f'{self.name} (RSS): 采集到 {len(items)} 条')
                    return items
        except Exception as e:
            logger.warning(f'{self.name} RSS 失败: {e}')

        # Fallback: HTML 解析
        try:
            response = await self.client.get(self.base_url)
            if response.status_code != 200:
                logger.warning(f'{self.name}: HTTP {response.status_code}')
                return items

            html = response.text

            # 解析文章列表 - 匹配包含 /blog/article-slug/ 的链接
            # 排除 /blog-collections/ 和 /blog/ 本身
            pattern = r'<a[^>]*href="(/blog/[^/"]+/)"[^>]*>'

            matches = []
            for match in re.finditer(pattern, html, re.IGNORECASE):
                url = match.group(1).strip()
                # 排除分类页面和首页
                if '/blog-collections/' in url or url == '/blog/':
                    continue
                matches.append(url)

            # 去重
            matches = list(dict.fromkeys(matches))

            for url in matches[:20]:
                if not url.startswith('http'):
                    url = f'https://condens.io{url}'

                # 访问页面获取标题和发布日期
                try:
                    page_resp = await self.client.get(url)
                    if page_resp.status_code == 200:
                        page_html = page_resp.text
                        # 提取标题 (h1)
                        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', page_html, re.DOTALL)
                        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''
                        # 提取发布日期 (time tag with datetime attribute)
                        date_match = re.search(r'<time[^>]*datetime="([^"]+)"', page_html)
                        if date_match:
                            try:
                                pub_dt = datetime.fromisoformat(date_match.group(1).replace('Z', '+00:00'))
                                published_date = pub_dt.strftime('%Y-%m-%d')
                            except:
                                published_date = datetime.now().strftime('%Y-%m-%d')
                        else:
                            published_date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        continue
                except Exception as e:
                    logger.debug(f'{self.name}: 无法访问页面 {url}: {e}')
                    continue

                if not title:
                    continue

                items.append(CollectedItem(
                    title=title,
                    summary='',
                    url=url,
                    source=self.name,
                    category='news',
                    published_date=published_date
                ))

            logger.info(f'{self.name}: 采集到 {len(items)} 条')

        except Exception as e:
            logger.error(f'{self.name}: 采集失败 - {e}')

        return items
