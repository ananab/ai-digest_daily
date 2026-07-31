import logging
from typing import List
from difflib import SequenceMatcher
from .collectors.base import CollectedItem

logger = logging.getLogger(__name__)


class Processor:
    """数据处理器：去重、清洗、分类"""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def process(self, items: List[CollectedItem]) -> dict[str, List[CollectedItem]]:
        """
        处理采集数据

        Args:
            items: 原始采集数据列表

        Returns:
            按类别分组的数据字典 {'news': [...], 'paper': [...], 'repo': [...], 'discussion': [...]}
        """
        # 1. 清洗：过滤无效数据
        cleaned = self._clean(items)
        logger.info(f'清洗后: {len(cleaned)} 条 (原始 {len(items)} 条)')

        # 2. 去重：基于标题相似度
        deduplicated = self._deduplicate(cleaned)
        logger.info(f'去重后: {len(deduplicated)} 条')

        # 3. 分类
        categorized = self._categorize(deduplicated)

        for category, items_list in categorized.items():
            logger.info(f'  {category}: {len(items_list)} 条')

        return categorized

    def _clean(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """清洗无效数据"""
        cleaned = []
        for item in items:
            # 过滤空标题
            if not item.title or len(item.title.strip()) < 3:
                continue

            # 清理标题
            item.title = item.title.strip()
            if len(item.title) > 200:
                item.title = item.title[:200] + '...'

            # 清理摘要
            if item.summary:
                item.summary = item.summary.strip()
                if len(item.summary) > 500:
                    item.summary = item.summary[:500] + '...'

            cleaned.append(item)

        return cleaned

    def _deduplicate(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """基于标题相似度去重"""
        unique = []

        for item in items:
            is_duplicate = False
            for existing in unique:
                # 使用 SequenceMatcher 计算标题相似度
                similarity = SequenceMatcher(
                    None,
                    item.title.lower(),
                    existing.title.lower()
                ).ratio()

                if similarity > self.similarity_threshold:
                    is_duplicate = True
                    # 保留信息更完整的（优先有 URL 的）
                    if item.url and not existing.url:
                        unique.remove(existing)
                        unique.append(item)
                    break

            if not is_duplicate:
                unique.append(item)

        return unique

    def _categorize(self, items: List[CollectedItem]) -> dict[str, List[CollectedItem]]:
        """按类别分组"""
        categorized = {
            'news': [],
            'paper': [],
            'repo': [],
            'discussion': [],
        }

        for item in items:
            category = item.category
            if category in categorized:
                categorized[category].append(item)
            else:
                categorized['news'].append(item)

        return categorized
