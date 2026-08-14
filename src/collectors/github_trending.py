import logging
from datetime import datetime
from bs4 import BeautifulSoup
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# 关注的编程语言（AI/ML 相关）
AI_LANGUAGES = {'python', 'jupyter-notebook', 'rust', 'c++', 'typescript'}


class GitHubTrendingCollector(BaseCollector):
    """GitHub Trending 热门项目采集"""

    name = 'github_trending'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            # 采集 daily trending 的 Python 项目（AI/ML 为主）
            response = await self.client.get(
                'https://github.com/trending/python',
                params={'since': 'daily'},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            for article in soup.select('article.Box-row'):
                # 项目名和链接
                repo_link = article.select_one('h2 a')
                if not repo_link:
                    continue

                repo_path = repo_link.get('href', '').strip('/')
                repo_name = repo_path.split('/')[-1] if repo_path else ''
                owner = repo_path.split('/')[0] if '/' in repo_path else ''
                url = f'https://github.com/{repo_path}' if repo_path else ''

                # 项目描述
                desc_el = article.select_one('p')
                description = desc_el.get_text(strip=True) if desc_el else ''

                # Stars 数量（今日新增）
                stars_today_el = article.select_one('span.d-inline-block.float-sm-right')
                stars_today = stars_today_el.get_text(strip=True) if stars_today_el else ''

                # 总 Stars
                stars_el = article.select_one('a.Link--muted.d-inline-block')
                total_stars = stars_el.get_text(strip=True).replace(',', '') if stars_el else ''

                # GitHub trending shows daily date, use today's date
                published_date = datetime.now().strftime('%Y-%m-%d')

                items.append(CollectedItem(
                    title=f'{owner}/{repo_name}' if owner else repo_name,
                    summary=description,
                    url=url,
                    source='GitHub Trending',
                    category='repo',
                    published_date=published_date,
                    metadata={
                        'stars_today': stars_today,
                        'total_stars': total_stars,
                        'owner': owner,
                    },
                ))

            logger.info(f'GitHub Trending: 采集到 {len(items)} 个项目')
        except Exception as e:
            logger.error(f'GitHub Trending 采集失败: {e}')

        return items
