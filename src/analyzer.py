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

        # 每类取前30条给LLM筛选（已按采集顺序排序）
        trimmed = {}
        for category, items in categorized_data.items():
            if not items:
                continue
            trimmed[category] = items[:30]
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
                f'{i+1}. {item.title}\n   {item.summary}\n   链接: {item.url}\n   发布时间: {item.published_date or "未知"}'
                for i, item in enumerate(items)
            ])

            sections.append(f'【{category_cn}】\n{items_text}')

        all_data = '\n\n'.join(sections)

        # 计算时间范围
        from datetime import datetime, timedelta
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        date_range = f"{week_ago.strftime('%Y年%m月%d日')}至{now.strftime('%Y年%m月%d日')}"

        # 如果没有领域相关新闻，并行调用 LLM fallback
        domain_fallback = self._check_domain_coverage(all_data)
        if domain_fallback:
            logger.info(f'检测到 {len(domain_fallback)} 个领域缺少相关内容，并行启动 LLM fallback')
            fallback_content = await self._fetch_domain_news_parallel(domain_fallback)
            if fallback_content:
                logger.info(f'Fallback 内容预览:\n{fallback_content[:500]}...')
                all_data += f'\n\n{fallback_content}'

        prompt = f"""你是一个科技媒体编辑，特别关注以下领域：
1. OTA（在线旅游）中AI作为酒店和机票预订入口的应用
2. Market Research（市场研究、用研、深访、social listening AI平台）
3. 客服AI应用（坐席助手如Cresta，纯AI客服如Decagon）
4. SaaS（企业级AI软件、工具、平台）
5. To C 大模型产品（消费者端AI产品、大模型应用）
6. 其他AI领域（模型发布、论文、行业动态、AI Native转型、AI Native组织演变等）

**全局强制规则（必须遵守）**：

1. **所有内容必须与AI直接相关**
   - 每条新闻必须明确提及AI、人工智能、机器学习、大模型、GPT、Claude、LLM、Agent、Chatbot等AI技术关键词
   - 纯商业/财务/战略新闻，如果不涉及AI技术应用，**一律排除**

2. **🔴 严格的日期过滤（最高优先级）**
   - 只接受 {date_range} 期间发布的内容
   - 如果标题或摘要中包含旧年份（如"2025"、"2024"、"2023"），**必须排除**
   - 年度报告、季度总结、回顾性文章，除非明确标注为本周发布，**一律排除**
   - 示例：
     ❌ 排除："2025用户研究行业现状报告"（标题含2025，是年度报告）
     ❌ 排除："2024年AI行业回顾"（回顾性文章）
     ✅ 保留：本周发布的新产品公告、融资消息、技术更新

3. **特别关注**：
   - 大企业如何向AI Native转型（如传统企业引入AI改造业务流程）
   - AI Native组织的形态演变（如全员AI、扁平化AI团队、Agent-First组织等）
   - 这些内容根据其行业属性放到对应板块

请基于以下本周动态，生成一份适合飞书群播报的中文周报。

本周动态：
{all_data}

请严格按以下格式生成报告（使用中文）：

---
## ✨ 本周速览

（**必须输出**：根据以上素材写一段「本周速览」总结。要求：
- **必须输出内容**，即使只有1条也要输出
- 按简单分类：🏨 OTA/旅游、🔍 Market Research、🎧 客服AI、💼 SaaS、🤖 To C 产品、📰 其他
- 每个分类下：1-3 条要点，每条一行，以「• 」开头
- **简洁专业的表达**，清晰易读，保持正式风格
- **重点内容加粗**（用 **文字** 格式），让关键信息一眼能看到
- 不要编造素材中没有的信息
- 不要输出开场白或结尾寒暄
- 总字数控制在 300 字以内）

---
## 📎 相关链接

请按以下规则将内容分类到对应板块（每个板块都必须填写）：

---
### 🏨 OTA/旅游

- 来源：Skift、PhocusWire、环球旅讯
- 关键词：酒店、机票、预订、旅游、OTA、Booking、Expedia、Airbnb、携程、飞猪、travel AI
- **严格规则**：只包含与AI直接相关的旅游行业新闻。排除纯旅游商业新闻
- **优先包含**：OTA行业的AI Native转型案例、OTA CEO的AI相关发言、OTA创业公司融资

---
### 🔍 Market Research

- 来源：UserWeekly、Dscout、User Interviews、UXRen
- 关键词：user research、UX research、usability test、user interview、social listening、consumer insight、market research、用户研究、用研、深访、访谈、用户洞察
- **严格规则**：只包含「研究用户/市场」的AI方法和工具（访谈、问卷、可用性测试、用户洞察平台）
- **排除**：产品设计工具（Figma）、产品功能介绍、一般UX/UI技巧、**学术论文**（即使标题含"research"）、**技术基础设施**（LLM路由、模型训练等）、**纯技术benchmark**

---
### 🎧 客服AI

- 来源：CX Today、Zendesk、Intercom
- 关键词：客服、customer service、contact center、坐席、Cresta、Decagon、客服机器人、AI客服、智能客服
- **严格规则**：只包含AI客服机器人、智能坐席助手、虚拟客服助手。排除：一般CX管理、销售营销、社区讨论、人事任命

---
### 💼 SaaS

- 来源：TechCrunch、VentureBeat、ProductHunt
- 关键词：SaaS、enterprise、platform、tool、API、automation、企业级、AI平台、B2B AI、software、AI software
- **严格规则**：包含企业级AI软件、工具、平台的发布、更新、融资、商业模式。排除：纯消费者端产品

---
### 🤖 To C 大模型产品

- 来源：TechCrunch、VentureBeat、ProductHunt、OpenAI Blog、Anthropic Blog
- 关键词：consumer、ChatGPT、Claude、Gemini、Copilot、consumer app、AI assistant、AI chat、personal AI
- **严格规则**：包含消费者端AI产品、大模型应用、AI助手、个人AI工具。排除：企业级SaaS产品

---
### 📰 其他

- 关键词：模型发布、论文、行业政策、AI Native转型、AI组织演变、startup、融资、funding、观点、opinion
- **严格规则**：只有当前5个板块都不符合时才放入「其他」
- 内容类型：不匹配前5类的模型发布、学术论文、行业政策、AI Native转型、AI组织演变、行业观点、创业公司融资
- **排序规则**：AI Native转型和组织演变内容优先，其次按融资额排序

**重要规则**：
- **🔴 严格时间过滤（最高优先级）**：
  - 所有新闻必须发布于 **{date_range}**，超出此时间范围的内容一律丢弃
  - 如果标题或摘要中包含旧年份（如"2025"、"2024"），**必须排除**
  - 年度报告、季度总结、回顾性文章，**一律排除**
- **严禁重复链接**：每个URL只能出现在一个板块中
- **严禁内容重复**：同一事件/产品/功能的多条新闻必须合并为一条，选择信息最完整的版本
  - ❌ 错误示例：
    - "Google将Agentic AI引入Maps酒店搜索"
    - "Google确认Agentic酒店预订进入测试"
  - ✅ 正确示例：
    - "Google将Agentic AI引入Maps酒店搜索，已进入测试阶段"（合并为一条）
  - 合并原则：同一公司+同一产品/功能/事件 = 合并为一条
- **分类优先级**：新闻必须按以下优先级归类：
  1. 如果涉及OTA/旅游，优先放 OTA/旅游
  2. 如果涉及Market Research/用研，优先放 Market Research
  3. 如果涉及客服AI，优先放 客服AI
  4. 如果涉及企业级SaaS/工具，优先放 SaaS
  5. 如果涉及消费者端AI产品，优先放 To C 大模型产品
  6. 只有以上都不符合时，才放 其他
- **AI Native转型和AI Native组织演变**：根据行业属性放到对应板块。如：OTA企业AI转型→OTA/旅游，客服AI Native组织→客服AI，通用SaaS企业AI转型→SaaS
- **Startup融资**：根据其行业属性放到对应板块。如：旅游AI创业融资→OTA/旅游，用研AI创业融资→Market Research，不明确的→其他
- **论文**：根据其领域放到对应板块。如：旅游AI论文→OTA/旅游，不明确的→其他
- **行业观点/CEO发言**：根据其行业属性放到对应板块。如：Booking CEO谈AI→OTA/旅游，不明确的→其他
- 每个板块都必须有内容，不允许输出"无"或"今日暂无重大更新"
- 如果某个板块没有直接相关内容，按以下优先级填充：
  1. 使用其他板块中标记为该板块的内容
  2. 从现有素材中找出最相关的新闻（必须在本周时间范围内）
  3. 作为fallback，直接与LLM对话，通过websearch找到最近7天内该板块的重要新闻

**通用规则**：
- **所有英文标题必须翻译成中文**，格式：**[中文标题](url)** （English Title）
- 语言简洁专业，适合飞书群快速阅读
- 突出技术创新和实际影响
- **总量控制**：每个板块最多展示5条新闻，优先选择最重要、最有影响力的内容
- **摘要精简**：每条新闻摘要控制在30字以内，突出核心信息

**输出格式要求（必须严格遵守）**：

⚠️ **飞书卡片 Markdown 限制**：
- ❌ 不支持 `###` 标题语法
- ❌ 不支持 `>` 引用块
- ✅ 支持 `**bold**` 加粗
- ✅ 支持 `- list` 无序列表
- ✅ 支持 `[link](url)` 链接
- ✅ 支持 `---` 分隔线

每个板块使用以下格式（使用飞书支持的语法）：

---

**🏨 OTA/旅游**

- **[中文标题](url)** （English Title）
  *摘要内容...*
  `发布时间: 2026-08-14`

- **[中文标题](url)** （English Title）
  *摘要内容...*
  `发布时间: 2026-08-13`

---

**🔍 Market Research**

- **[中文标题](url)** （English Title）
  *摘要内容...*
  `发布时间: 2026-08-12`

---

以此类推。每个板块之间用 `---` 分隔。每条新闻末尾必须标注发布时间（从输入数据的"发布时间"字段获取）。"""

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
            'OTA/旅游': ['OTA', '旅游', '酒店', '机票', '预订', 'Booking', 'Expedia', 'Airbnb', 'travel'],
            'Market Research': ['用户研究', '用研', 'UX', '用户体验', 'social listening', '访谈', 'market research'],
            '客服AI': ['客服', 'customer service', 'contact center', '坐席', 'Cresta', 'Decagon'],
            'SaaS': ['SaaS', 'enterprise', 'platform', 'tool', 'API', 'automation', '企业级', 'B2B'],
            'To C 大模型产品': ['consumer', 'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'consumer app', 'AI assistant'],
            '其他': ['startup', '创业', '融资', 'funding', 'model', '论文', 'paper', '政策', 'regulation', 'AI Native'],
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
            'OTA/旅游': [
                ('https://skift.com/feed/', 'Skift'),
                ('https://www.phocuswire.com/feed/', 'PhocusWire'),
            ],
            'Market Research': [
                ('https://userweekly.com/feed/', 'UserWeekly'),
                ('https://uxplanet.org/feed', 'UXPlanet'),
            ],
            '客服AI': [
                ('https://www.cxtoday.com/feed/', 'CX Today'),
                ('https://www.zendesk.com/blog/feed/', 'Zendesk'),
                ('https://www.intercom.com/blog/feed/', 'Intercom'),
                ('https://www.salesforce.com/blog/feed/', 'Salesforce Service Cloud'),
                ('https://www.servicenow.com/blog/feed', 'ServiceNow'),
                ('https://www.freshworks.com/blog/feed', 'Freshworks'),
                ('https://www.helpscout.com/blog/feed', 'Help Scout'),
                ('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI'),
                ('https://venturebeat.com/feed/?category_name=ai', 'VentureBeat AI'),
            ],
            'SaaS': [
                ('https://techcrunch.com/feed/', 'TechCrunch'),
                ('https://venturebeat.com/feed/', 'VentureBeat'),
                ('https://www.producthunt.com/feed', 'ProductHunt'),
            ],
            'To C 大模型产品': [
                ('https://openai.com/blog/rss.xml', 'OpenAI Blog'),
                ('https://www.anthropic.com/feed', 'Anthropic Blog'),
                ('https://www.producthunt.com/feed', 'ProductHunt'),
            ],
            '其他': [
                ('https://techcrunch.com/feed/', 'TechCrunch'),
                ('https://venturebeat.com/feed/', 'VentureBeat'),
                ('https://arxiv.org/rss/cs.AI', 'arXiv AI'),
                ('https://towardsdatascience.com/feed', 'Towards Data Science'),
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
            'OTA/旅游': ['travel AI', 'hotel AI', 'booking AI', 'flight AI', '旅游AI', '酒店AI', '机票AI', 'OTA AI', 'Expedia AI', 'Booking.com AI', 'Airbnb AI', '携程AI', '飞猪AI', 'travel chatbot', 'travel agent', 'travel personalization'],
            'Market Research': ['user research', 'UX research', 'user study', 'usability', '用户研究', '用研', '深访', '用户体验研究', 'social listening', 'user insight', 'user interview', 'usability test', 'UX insight', '用户洞察AI', 'UX AI tool'],
            '客服AI': ['customer service AI', 'customer support AI', 'service chatbot', 'support chatbot', '客服AI', '客服机器人', '智能客服', 'service agent AI', 'support agent AI', 'contact center AI', 'call center AI', 'service bot', 'support bot', 'CX AI assistant', 'service copilot', 'conversational AI', 'virtual agent'],
            'SaaS': ['SaaS', 'enterprise', 'platform', 'tool', 'API', 'automation', '企业级', 'B2B', 'software', 'AI platform', 'AI tool'],
            'To C 大模型产品': ['consumer', 'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'AI assistant', 'AI chat', 'personal AI', 'consumer app'],
            '其他': ['AI', 'model', '论文', 'paper', 'startup', '政策', 'regulation', 'AI Native', 'AI organization'],
        }

        items = []
        keywords = filter_keywords.get(domain, [])

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
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
                except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                    logger.error(f'{domain}: {source_name} RSS 超时: {type(e).__name__}')
                except httpx.HTTPError as e:
                    logger.error(f'{domain}: {source_name} RSS HTTP错误: {type(e).__name__}: {e}')
                except Exception as e:
                    logger.error(f'{domain}: {source_name} RSS 抓取失败: {type(e).__name__}: {e}')

        # 如果过滤后结果少于3条，触发web search fallback
        if len(items) < 3:
            logger.info(f'{domain}: RSS过滤后仅 {len(items)} 条，启用 web search 补充')
            web_results = await self._llm_web_search(domain)
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

        # RSS 全部失败，用 LLM web search
        logger.info(f'{domain}: RSS 失败，启用 LLM 联网搜索')
        return await self._llm_web_search(domain)

    async def _llm_web_search(self, domain: str) -> str:
        """使用 LLM 联网搜索获取领域新闻（只用 Kimi，DeepSeek 无联网能力）"""
        # 只用 Kimi web search（有真实联网能力）
        if self.kimi_client:
            return await self._kimi_web_search(domain)

        logger.error(f'{domain}: Kimi 不可用，无法进行联网搜索')
        return ''

    async def _deepseek_web_search(self, domain: str) -> str:
        """使用 DeepSeek 联网搜索获取领域新闻"""
        import httpx
        from datetime import date, timedelta

        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        time_range = f'{seven_days_ago.strftime("%Y-%m-%d")}至{today.strftime("%Y-%m-%d")}'

        domain_queries = {
            'OTA/旅游': f'{time_range} OTA旅游AI 酒店预订 机票 Booking Expedia 携程最新动态',
            'Market Research': f'{time_range} 用户研究 UX Research social listening AI平台最新动态',
            '客服AI': f'{time_range} 客服AI customer service AI Cresta Decagon 智能客服最新动态',
            'SaaS': f'{time_range} 企业级AI SaaS 软件 平台 工具 最新动态',
            'To C 大模型产品': f'{time_range} 消费者端AI产品 ChatGPT Claude Gemini 大模型应用最新动态',
            '其他': f'{time_range} AI行业 模型发布 论文 政策 AI Native转型 最新动态',
        }
        query = domain_queries.get(domain, f'{time_range} {domain} 最新动态')

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{config.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.deepseek_model,
                        "max_tokens": 3000,
                        "messages": [
                            {"role": "system", "content": f"你是一个科技新闻编辑。今天是{today.strftime('%Y-%m-%d')}。请搜索并整理{time_range}期间的相关新闻。每条新闻需包含标题、来源和URL链接。"},
                            {"role": "user", "content": f"请搜索以下内容，返回{time_range}期间的新闻（3-5条），格式：标题 - 来源 - URL\n\n{query}"}
                        ]
                    }
                )

                if response.status_code != 200:
                    logger.error(f'{domain}: DeepSeek API 返回 {response.status_code}: {response.text[:200]}')
                    return ''

                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

                refusal_phrases = ['无法提供', '无法访问', '无法确认', '很抱歉', '抱歉，我', '无法验证', '无法搜索']
                has_refusal = any(phrase in content for phrase in refusal_phrases)

                if not has_refusal and len(content) > 50:
                    result = f'【{domain}】\n{content}'
                    logger.info(f'{domain}: DeepSeek 联网搜索成功')
                    return result
                else:
                    logger.warning(f'{domain}: DeepSeek 联网搜索返回空或拒绝')
                    return ''

        except httpx.TimeoutException as e:
            logger.error(f'{domain}: DeepSeek 联网搜索超时: {type(e).__name__}')
            return ''
        except httpx.ConnectError as e:
            logger.error(f'{domain}: DeepSeek 联网搜索连接失败: {type(e).__name__}')
            return ''
        except httpx.HTTPStatusError as e:
            logger.error(f'{domain}: DeepSeek 联网搜索HTTP错误: {e.response.status_code} - {e.response.text[:200]}')
            return ''
        except Exception as e:
            logger.error(f'{domain}: DeepSeek 联网搜索异常: {type(e).__name__}: {e}')
            return ''

    async def _kimi_web_search(self, domain: str) -> str:
        """使用 Kimi 联网搜索获取领域新闻"""
        import httpx
        from datetime import date, timedelta

        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        time_range = f'{seven_days_ago.strftime("%Y-%m-%d")}至{today.strftime("%Y-%m-%d")}'

        domain_queries = {
            'OTA/旅游': f'{time_range} OTA旅游AI 酒店预订 机票 Booking Expedia 携程最新动态',
            'Market Research': f'{time_range} 用户研究 UX Research social listening AI平台最新动态',
            '客服AI': f'{time_range} 客服AI customer service AI Cresta Decagon 智能客服最新动态',
            'SaaS': f'{time_range} 企业级AI SaaS 软件 平台 工具 最新动态',
            'To C 大模型产品': f'{time_range} 消费者端AI产品 ChatGPT Claude Gemini 大模型应用最新动态',
            '其他': f'{time_range} AI行业 模型发布 论文 政策 AI Native转型 最新动态',
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
                    logger.warning(f'{domain}: Kimi 联网搜索返回空或拒绝 (长度: {len(content)}, 拒绝词: {has_refusal})')
                    logger.debug(f'{domain}: Kimi 返回内容: {content[:200]}')
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
            'OTA/旅游': '🏨 OTA/旅游',
            'Market Research': '🔍 Market Research',
            '客服AI': '💬 客服AI',
            'SaaS': '📊 SaaS',
            'To C 大模型产品': '🤖 To C 大模型产品',
            '其他': '📋 其他',
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