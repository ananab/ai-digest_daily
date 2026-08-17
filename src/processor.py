import logging
import re
from typing import List
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from .collectors.base import CollectedItem

logger = logging.getLogger(__name__)


class Processor:
    """数据处理器：去重、清洗、分类、硬性过滤"""

    # AI 相关关键词（必须包含至少一个）
    AI_KEYWORDS = [
        # 通用 AI 术语
        r'\bAI\b', r'\bA\.I\.\b', r'\bartificial intelligence\b', r'\bmachine learning\b', r'\bML\b',
        r'\bdeep learning\b', r'\bDL\b', r'\bneural network\b', r'\bLLM\b', r'\bAGI\b',
        # 大模型相关
        r'\bGPT\b', r'\bChatGPT\b', r'\bClaude\b', r'\bGemini\b', r'\bLlama\b', r'\bPaLM\b',
        r'\blarge language model\b', r'\bfoundation model\b', r'\bgenerative AI\b',
        # AI 应用
        r'\bNLP\b', r'\bnatural language processing\b', r'\bcomputer vision\b', r'\bCV\b',
        r'\bagent\b', r'\bchatbot\b', r'\bcopilot\b', r'\bAI assistant\b',
        # 中文关键词
        r'人工智能', r'机器学习', r'深度学习', r'大模型', r'大语言模型',
        r'神经网络', r'智能', r'AI', r'机器人',
        # 垂直领域 AI
        r'AI客服', r'AI助手', r'AI客服机器人', r'智能客服',
        r'user research.*AI', r'AI.*user research',
        r'OTA.*AI', r'AI.*OTA', r'travel.*AI', r'AI.*travel',
        r'AI.*SaaS', r'SaaS.*AI', r'AI platform', r'AI tool',
        # 技术术语
        r'transformer', r'attention mechanism', r'token', r'prompt', r'fine-tune',
        r'RAG', r'vector database', r'embedding', r'inference',
    ]

    # 行业分类关键词
    INDUSTRY_KEYWORDS = {
        'OTA/旅游': [
            r'\bOTA\b', r'\btravel\b', r'\bhotel\b', r'\bflight\b', r'\bbooking\b',
            r'\bExpedia\b', r'\bBooking\.com\b', r'\bAirbnb\b', r'\bTrip\.com\b',
            r'旅游', r'酒店', r'机票', r'预订', r'携程', r'飞猪', r'去哪儿',
            r'Skift', r'PhocusWire', r'环球旅讯',
        ],
        'Market Research': [
            r'user research', r'UX research', r'usability', r'user interview',
            r'social listening', r'consumer insight', r'market research',
            r'用户研究', r'用研', r'深访', r'访谈', r'用户洞察',
            r'UserWeekly', r'Dscout', r'User Interviews',
        ],
        '客服AI': [
            r'customer service', r'contact center', r'call center',
            r'AI客服', r'客服机器人', r'智能客服', r'AI assistant',
            r'Cresta', r'Decagon', r'Zendesk', r'Intercom',
        ],
        'SaaS': [
            r'SaaS', r'enterprise', r'B2B', r'AI platform', r'AI tool',
            r'Salesforce', r'HubSpot', r'Zoho', r'Notion',
            r'企业级', r'企业软件', r'企业服务',
        ],
        'To C 大模型产品': [
            r'ChatGPT', r'Claude', r'Gemini', r'Copilot',
            r'consumer.*AI', r'AI.*consumer', r'AI app',
            r'消费者', r'个人AI', r'AI应用',
        ],
    }

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        today = datetime.now()
        self.cutoff_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        self.max_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')  # T-1 (exclude today)

    def process(self, items: List[CollectedItem]) -> dict[str, List[CollectedItem]]:
        """
        处理采集数据（带硬性过滤）

        执行流程：
        1. 清洗：过滤无效数据
        2. 发布时间过滤：硬性过滤无日期的内容
        3. 日期范围过滤：硬性过滤旧内容
        4. AI相关性过滤：硬性过滤非AI内容
        5. 去重：基于标题相似度
        6. 行业分类：按行业分类
        """
        # 1. 清洗
        cleaned = self._clean(items)
        logger.info(f'清洗后: {len(cleaned)} 条 (原始 {len(items)} 条)')

        # 2. 发布时间过滤（硬性）- 丢弃没有发布日期的内容
        has_date = self._filter_by_has_date(cleaned)
        logger.info(f'有发布时间: {len(has_date)} 条 (丢弃 {len(cleaned) - len(has_date)} 条无日期内容)')

        # 3. 日期范围过滤（硬性）
        date_filtered = self._filter_by_date(has_date)
        logger.info(f'日期过滤后: {len(date_filtered)} 条 (过滤 {len(has_date) - len(date_filtered)} 条旧内容)')

        # 3. AI相关性过滤（硬性）
        ai_filtered = self._filter_by_ai_relevance(date_filtered)
        logger.info(f'AI相关性过滤后: {len(ai_filtered)} 条 (过滤 {len(date_filtered) - len(ai_filtered)} 条非AI内容)')

        # 4. 去重
        deduplicated = self._deduplicate(ai_filtered)
        logger.info(f'去重后: {len(deduplicated)} 条')

        # 5. 行业分类
        categorized = self._categorize_by_industry(deduplicated)

        # 调试日志：检查 UserWeekly 文章的分类
        userweekly_items = [item for item in deduplicated if item.source == 'User Weekly']
        if userweekly_items:
            logger.info(f'UserWeekly 文章分类调试:')
            for item in userweekly_items:
                logger.info(f'  - {item.title[:60]} -> {item.published_date}')

        for category, items_list in categorized.items():
            logger.info(f'  {category}: {len(items_list)} 条')

        return categorized

    def _is_ai_related(self, item: CollectedItem) -> bool:
        """检查内容是否与AI相关（硬性规则）"""
        text = f"{item.title} {item.summary}".lower()

        # 检查是否包含至少一个AI关键词
        for pattern in self.AI_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _filter_by_ai_relevance(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """硬性过滤非AI内容"""
        filtered = [item for item in items if self._is_ai_related(item)]

        # 记录被过滤的内容（用于调试）
        filtered_out = [item for item in items if not self._is_ai_related(item)]
        if filtered_out:
            logger.debug(f'过滤的非AI内容示例:')
            for item in filtered_out[:3]:
                logger.debug(f'  - {item.title[:80]}')

        return filtered

    def _detect_industry(self, item: CollectedItem) -> str:
        """检测内容所属行业"""
        # 首先根据 source 判断
        source_market_research = ['NNGroup', 'UXRCl', 'Condens', 'Dovetail', 'MiroResearch',
                                'Userlytics', 'Loop11', 'DelveAI', 'Lyssna',
                                'UserWeekly', 'Dscout', 'UserInterviews', 'UxRen']
        if item.source in source_market_research:
            return 'Market Research'

        # OTA/旅游 来源
        ota_sources = ['Skift', 'PhocusWire', 'HuanqiuTravel']
        if item.source in ota_sources:
            return 'OTA/旅游'

        # 客服AI 来源
        cs_sources = ['CXToday', 'CMSWire']
        if item.source in cs_sources:
            return '客服AI'

        # 基于关键词判断
        text = f"{item.title} {item.summary}".lower()
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for pattern in keywords:
                if re.search(pattern, text, re.IGNORECASE):
                    return industry

        return '其他'

    def _categorize_by_industry(self, items: List[CollectedItem]) -> dict[str, List[CollectedItem]]:
        """按行业分类（硬性规则）"""
        categorized = {
            'OTA/旅游': [],
            'Market Research': [],
            '客服AI': [],
            'SaaS': [],
            'To C 大模型产品': [],
            '其他': [],
        }

        for item in items:
            # 根据原始 category 映射到行业
            if item.category in ['news', 'startups']:
                industry = self._detect_industry(item)
            elif item.category == 'paper':
                industry = '其他'  # 论文默认放"其他"
            elif item.category == 'repo':
                industry = 'SaaS'  # 开源项目默认放"SaaS"
            else:
                industry = self._detect_industry(item)

            # Startup 融资/产品新闻：根据行业属性分到对应板块
            # 如果检测到明确行业就分到该板块，否则保持原分类
            if item.category == 'startups' and industry == '其他':
                # 用更宽松的关键词再尝试一次行业匹配
                industry = self._detect_industry_loose(item)

            categorized[industry].append(item)

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

    def _detect_industry_loose(self, item: CollectedItem) -> str:
        """宽松的行业检测（用于 startup 新闻的二次匹配）"""
        text = f"{item.title} {item.summary}".lower()

        # Startup 相关的宽松关键词映射
        loose_keywords = {
            'OTA/旅游': [
                'travel', 'hotel', 'flight', 'booking', 'tourism', 'hospitality',
                'trip', 'vacation', 'airline', 'resort', 'accommodation',
                '旅游', '酒店', '机票', '出行', '住宿', '度假',
            ],
            'Market Research': [
                'user research', 'ux research', 'usability', 'user testing',
                'user interview', 'survey', 'feedback', 'insight', 'analytics',
                '用户研究', '用研', '调研', '问卷', '访谈', '洞察',
            ],
            '客服AI': [
                'customer service', 'customer support', 'helpdesk', 'contact center',
                'call center', 'support agent', 'service bot', 'help desk',
                '客服', '客户支持', '服务中心', '呼叫中心',
            ],
            'SaaS': [
                'saas', 'b2b', 'enterprise', 'workflow', 'productivity',
                'automation', 'integration', 'api', 'platform', 'tool',
                '企业级', '工作流', '自动化', '集成',
            ],
            'To C 大模型产品': [
                'chatgpt', 'claude', 'gemini', 'copilot', 'ai assistant',
                'ai chat', 'personal ai', 'consumer', 'mobile app',
                'ai应用', 'ai助手', '个人ai',
            ],
        }

        for industry, keywords in loose_keywords.items():
            for kw in keywords:
                if kw in text:
                    return industry

        return '其他'

    def _categorize(self, items: List[CollectedItem]) -> dict[str, List[CollectedItem]]:
        """按类别分组"""
        categorized = {
            'news': [],
            'paper': [],
            'repo': [],
            'startups': [],
        }

        for item in items:
            category = item.category
            if category in categorized:
                categorized[category].append(item)
            else:
                categorized['news'].append(item)

        return categorized

    def _filter_by_has_date(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """硬性过滤：只保留有发布日期的内容"""
        filtered = []
        for item in items:
            # 优先使用 published_date 字段
            if item.published_date:
                filtered.append(item)
            else:
                # 尝试从文本中解析日期
                parsed_date = self._try_parse_date_from_text(item)
                if parsed_date:
                    item.published_date = parsed_date
                    filtered.append(item)
                else:
                    logger.debug(f'丢弃无日期内容: {item.title[:60]}')
        return filtered

    def _filter_by_date(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """硬性过滤旧内容（超过7天）和今天的内容"""
        filtered = []
        for item in items:
            # 只处理有 published_date 的内容
            if item.published_date:
                if self.cutoff_date <= item.published_date <= self.max_date:
                    filtered.append(item)
                else:
                    logger.debug(f'过滤旧内容或今天内容: {item.title[:60]} ({item.published_date})')

        return filtered

    def _try_parse_date_from_text(self, item: CollectedItem) -> str:
        """尝试从标题或摘要中解析日期"""
        text = f"{item.title} {item.summary}"

        # 匹配 "24 Oct 2025", "Jan 15, 2024", "15 Mar 2026" 等格式
        month_names = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
        }

        patterns = [
            # "24 Oct 2025" / "15 Mar 2026"
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})',
            # "Oct 24, 2025" / "Mar 15, 2026"
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2}),?\s+(\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) <= 2 and groups[0].isdigit():
                        # "24 Oct 2025" format
                        day, month_str, year = groups
                        month = month_names.get(month_str[:3].lower(), '01')
                    else:
                        # "Oct 24, 2025" format
                        month_str, day, year = groups
                        month = month_names.get(month_str[:3].lower(), '01')

                    date_str = f"{year}-{month}-{day.zfill(2)}"
                    # 验证日期格式
                    datetime.strptime(date_str, '%Y-%m-%d')
                    return date_str
                except (ValueError, KeyError):
                    continue

        return ''
