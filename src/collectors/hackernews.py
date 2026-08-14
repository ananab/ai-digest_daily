import logging
from datetime import datetime
from .base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# AI 相关关键词
AI_KEYWORDS = {
    'ai', 'artificial intelligence', 'llm', 'gpt', 'claude', 'openai', 'anthropic',
    'machine learning', 'deep learning', 'neural', 'transformer', 'diffusion',
    'generative', 'chatbot', 'copilot', 'gemini', 'mistral', 'llama', 'embedding',
    'rag', 'fine-tune', 'fine tuning', 'agent', 'mcp', 'multimodal',
    '人工智能', '大模型', '机器学习', '深度学习',
}


class HackerNewsCollector(BaseCollector):
    """Hacker News AI 相关热门讨论"""

    name = 'hackernews'

    async def collect(self) -> list[CollectedItem]:
        items = []
        try:
            # 获取 top stories
            response = await self.client.get(
                'https://hacker-news.firebaseio.com/v0/topstories.json'
            )
            response.raise_for_status()
            story_ids = response.json()[:50]  # 取前 50 条检查

            # 并发获取详情
            import asyncio
            tasks = [self._fetch_item(sid) for sid in story_ids]
            stories = await asyncio.gather(*tasks, return_exceptions=True)

            for story in stories:
                if isinstance(story, Exception) or story is None:
                    continue
                items.append(story)

            logger.info(f'HackerNews: 采集到 {len(items)} 条 AI 相关讨论')
        except Exception as e:
            logger.error(f'HackerNews 采集失败: {e}')

        return items

    async def _fetch_item(self, story_id: int) -> CollectedItem | None:
        """获取单条 story 详情，过滤 AI 相关"""
        try:
            response = await self.client.get(
                f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
            )
            story = response.json()
            if not story:
                return None

            title = story.get('title', '')
            url = story.get('url', f'https://news.ycombinator.com/item?id={story_id}')
            score = story.get('score', 0)

            # 过滤：只保留 AI 相关或高分讨论
            title_lower = title.lower()
            is_ai_related = any(kw in title_lower for kw in AI_KEYWORDS)

            if not is_ai_related and score < 100:
                return None

            # 提取发布日期（HN API 返回 unix timestamp）
            published_date = ''
            timestamp = story.get('time')
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(timestamp)
                    published_date = dt.strftime('%Y-%m-%d')
                except (ValueError, OSError):
                    pass

            return CollectedItem(
                title=title,
                summary=f'⬆️ {score} points · {story.get("descendants", 0)} comments',
                url=url,
                source='Hacker News',
                category='discussion',
                published_date=published_date,
                metadata={'score': score, 'comments': story.get('descendants', 0)},
            )
        except Exception:
            return None
