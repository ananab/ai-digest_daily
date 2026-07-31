import logging
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

                items.append(CollectedItem(
                    title=title,
                    summary=summary,
                    url=url,
                    source='Hugging Face',
                    category='paper',
                    metadata={'authors': author_names},
                ))

            logger.info(f'HuggingFace: 采集到 {len(items)} 篇论文')
        except Exception as e:
            logger.error(f'HuggingFace 采集失败: {e}')

        return items
