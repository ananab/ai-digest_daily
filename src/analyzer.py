import logging
import asyncio
from typing import List
from openai import OpenAI
from .config import config
from .collectors.base import CollectedItem

logger = logging.getLogger(__name__)


class Analyzer:
    """Kimi (Moonshot AI) 智能分析器"""

    def __init__(self):
        self._deepseek_client = None
        self._kimi_client = None

    @property
    def deepseek_client(self):
        if self._deepseek_client is None and config.deepseek_api_key:
            self._deepseek_client = OpenAI(
                api_key=config.deepseek_api_key,
                base_url=config.deepseek_base_url,
            )
        return self._deepseek_client

    @property
    def kimi_client(self):
        if self._kimi_client is None and config.kimi_api_key:
            self._kimi_client = OpenAI(
                api_key=config.kimi_api_key,
                base_url="https://api.moonshot.cn/v1",
            )
        return self._kimi_client

    async def analyze(
        self,
        categorized_data: dict[str, List[CollectedItem]]
    ) -> dict:
        """
        生成分析报告

        Args:
            categorized_data: 分类后的数据 {'news': [...], 'paper': [...], ...}

        Returns:
            分析报告字典
        """
        logger.info('开始生成报告...')

        # 每类取前10条（已按采集顺序排序）
        trimmed = {}
        for category, items in categorized_data.items():
            if not items:
                continue
            trimmed[category] = items[:10]
            logger.info(f'{category}: {len(items)} 条 → 取前 {len(trimmed[category])} 条')

        report = await self._generate_report(trimmed)

        return report

    async def _generate_report(self, trimmed_data: dict) -> dict:
        """生成深度分析报告"""

        # 构建输入数据
        sections = []
        for category, items in trimmed_data.items():
            if not items:
                continue

            category_cn = {
                'news': 'AI 新闻热点',
                'paper': '学术论文',
                'repo': '开源项目',
                'startups': 'Startups',
            }.get(category, category)

            items_text = '\n'.join([
                f'{i+1}. {item.title}\n   {item.summary}\n   链接: {item.url}'
                for i, item in enumerate(items)
            ])

            sections.append(f'【{category_cn}】\n{items_text}')

        all_data = '\n\n'.join(sections)

        # 如果没有领域相关新闻，并行调用 LLM fallback
        domain_fallback = self._check_domain_coverage(all_data)
        if domain_fallback:
            logger.info(f'检测到 {len(domain_fallback)} 个领域缺少相关内容，并行启动 LLM fallback')
            fallback_content = await self._fetch_domain_news_parallel(domain_fallback)
            if fallback_content:
                logger.info(f'Fallback 内容预览:\n{fallback_content[:500]}...')
                all_data += f'\n\n{fallback_content}'

        prompt = f"""你是一个科技媒体编辑，特别关注以下领域：
1. OTA行业（在线旅游）中AI作为酒店和机票预订入口的应用
2. 用户研究公司/创业公司（用研、深度访谈、social listening AI平台）
3. 客服AI应用（坐席助手如Cresta，纯AI客服如Decagon）
4. 通用AI技术、创业公司、学术研究

请基于以下本周动态，生成一份适合飞书群播报的中文周报。

本周动态：
{all_data}

请严格按以下格式生成报告（使用中文）：

## 🔍 本周速览
（你是科技媒体编辑，请根据以上素材写一段「本周速览」总结。要求：
- 5-8 条要点，每条一行，以「• 」开头
- **简洁专业的表达**，清晰易读，保持正式风格
- **重点内容加粗**（用 **文字** 格式），让关键信息一眼能看到
- 优先关注上述4个领域（OTA/用研/客服AI/通用AI）
- 不要编造素材中没有的信息
- 不要输出开场白或结尾寒暄
- 总字数控制在 300 字以内）

## 📎 相关链接

请按以下规则将内容分类到对应板块（每个板块都必须填写）：

**OTA与旅游AI**
- 来源：Skift、PhocusWire、环球旅讯
- 标记：【OTA与旅游AI】
- 关键词：酒店、机票、预订、旅游、OTA、Booking、Expedia、Airbnb、携程、飞猪

**用户研究AI**
- 来源：UserWeekly、Dscout、User Interviews、UXRen
- 标记：【用户研究AI】
- 关键词：用户研究、用研、深访、访谈、UX、用户体验、social listening、用户洞察

**客服AI**
- 来源：CX Today、Zendesk、Intercom
- 标记：【客服AI】
- 关键词：客服、customer service、contact center、坐席、Cresta、Decagon、客服机器人、AI agent
- **严格规则**：只包含AI客服机器人、智能坐席助手、虚拟客服助手相关内容。排除：一般CX管理、销售营销、社区讨论、人事任命（除非明确涉及AI客服）

**模型发布/更新**
- 标记：【模型发布/更新】
- 关键词：GPT、Claude、Gemini、Llama、模型、model、开源模型

**产品发布/更新**
- 标记：【产品发布/更新】
- 关键词：发布、launch、release、product、产品、工具、tool、API

**Startups**
- 来源：TechCrunch AI、Newcomer、ProductHunt
- 标记：【Startups】
- 关键词：startup、创业、融资、funding

**行业动态**
- 标记：【行业动态】
- 关键词：政策、regulation、合作、partnership、市场、market、收购、acquisition

**论文研究**
- 标记：【论文研究】
- 关键词：论文、paper、arxiv、研究、research、HuggingFace

**技巧与观点**
- 标记：【技巧与观点】
- 关键词：技巧、实践、practice、观点、opinion、best practice、tutorial、guide
- 要求：每条内容必须包含标题、链接和50字以内的中文摘要

**重要规则**：
- 每个板块都必须有内容，不允许输出"无"或"今日暂无重大更新"
- 如果某个板块没有直接相关内容，使用其他板块中标记为该板块的内容，或从现有素材中找出最相关的新闻
- 对于标记为【板块名称】的内容，直接放入对应的板块
- **严禁强行归类**：如果某条新闻明显不属于该板块主题，不要为了填满板块而强行放入。宁可放相关内容到最合适的板块，也不要放入不相关的新闻
- **客服AI板块特别注意**：只放AI客服机器人、智能坐席助手、虚拟客服助手。不要放一般CX管理、销售营销、社区讨论、纯人事任命

**通用规则**：
- **所有英文标题必须翻译成中文**，格式：[中文标题](url)（原标题：English Title）
- 语言简洁专业，适合飞书群快速阅读
- 链接格式: [标题](url)
- 突出技术创新和实际影响
- 优先突出OTA、用户研究、客服AI三个重点领域"""

        report_text = None
        llm_used = None

        # 1. 尝试 DeepSeek (primary)
        if self.deepseek_client:
            try:
                logger.info('使用 DeepSeek 生成报告...')
                response = self.deepseek_client.chat.completions.create(
                    model=config.deepseek_model,
                    max_tokens=15000,
                    messages=[
                        {'role': 'system', 'content': '你是一个科技媒体编辑，负责生成AI领域周报。'},
                        {'role': 'user', 'content': prompt},
                    ],
                )
                if response.choices and response.choices[0].message.content:
                    report_text = response.choices[0].message.content
                    llm_used = 'DeepSeek'
                    logger.info('DeepSeek 生成成功')
            except Exception as e:
                logger.error(f'DeepSeek 生成失败: {e}')

        # 2. 尝试 Kimi (backup)
        if not report_text and self.kimi_client:
            try:
                logger.info('使用 Kimi 生成报告...')
                response = self.kimi_client.chat.completions.create(
                    model=config.kimi_model_report,
                    max_tokens=15000,
                    messages=[
                        {'role': 'system', 'content': '你是一个科技媒体编辑，负责生成AI领域周报。'},
                        {'role': 'user', 'content': prompt},
                    ],
                )
                if response.choices and response.choices[0].message.content:
                    report_text = response.choices[0].message.content
                    llm_used = 'Kimi'
                    logger.info('Kimi 生成成功')
            except Exception as e:
                logger.error(f'Kimi 生成失败: {e}')

        if report_text:
            return {'report': report_text, 'data': trimmed_data, 'llm_used': llm_used}
        else:
            logger.error('DeepSeek 和 Kimi 都失败，使用 fallback 报告')
            return {'report': self._fallback_report(trimmed_data), 'data': trimmed_data}

    def _check_domain_coverage(self, all_data: str) -> list[str]:
        """检查哪些领域缺少相关内容"""
        missing = []
        keywords_map = {
            'OTA与旅游AI': ['OTA', '旅游', '酒店', '机票', '预订', 'Booking', 'Expedia', 'Airbnb'],
            '用户研究AI': ['用户研究', '用研', 'UX', '用户体验', 'social listening', '访谈'],
            '客服AI': ['客服', 'customer service', 'contact center', '坐席', 'Cresta', 'Decagon'],
            'Startups': ['startup', '创业', '融资', 'funding', 'TechCrunch', 'Newcomer', 'ProductHunt', 'seed', 'series'],
            '模型发布/更新': ['GPT', 'Claude', 'Gemini', 'Llama', '模型', 'model', 'open-source', '开源模型'],
            '产品发布/更新': ['发布', 'launch', 'release', 'product', '产品', '工具', 'tool', 'API'],
            '行业动态': ['政策', 'regulation', '合作', 'partnership', '市场', 'market', '收购', 'acquisition'],
            '论文研究': ['论文', 'paper', 'arxiv', '研究', 'research', 'HuggingFace'],
            '技巧与观点': ['技巧', '实践', 'practice', '观点', 'opinion', 'best practice', 'tutorial', 'guide'],
        }

        for domain, keywords in keywords_map.items():
            if not any(kw in all_data for kw in keywords):
                missing.append(domain)

        return missing

    async def _fetch_domain_news_parallel(self, domains: list[str]) -> str:
        """并行获取缺失领域的最新消息（使用RSS真实抓取）"""
        import httpx
        import feedparser
        from bs4 import BeautifulSoup

        # 每个领域的备用RSS源
        domain_feeds = {
            'OTA与旅游AI': [
                ('https://skift.com/feed/', 'Skift'),
                ('https://www.phocuswire.com/feed/', 'PhocusWire'),
            ],
            '用户研究AI': [
                ('https://userweekly.com/feed/', 'UserWeekly'),
                ('https://uxplanet.org/feed', 'UXPlanet'),
            ],
            '客服AI': [
                ('https://www.cxtoday.com/feed/', 'CX Today'),
                ('https://www.zendesk.com/blog/feed/', 'Zendesk'),
                ('https://www.intercom.com/blog/feed/', 'Intercom'),
                ('https://www.salesforce.com/blog/feed/', 'Salesforce Service Cloud'),
            ],
            'Startups': [
                ('https://techcrunch.com/feed/', 'TechCrunch'),
                ('https://www.producthunt.com/feed', 'ProductHunt'),
            ],
            '模型发布/更新': [
                ('https://openai.com/blog/rss.xml', 'OpenAI Blog'),
                ('https://www.anthropic.com/feed', 'Anthropic Blog'),
                ('https://huggingface.co/blog/feed.xml', 'HuggingFace Blog'),
            ],
            '产品发布/更新': [
                ('https://openai.com/blog/rss.xml', 'OpenAI Blog'),
                ('https://www.anthropic.com/feed', 'Anthropic Blog'),
                ('https://www.producthunt.com/feed', 'ProductHunt'),
            ],
            '行业动态': [
                ('https://techcrunch.com/feed/', 'TechCrunch'),
                ('https://venturebeat.com/feed/', 'VentureBeat'),
                ('https://www.theverge.com/rss/ai-artificial-intelligence/index.xml', 'The Verge AI'),
            ],
            '论文研究': [
                ('https://arxiv.org/rss/cs.AI', 'arXiv AI'),
                ('https://paperswithcode.com/latest', 'Papers With Code'),
            ],
            '技巧与观点': [
                ('https://towardsdatascience.com/feed', 'Towards Data Science'),
                ('https://machinelearningmastery.com/feed/', 'ML Mastery'),
            ]
        }

        tasks = []
        for domain in domains:
            feeds = domain_feeds.get(domain, [])
            if feeds:
                tasks.append(self._fetch_from_feeds(domain, feeds))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, str) and r:
                valid_results.append(r)

        return '\n\n'.join(valid_results)

    async def _fetch_from_feeds(self, domain: str, feeds: list) -> str:
        """从RSS源抓取最新内容，过滤不相关内容，不足时用Kimi联网搜索"""
        import httpx
        import feedparser
        from bs4 import BeautifulSoup
        from datetime import date

        # 每个领域的过滤关键词（必须包含至少一个）
        filter_keywords = {
            'OTA与旅游AI': ['AI', '人工智能', 'machine learning', 'chatbot', 'agent', '智能', '自动化', 'GPT', 'LLM', 'recommendation', 'personalization'],
            '用户研究AI': ['AI', '人工智能', 'machine learning', 'NLP', 'sentiment', 'analysis', 'automation', 'GPT', 'LLM', 'insight'],
            '客服AI': ['AI', 'agent', 'chatbot', 'virtual assistant', 'automation', 'GPT', 'LLM', 'copilot', 'customer service', 'support', 'bot', '机器人', '客服', '智能客服'],
            'Startups': ['AI', 'startup', 'funding', 'raise', 'launch', 'Series', 'seed', 'venture', 'investment', 'AI startup'],
            '模型发布/更新': ['model', 'release', 'update', 'version', 'launch', 'GPT', 'Claude', 'Gemini', 'Llama', 'open-source', '模型'],
            '产品发布/更新': ['launch', 'release', 'update', 'product', 'feature', 'API', 'tool', 'platform', '发布', '上线'],
            '行业动态': ['regulation', 'policy', 'partnership', 'acquisition', 'market', 'industry', 'trend', '政策', '监管', '合作'],
            '论文研究': ['paper', 'research', 'study', 'arxiv', 'paper', 'benchmark', '论文', '研究'],
            '技巧与观点': ['tutorial', 'guide', 'best practice', 'how to', 'tips', '技巧', '教程', '实践'],
        }

        items = []
        keywords = filter_keywords.get(domain, [])

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for feed_url, source_name in feeds:
                try:
                    response = await client.get(feed_url)
                    if response.status_code != 200:
                        logger.warning(f'{domain}: {source_name} RSS 返回 {response.status_code}')
                        continue

                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:10]:  # 多抓一些以便过滤
                        title = entry.get('title', '').strip()
                        link = entry.get('link', '')

                        # 清理摘要
                        summary = ''
                        if hasattr(entry, 'summary'):
                            soup = BeautifulSoup(entry.summary, 'html.parser')
                            summary = soup.get_text().strip()
                        elif hasattr(entry, 'description'):
                            soup = BeautifulSoup(entry.description, 'html.parser')
                            summary = soup.get_text().strip()
                        if len(summary) > 200:
                            summary = summary[:200] + '...'

                        # 关键词过滤：标题或摘要必须包含至少一个关键词
                        if not title:
                            continue

                        text_to_check = (title + ' ' + summary).lower()
                        if keywords and not any(kw.lower() in text_to_check for kw in keywords):
                            logger.debug(f'{domain}: 跳过不相关内容 "{title[:50]}..."')
                            continue

                        items.append({
                            'title': title,
                            'url': link,
                            'summary': summary,
                            'source': source_name
                        })
                except Exception as e:
                    logger.error(f'{domain}: {source_name} RSS 抓取失败: {e}')

        # 如果过滤后结果少于3条，触发web search fallback
        if len(items) < 3:
            logger.info(f'{domain}: RSS过滤后仅 {len(items)} 条，启用 Kimi 联网搜索补充')
            web_results = await self._kimi_web_search(domain)
            if web_results:
                return web_results  # 直接使用web搜索结果

        if items:
            formatted = [f'【{domain}】']
            for item in items[:5]:
                line = f"{item['title']}"
                if item['url']:
                    line += f" - {item['url']}"
                if item['summary']:
                    line += f"\n   {item['summary']}"
                formatted.append(line)
            result = '\n'.join(formatted)
            logger.info(f'{domain}: RSS 获取到 {len(items)} 条（过滤后）')
            return result

        # RSS 全部失败，用 Kimi web_search
        logger.info(f'{domain}: RSS 失败，启用 Kimi 联网搜索')
        return await self._kimi_web_search(domain)

    async def _kimi_web_search(self, domain: str) -> str:
        """使用 Kimi 联网搜索获取领域新闻"""
        import httpx
        from datetime import date, timedelta

        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        time_range = f'{seven_days_ago.strftime("%Y-%m-%d")}至{today.strftime("%Y-%m-%d")}'

        domain_queries = {
            'OTA与旅游AI': f'{time_range} OTA旅游AI 酒店预订 机票 Booking Expedia 携程最新动态',
            '用户研究AI': f'{time_range} 用户研究 UX Research social listening AI平台最新动态',
            '客服AI': f'{time_range} 客服AI customer service AI Cresta Decagon 智能客服最新动态',
            'Startups': f'{time_range} AI创业公司 融资 产品发布 TechCrunch最新动态',
            '模型发布/更新': f'{time_range} 大语言模型 发布 GPT Claude Gemini Llama 开源模型',
            '产品发布/更新': f'{time_range} AI产品 工具 应用 发布 更新 OpenAI Anthropic',
            '行业动态': f'{time_range} AI行业 政策 合作 市场 收购 投资',
            '论文研究': f'{time_range} AI论文 研究 arxiv 深度学习 机器学习',
            '技巧与观点': f'{time_range} AI最佳实践 技巧 教程 观点 prompt engineering',
        }
        query = domain_queries.get(domain, f'{time_range} {domain} 最新动态')

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.kimi_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.kimi_model_report,
                        "max_tokens": 3000,
                        "messages": [
                            {"role": "system", "content": f"你是一个科技新闻编辑。今天是{today.strftime('%Y-%m-%d')}。请搜索并整理{time_range}期间的相关新闻。每条新闻需包含标题、来源和URL链接。"},
                            {"role": "user", "content": f"请搜索以下内容，返回{time_range}期间的新闻（3-5条），格式：标题 - 来源 - URL\n\n{query}"}
                        ],
                        "tools": [
                            {
                                "type": "builtin_function",
                                "function": {
                                    "name": "$web_search"
                                }
                            }
                        ]
                    }
                )

                data = response.json()
                content = data['choices'][0]['message']['content'].strip()

                refusal_phrases = ['无法提供', '无法访问', '无法确认', '很抱歉', '抱歉，我', '无法验证', '无法搜索']
                has_refusal = any(phrase in content for phrase in refusal_phrases)

                if not has_refusal and len(content) > 50:
                    result = f'【{domain}】\n{content}'
                    logger.info(f'{domain}: Kimi 联网搜索成功')
                    return result
                else:
                    logger.warning(f'{domain}: Kimi 联网搜索返回空或拒绝')
                    return ''

        except Exception as e:
            logger.error(f'{domain}: Kimi 联网搜索失败: {e}')
            return ''

    def _fallback_report(self, data: dict) -> str:
        """降级报告：不使用 LLM API"""
        from datetime import date

        today = date.today().isoformat()
        lines = [f'# 🤖 AI 前沿周报 | {today}\n']
        lines.append('⚠️ **降级报告**：LLM 生成失败，以下为原始数据\n')

        category_cn = {
            'news': '📰 本周热点',
            'paper': '📄 论文精选',
            'repo': '🛠️ 开源项目',
            'startups': '🚀 Startups',
        }

        # 领域板块
        domain_sections = {
            'OTA与旅游AI': '🏨 OTA与旅游AI',
            '用户研究AI': '🔍 用户研究AI',
            '客服AI': '💬 客服AI',
            '技巧与观点': '💡 技巧与观点',
        }

        # 先输出领域板块
        for domain_key, domain_name in domain_sections.items():
            items = data.get(domain_key, [])
            if not items:
                continue

            lines.append(f'\n## {domain_name}\n')
            for i, item in enumerate(items[:5], 1):
                lines.append(f'{i}. [{item.title}]({item.url})')
                if item.summary:
                    lines.append(f'   {item.summary[:100]}...' if len(item.summary) > 100 else f'   {item.summary}')

        # 再输出主分类
        for category, items in data.items():
            if not items or category in domain_sections:
                continue

            lines.append(f'\n## {category_cn.get(category, category)}\n')
            for i, item in enumerate(items[:5], 1):
                lines.append(f'{i}. [{item.title}]({item.url})')
                if item.summary:
                    lines.append(f'   {item.summary[:100]}...' if len(item.summary) > 100 else f'   {item.summary}')

        return '\n'.join(lines)
