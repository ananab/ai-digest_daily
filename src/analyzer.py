import logging
from typing import List
from anthropic import Anthropic
from .config import config
from .collectors.base import CollectedItem

logger = logging.getLogger(__name__)


class Analyzer:
    """Claude API 智能分析器"""

    def __init__(self):
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def analyze(
        self,
        categorized_data: dict[str, List[CollectedItem]]
    ) -> dict:
        """
        两阶段分析

        Args:
            categorized_data: 分类后的数据 {'news': [...], 'paper': [...], ...}

        Returns:
            分析报告字典
        """
        # 阶段 1：筛选与排序（使用 Haiku 快速处理）
        logger.info('阶段 1：筛选与分类...')
        filtered = self._filter_and_rank(categorized_data)

        # 阶段 2：深度分析（使用 Sonnet 生成报告）
        logger.info('阶段 2：深度分析...')
        report = self._generate_report(filtered)

        return report

    def _filter_and_rank(self, categorized_data: dict) -> dict:
        """筛选与排序：过滤低质量内容，按重要性排序"""
        filtered = {}

        for category, items in categorized_data.items():
            if not items:
                filtered[category] = []
                continue

            # 构建输入文本
            items_text = '\n'.join([
                f'{i+1}. {item.title}' + (f' - {item.summary}' if item.summary else '')
                for i, item in enumerate(items)
            ])

            prompt = f"""你是一个 AI 领域内容筛选专家。请从以下{category}列表中筛选出最重要、最有价值的内容。

要求：
1. 过滤掉重复、低质量、营销性质的内容
2. 保留真正有技术价值或影响力的内容
3. 按重要性排序（最重要的在前）
4. 最多保留 10 条

{category}列表：
{items_text}

请直接返回筛选后的编号列表，每行一个编号，例如：
1
3
5
7"""

            try:
                response = self.client.messages.create(
                    model=config.claude_model_filter,
                    max_tokens=200,
                    messages=[{'role': 'user', 'content': prompt}],
                )

                # 解析返回的编号
                selected_indices = []
                for line in response.content[0].text.strip().split('\n'):
                    line = line.strip()
                    if line.isdigit():
                        idx = int(line) - 1
                        if 0 <= idx < len(items):
                            selected_indices.append(idx)

                filtered[category] = [items[i] for i in selected_indices[:10]]
                logger.info(f'{category}: 筛选后保留 {len(filtered[category])} 条')

            except Exception as e:
                logger.error(f'筛选 {category} 失败: {e}')
                # 降级：直接取前 10 条
                filtered[category] = items[:10]

        return filtered

    def _generate_report(self, filtered_data: dict) -> dict:
        """生成深度分析报告"""

        # 构建输入数据
        sections = []
        for category, items in filtered_data.items():
            if not items:
                continue

            category_cn = {
                'news': 'AI 新闻热点',
                'paper': '学术论文',
                'repo': '开源项目',
                'discussion': '社区讨论',
            }.get(category, category)

            items_text = '\n'.join([
                f'{i+1}. {item.title}\n   {item.summary}\n   链接: {item.url}'
                for i, item in enumerate(items)
            ])

            sections.append(f'【{category_cn}】\n{items_text}')

        all_data = '\n\n'.join(sections)

        prompt = f"""你是一个科技媒体编辑。请基于以下今日 AI 领域动态，生成一份适合飞书群播报的中文日报。

今日动态：
{all_data}

请严格按以下格式生成报告（使用中文）：

## 🔍 今日速览
（你是科技媒体编辑，请根据以上素材写一段「今日速览」总结。要求：3-6 条要点，每条一行，以「• 」开头。抓住最重要的模型/产品/行业动态，信息密度高。不要编造素材中没有的信息。不要输出开场白或结尾寒暄。总字数控制在 220 字以内。）

## 📎 相关链接

**模型发布/更新**
（列出相关链接）

**产品发布/更新**
（列出相关链接）

**Startups**
（列出相关链接）

**行业动态**
（列出相关链接）

**论文研究**
（列出相关链接）

**技巧与观点**
（列出相关链接）

要求：
- 语言简洁专业，适合飞书群快速阅读
- 链接格式: [标题](url)
- 如果某个分类没有相关内容，写「无」
- 突出技术创新和实际影响"""

        try:
            response = self.client.messages.create(
                model=config.claude_model_report,
                max_tokens=4000,
                messages=[{'role': 'user', 'content': prompt}],
            )

            if not response.content:
                logger.error(f'生成报告失败: response.content 为空, response={response}')
                return {
                    'report': self._fallback_report(filtered_data),
                    'data': filtered_data,
                }

            report_text = response.content[0].text

            return {
                'report': report_text,
                'data': filtered_data,
            }

        except Exception as e:
            logger.error(f'生成报告失败: {e}')
            # 降级：返回简单格式
            return {
                'report': self._fallback_report(filtered_data),
                'data': filtered_data,
            }

    def _fallback_report(self, filtered_data: dict) -> str:
        """降级报告：不使用 Claude API"""
        from datetime import date

        lines = [f'# 🤖 AI 前沿日报 | {date.today().isoformat()}\n']

        category_cn = {
            'news': '📰 今日热点',
            'paper': '📄 论文精选',
            'repo': '🛠️ 开源项目',
            'discussion': '💬 社区讨论',
        }

        for category, items in filtered_data.items():
            if not items:
                continue

            lines.append(f'\n## {category_cn.get(category, category)}\n')
            for i, item in enumerate(items[:5], 1):
                lines.append(f'{i}. [{item.title}]({item.url})')
                if item.summary:
                    lines.append(f'   {item.summary}')

        return '\n'.join(lines)
