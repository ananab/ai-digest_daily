"""
轻量级冒烟测试：验证采集+处理流程（不需要 API key）
用法: python src/test_smoke.py
"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def test_collectors():
    """测试各采集器能否正常获取数据"""
    from src.collectors.huggingface import HuggingFaceCollector
    from src.collectors.arxiv import ArxivCollector
    from src.collectors.github_trending import GitHubTrendingCollector
    from src.collectors.hackernews import HackerNewsCollector
    from src.collectors.reddit_ml import RedditMLCollector

    collectors = [
        HuggingFaceCollector(),
        ArxivCollector(),
        GitHubTrendingCollector(),
        HackerNewsCollector(),
        RedditMLCollector(),
    ]

    results = {}
    for c in collectors:
        try:
            items = await c.collect()
            results[c.name] = len(items)
            if items:
                logger.info(f'  {c.name}: 示例 - {items[0].title[:60]}')
        except Exception as e:
            results[c.name] = f'ERROR: {e}'
            logger.error(f'  {c.name}: {e}')
        finally:
            await c.close()

    return results


async def test_processor(raw_items):
    """测试数据处理器"""
    from src.processor import Processor

    processor = Processor()
    categorized = processor.process(raw_items)
    return categorized


async def test_fallback_report(categorized):
    """测试降级报告生成（不需要 Claude API）"""
    from src.analyzer import Analyzer
    from src.config import config

    # 临时清空 API key 以测试降级模式
    original_key = config.kimi_api_key
    config.kimi_api_key = ''

    analyzer = Analyzer()
    report = analyzer._fallback_report(categorized)

    config.kimi_api_key = original_key
    return report


async def main():
    logger.info('=' * 60)
    logger.info('冒烟测试: 采集 + 处理 + 降级报告')
    logger.info('=' * 60)

    # 1. 测试采集
    logger.info('\n--- 测试采集 ---')
    results = await test_collectors()
    logger.info(f'\n采集结果: {results}')

    total = sum(v for v in results.values() if isinstance(v, int))
    logger.info(f'总计: {total} 条')

    if total == 0:
        logger.error('未采集到任何数据，测试失败')
        return False

    # 2. 测试处理
    logger.info('\n--- 测试数据处理 ---')
    from src.collectors.huggingface import HuggingFaceCollector
    from src.collectors.arxiv import ArxivCollector
    from src.collectors.github_trending import GitHubTrendingCollector
    from src.collectors.hackernews import HackerNewsCollector

    all_items = []
    for cls in [HuggingFaceCollector, ArxivCollector, GitHubTrendingCollector, HackerNewsCollector]:
        c = cls()
        items = await c.collect()
        all_items.extend(items)
        await c.close()

    categorized = await test_processor(all_items)
    for cat, items in categorized.items():
        logger.info(f'  {cat}: {len(items)} 条')

    # 3. 测试降级报告
    logger.info('\n--- 测试降级报告生成 ---')
    report = await test_fallback_report(categorized)
    logger.info(f'\n报告预览（前 500 字符）:\n{report[:500]}')

    logger.info('\n' + '=' * 60)
    logger.info('✅ 冒烟测试通过')
    logger.info('=' * 60)
    return True


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
