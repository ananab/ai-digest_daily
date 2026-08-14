import logging
from datetime import datetime
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)


class HuggingFaceCollector(BaseCollector):
    """Hugging Face Daily Papers API"""

    name = 'huggingface'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            response = await self.client.get(
                'https://huggingface.co/api/daily_papers',
                params={'limit': 20},
            )
            response.raise_for_status()
            papers = response.json()

            for paper in papers:
                paper_info = paper.get('paper', paper)
                title = paper_info.get('title', '')
                summary = paper_info.get('summary', '')
                paper_id = paper_info.get('id', '')
                url = f'https://huggingface.co/papers/{paper_id}' if paper_id else ''

                # 提取作者
                authors = paper_info.get('authors', [])
                author_names = ', '.join(
                    a.get('name', '') for a in authors[:3]
                ) if isinstance(authors, list) else ''

                # 提取发布日期
                published_date = ''
                for date_key in ['publishedAt', 'published_at', 'date']:
                    date_val = paper_info.get(date_key, '') or paper.get(date_key, '')
                    if date_val:
                        try:
                            if isinstance(date_val, str):
                                dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                                published_date = dt.strftime('%Y-%m-%d')
                                break
                        except (ValueError, AttributeError):
                            pass

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=url,
                    source='Hugging Face',
                    category='paper',
                    published_date=published_date,
                    metadata={'authors': author_names},
                ))

            logger.info(f'HuggingFace: 采集到 {len(items)} 篇论文')
        except Exception as e:
            logger.error(f'HuggingFace 采集失败: {e}')

        return items
