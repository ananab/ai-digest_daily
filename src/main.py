import asyncio
import logging
import sys
from datetime import date

from .config import config
from .collectors.aihot import AIHotCollector
from .collectors.huggingface import HuggingFaceCollector
from .collectors.arxiv import ArxivCollector
from .collectors.github_trending import GitHubTrendingCollector
from .collectors.skift import SkiftCollector
from .collectors.phocuswire import PhocusWireCollector
from .collectors.huanqiu_travel import HuanqiuTravelCollector
from .collectors.userweekly import UserWeeklyCollector
from .collectors.dscout import DscoutCollector
from .collectors.userinterviews import UserInterviewsCollector
from .collectors.uxren import UxRenCollector
from .collectors.cxtoday import CXTodayCollector
from .collectors.cmswire import CMSWireCollector
from .collectors.venturebeat_ai import VentureBeatAICollector
from .collectors.startups import StartupsCollector
from .processor import Processor
from .analyzer import Analyzer
from .publisher import FeishuPublisher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def _safe_collect(collector):
    """安全采集：单个采集器失败不影响其他"""
    try:
        items = await collector.collect()
        logger.info(f'{collector.name}: {len(items)} 条')
        return items
    except Exception as e:
        logger.error(f'{collector.name} 采集异常: {e}')
        return []
    finally:
        try:
            await collector.close()
        except Exception:
            pass


async def collect_all():
    """并发采集所有数据源（容错模式）"""
    collectors = [
        AIHotCollector(),
        HuggingFaceCollector(),
        ArxivCollector(),
        GitHubTrendingCollector(),
        # OTA/旅游
        SkiftCollector(),
        PhocusWireCollector(),
        HuanqiuTravelCollector(),
        # 用户研究
        UserWeeklyCollector(),
        DscoutCollector(),
        UserInterviewsCollector(),
        UxRenCollector(),
        # 客服AI/CX
        CXTodayCollector(),
        CMSWireCollector(),
        # AI新闻
        VentureBeatAICollector(),
        # Startups
        StartupsCollector(),
    ]

    logger.info(f'开始采集，共 {len(collectors)} 个数据源...')

    # 并发执行所有采集任务
    results = await asyncio.gather(
        *[_safe_collect(c) for c in collectors],
        return_exceptions=False,
    )

    all_items = []
    for items in results:
        if isinstance(items, list):
            all_items.extend(items)

    logger.info(f'总计采集: {len(all_items)} 条')
    return all_items


async def run():
    """主流程"""
    logger.info(f'AI Weekly Digest 启动 - {date.today().isoformat()}')

    # 验证配置
    try:
        config.validate()
    except ValueError as e:
        logger.error(f'配置错误: {e}')
        return False

    # 1. 采集
    logger.info('=' * 50)
    logger.info('阶段 1: 数据采集')
    logger.info('=' * 50)
    all_items = await collect_all()

    if not all_items:
        logger.warning('未采集到任何数据')
        return False

    # 2. 处理
    logger.info('=' * 50)
    logger.info('阶段 2: 数据处理')
    logger.info('=' * 50)
    processor = Processor()
    categorized = processor.process(all_items)

    total_processed = sum(len(v) for v in categorized.values())
    if total_processed == 0:
        logger.warning('处理后无有效数据')
        return False

    # 3. 分析
    logger.info('=' * 50)
    logger.info('阶段 3: Kimi API 智能分析')
    logger.info('=' * 50)
    analyzer = Analyzer()
    report = await analyzer.analyze(categorized)

    if not report.get('report'):
        logger.warning('分析报告为空')
        return False

    # 4. 推送
    logger.info('=' * 50)
    logger.info('阶段 4: 飞书推送')
    logger.info('=' * 50)
    async with FeishuPublisher() as publisher:
        success = await publisher.publish(report)

    if success:
        logger.info('✅ 全流程完成')
    else:
        logger.error('❌ 飞书推送失败')

    return success


def main():
    """入口函数"""
    success = asyncio.run(run())
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
