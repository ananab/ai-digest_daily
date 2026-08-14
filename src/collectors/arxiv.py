import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Arxiv 分类：AI、NLP、计算机视觉
ARXIV_CATEGORIES = ['cs.AI', 'cs.CL', 'cs.CV', 'cs.LG']


class ArxivCollector(BaseCollector):
    """Arxiv 最新论文采集"""

    name = 'arxiv'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            category_query = '+OR+'.join(f'cat:{cat}' for cat in ARXIV_CATEGORIES)
            url = (
                f'http://export.arxiv.org/api/query?'
                f'search_query={category_query}'
                f'&sortBy=submittedDate&sortOrder=descending&max_results=20'
            )

            response = await self.client.get(url)
            response.raise_for_status()

            # 解析 Atom XML
            root = ET.fromstring(response.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.findtext('atom:title', '', ns).strip().replace('\n', ' ')
                summary = entry.findtext('atom:summary', '', ns).strip().replace('\n', ' ')

                # 获取链接
                link = ''
                for link_el in entry.findall('atom:link', ns):
                    if link_el.get('type') == 'text/html':
                        link = link_el.get('href', '')
                        break
                if not link:
                    link_el = entry.find('atom:link', ns)
                    link = link_el.get('href', '') if link_el is not None else ''

                # 获取作者
                authors = [
                    a.findtext('atom:name', '', ns)
                    for a in entry.findall('atom:author', ns)
                ][:3]

                # 截断过长的摘要
                if len(summary) > 300:
                    summary = summary[:300] + '...'

                # 提取发布日期
                published_date = ''
                for date_tag in ['atom:published', 'atom:updated']:
                    date_str = entry.findtext(date_tag, '', ns)
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            published_date = dt.strftime('%Y-%m-%d')
                            break
                        except (ValueError, AttributeError):
                            pass

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source='Arxiv',
                    category='paper',
                    published_date=published_date,
                    metadata={'authors': ', '.join(authors)},
                ))

            logger.info(f'Arxiv: 采集到 {len(items)} 篇论文')
        except Exception as e:
            logger.error(f'Arxiv 采集失败: {e}')

        return items
