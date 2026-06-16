"""
Agent Service - 大件运输智能体。

流程: 关键词搜索知识库 → 规划路线 → DeepSeek 综合回答

检索策略: 直接对 Markdown 文件做关键词搜索（高速名、地名、桩号），
比 MaxKB embedding 搜索更准确可靠（适合领域专用知识库）。
"""
import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import AsyncGenerator, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)

# Markdown 文件目录（Spider 输出）
SPIDER_DATA = Path(__file__).resolve().parent.parent.parent / "spider" / "data" / "road_details"

# 法规知识库查询关键词（用于检测用户是否在询问法规相关问题）
REGULATION_KEYWORDS = [
    "超限", "大件运输", "许可证", "通行证", "罚款", "处罚",
    "护送", "护送车辆", "警车", "护送方案",
    "申请材料", "申请表", "审批", "办理时限", "有效期",
    "分类", "一类", "二类", "三类", "分类标准",
    "尺寸限制", "高度限制", "宽度限制", "长度限制", "重量限制",
    "轴数", "轴重", "超重", "超高", "超宽", "超长",
    "公路管理机构", "交通运输部", "法规", "规定", "条例",
    "违法", "违规", "合规", "标准",
    "大件", "特种运输", "超限运输",
]


class AgentService:
    """大件运输智能助手 —— 关键词检索 + 路线规划 + LLM 合成。"""

    def __init__(self):
        self.llm_base = settings.DEEPSEEK_BASE_URL
        self.llm_key = settings.DEEPSEEK_API_KEY
        self.llm_model = settings.DEEPSEEK_MODEL

    # ---- 关键词检索 ----

    @staticmethod
    def _search_files(query: str, max_files: int = 15) -> str:
        """
        对 Spider 输出的 Markdown 文件做关键词搜索。
        提取 query 中的高速名、地名、编号作为关键词，匹配文件内容。
        返回匹配到的文档内容拼接。
        """
        if not SPIDER_DATA.exists():
            return ""

        # 提取关键词：高速名（XX高速）、编号（G15/S21等）、地名
        keywords = set()
        # 高速名
        for m in re.finditer(r'[一-龥]{1,4}高速', query):
            keywords.add(m.group())
        # 编号
        for m in re.finditer(r'[GSgs]\d{1,3}', query):
            keywords.add(m.group().upper())
        # 地名（2-4字中文）
        for m in re.finditer(r'[一-龥]{2,4}', query):
            w = m.group()
            if w not in ('请问', '最近', '有什么', '怎么样', '如何', '怎么', '施工', '路段', '路线',
                         '规划', '导航', '有没有', '知道', '帮我', '可以', '是否', '福建高速'):
                keywords.add(w)

        logger.info(f"Search keywords: {keywords}")

        # 收集所有 .md 文件
        all_files = list(SPIDER_DATA.rglob("*.md"))
        if not all_files:
            return ""

        # 匹配评分：文件名匹配 +1，内容匹配每个关键词 +1
        scored = []
        for fp in all_files:
            try:
                raw = fp.read_text(encoding='utf-8')
            except Exception:
                continue
            score = 0
            fname = fp.name
            for kw in keywords:
                if kw in fname:
                    score += 3
                if kw in raw:
                    score += 1
            if score > 0:
                scored.append((score, fp, raw))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_files]

        if not top:
            return ""

        parts = []
        for score, fp, raw in top:
            # 提取核心信息行
            lines = raw.split('\n')
            info = []
            for line in lines:
                line = line.strip()
                if line.startswith('##') or line.startswith('**'):
                    info.append(line)
                elif any(kw in line for kw in keywords):
                    info.append(line)
            parts.append(f"--- 文件: {fp.name} (相关度: {score}) ---\n" + '\n'.join(info[:15]))

        result = '\n\n'.join(parts)
        logger.info(f"Search found {len(top)} docs, {len(result)} chars")
        return result

    # ---- 综合路线评估（桥梁 + 施工 + 尺寸合规） ----

    @staticmethod
    def _assess_route_comprehensive(route_text: str, vehicle: dict) -> tuple:
        """使用 route_assessor 对路线进行综合评估，返回 (桥梁文本, 施工文本)."""
        bridge_text = ""
        construction_text = ""

        try:
            from app.services.route_assessor import route_assessor

            # Parse route info from the formatted route text
            route_data = {}
            hw_codes = list(set(re.findall(r'([GS]\d{1,4})', route_text)))

            for line in route_text.split('\n'):
                line = line.strip()
                if '路径:' in line:
                    route_data['route_description'] = line.split('路径:', 1)[-1].strip()
                if '隧道:' in line:
                    try:
                        route_data['tunnel_count'] = int(
                            re.search(r'(\d+)', line).group(1)
                        )
                    except Exception:
                        pass
                # Extract distance: "85.0km" or similar
                dist_match = re.search(r'([\d.]+)\s*km', line)
                if dist_match and 'distance' not in route_data:
                    try:
                        route_data['distance'] = int(float(dist_match.group(1)) * 1000)
                    except Exception:
                        pass
                # Extract duration: "约\d+分钟"
                dur_match = re.search(r'约\s*(\d+)\s*分钟', line)
                if dur_match and 'duration' not in route_data:
                    try:
                        route_data['duration'] = int(dur_match.group(1)) * 60
                    except Exception:
                        pass

            route_data['major_roads'] = hw_codes

            if not hw_codes:
                return "", ""

            # Run unified assessment
            assessment = route_assessor.assess_route(route_data, vehicle or {})

            # ── Format bridge assessment section for LLM ──
            compat = assessment.get("route_compatibility", {})
            struct = compat.get("structural_safety", {})
            overall = assessment.get("overall_assessment", {})

            if struct.get("total_bridges", 0) > 0:
                bridge_lines = [
                    "【桥梁安全性评估结果】",
                    f"总体评估: {'[OK] 安全' if struct.get('high_risk_bridges', 0) == 0 else '[!!] 存在风险'}",
                    f"综合评分: {overall.get('score', 0)}/10",
                    f"风险等级: {overall.get('risk_level', '未知')}",
                    f"路线桥梁总数: {struct.get('total_bridges', 0)}座",
                    f"高风险桥梁: {struct.get('high_risk_bridges', 0)}座",
                    f"最小效应比值: {struct.get('min_effect_ratio', 0)}",
                    f"最大效应比值: {struct.get('max_moment_ratio', 0)}",
                    f"安全阈值: {struct.get('safety_threshold', 0.8)}",
                    f"安全评估: {struct.get('safety_assessment', '未知')}",
                    "",
                ]

                # Add recommendations
                recs = assessment.get("recommendations", {})
                for_user = recs.get("for_user", [])
                if for_user:
                    bridge_lines.append("通行建议:")
                    for r in for_user[:5]:
                        bridge_lines.append(f"  • {r}")
                    bridge_lines.append("")

                bridge_text = '\n'.join(bridge_lines)
            else:
                bridge_text = "【桥梁安全性评估结果】\n该路线暂无桥梁数据，无法进行桥梁评估。\n"

            # ── Format construction matching section for LLM ──
            traffic = assessment.get("traffic_analysis", {})
            impacts = traffic.get("construction_impacts", [])

            if impacts:
                const_lines = [
                    "【施工/事件匹配结果】",
                    f"路线涉及施工/事件路段: {len(impacts)}处",
                    f"预计总延误: {traffic.get('total_delay', 0)}分钟",
                    "",
                ]
                for imp in impacts[:10]:
                    const_lines.append(f"  • {imp.get('location', '')}")
                    const_lines.append(f"    影响等级: {imp.get('impact_level', '')}")
                    const_lines.append(f"    车道占用: {imp.get('lane_occupancy', '')}")
                    const_lines.append(f"    预计延误: {imp.get('delay_minutes', 0)}分钟")
                    const_lines.append("")

                const_lines.append(f"推荐通行时段: {traffic.get('recommended_time_window', '')}")
                construction_text = '\n'.join(const_lines)
            else:
                construction_text = ""

            return bridge_text, construction_text

        except Exception as e:
            logger.error(f"Route assessor error: {e}")
            # Fallback: try individual services
            try:
                from app.services.bridge_service import bridge_service
                route_info = {
                    'route_description': '',
                    'major_roads': list(set(re.findall(r'([GS]\d{1,4})', route_text))),
                    'tunnel_count': 0,
                }
                result = bridge_service.assess_route_safety(route_info, vehicle or {})
                if result.get('bridges_evaluated', 0) > 0:
                    bridge_text = f"【桥梁安全性评估结果】\n桥梁总数: {result.get('total_bridges_on_route', 0)}座, 风险等级: {result.get('risk_level', '未知')}\n"
            except Exception:
                pass
            return bridge_text, construction_text

    # ---- 路线规划 ----

    @staticmethod
    def _extract_od(msg: str) -> tuple:
        """从消息中提取起点和终点。"""
        # 1) "从X到Y" — 纯地名优先（2-4字中文+可选市县区）
        m = re.search(r'从([一-龥]{2,4}(?:市|县|区|综合实验区)?)[到去往]([一-龥]{2,4}(?:市|县|区|综合实验区)?)', msg)
        if m: return m.group(1), m.group(2)

        # 2) "从...到..." — 截断到标点/问词/动词
        m = re.search(r'从(.+?)[到去往](.+?)(?:怎么|如何|规划|路线|导航|运输|安全|施工|有|吗|走|哪|什么|[，。,\.!\?！？\s]|$)', msg)
        if m:
            o = re.sub(r'(运货|送货|出发|运输|开车|通行|货运)\s*$', '', m.group(1).strip()).strip('，。,!！?？ ')
            d = re.sub(r'(运货|送货|运输|货运|收货|怎么|如何|走哪)\s*$', '', m.group(2).strip()).strip('，。,!！?？ ')
            if o and d and len(o) < 20 and len(d) < 20: return o, d

        # 3) "X到Y" 无"从"
        m = re.search(r'([一-龥]{2,4}(?:市|县|区)?)[到去往]([一-龥]{2,4}(?:市|县|区)?)', msg)
        if m: return m.group(1), m.group(2)

        return None, None

    async def _plan_route(self, origin: str, dest: str) -> Optional[str]:
        """直接调用 AmapService，不走 HTTP 自调用。"""
        try:
            from app.services.amap_service import AmapService, CITY_COORDS
            import asyncio as aio

            # 尝试地理编码，失败则用坐标表兜底
            coords_o = await AmapService.get_geo_code(origin)
            coords_d = await AmapService.get_geo_code(dest)
            if not coords_o or not coords_d:
                return None

            o_str = f"{coords_o[0]},{coords_o[1]}"
            d_str = f"{coords_d[0]},{coords_d[1]}"

            # 多策略并发
            tasks = [AmapService.plan_route_driving(o_str, d_str, s) for s in [0, 9]]
            results = await aio.gather(*tasks, return_exceptions=True)

            from app.api.routes import process_route_data  # reuse existing logic
            all_routes = []
            for i, res in enumerate(results):
                if isinstance(res, Exception) or not isinstance(res, dict):
                    continue
                if res.get("status") == "1":
                    label = "速度优先" if i == 0 else "躲避拥堵"
                    try:
                        processed = process_route_data(res, label, None, origin, dest)
                        all_routes.extend(processed)
                    except Exception:
                        continue

            if not all_routes:
                return None
            routes = sorted(all_routes, key=lambda r: r.distance)[:2]
            if not routes:
                return None
            lines = []
            for i, rt in enumerate(routes[:2]):
                dist = rt.distance / 1000
                dur = rt.duration // 60
                lines.append(
                    f"**方案{i+1}**: {dist:.1f}km, 约{dur}分钟, "
                    f"过路费¥{rt.toll_cost:.0f}, "
                    f"路况:{rt.traffic_condition or '未知'}"
                )
                if rt.route_description:
                    lines.append(f"  路径: {rt.route_description}")
                if rt.risk_warnings:
                    lines.append(f"  [!] 风险: {', '.join(rt.risk_warnings)}")
                if rt.tunnel_count:
                    lines.append(f"  隧道: {rt.tunnel_count}个, 总长{rt.tunnel_distance/1000:.1f}km")
                if rt.major_roads:
                    lines.append(f"  主要道路: {' → '.join(rt.major_roads)}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Route error: {e}")
            return None

    # ---- 法规知识库查询 ----

    @staticmethod
    def _is_regulation_query(message: str) -> bool:
        """Detect whether the user message is asking about regulations."""
        return any(kw in message for kw in REGULATION_KEYWORDS)

    @staticmethod
    def _query_regulation_kb(message: str) -> str:
        """Query the regulation knowledge base and return formatted results."""
        try:
            from app.services.regulation_kb import regulation_kb

            # Extract potential vehicle parameters from the message
            vehicle_info = AgentService._extract_vehicle_info(message)

            # If vehicle parameters were found, do a comprehensive lookup
            if vehicle_info and any(v > 0 for v in vehicle_info.values()):
                kb_text = regulation_kb.format_for_llm(vehicle_info)
            else:
                # Fall back to keyword search
                results = regulation_kb.query(message)
                if not results:
                    return ""
                lines = ["【法规知识库查询结果】", ""]
                for art in results[:5]:
                    lines.append(f"## {art.get('title', '')}（第{art.get('article_number', '')}条）")
                    # Truncate long content for the LLM context
                    content = art.get("content", "")
                    if len(content) > 300:
                        content = content[:300] + "..."
                    lines.append(content)
                    lines.append("")
                kb_text = "\n".join(lines)

            if kb_text:
                logger.info(f"Regulation KB lookup returned {len(kb_text)} chars")
            return kb_text
        except Exception as e:
            logger.error(f"Regulation KB lookup error: {e}")
            return ""

    @staticmethod
    def _extract_vehicle_info(message: str) -> dict:
        """Extract vehicle dimension/weight parameters from natural language message.

        Looks for patterns like:
            - 高4.7米 / 高度4.7m / 4.7米高
            - 宽3.0米 / 宽度3米
            - 长28米 / 长度28m
            - 重60吨 / 总重80吨 / 重量50t
            - 6轴 / 六轴 / 轴数5
        """
        info: dict = {}

        # Height patterns
        h_match = re.search(r'(?:高度|高)[约达为]?\s*([\d.]+)\s*(?:米|m)', message)
        if not h_match:
            h_match = re.search(r'([\d.]+)\s*(?:米|m)\s*(?:高|高度)', message)
        if h_match:
            info["height"] = float(h_match.group(1))

        # Width patterns
        w_match = re.search(r'(?:宽度|宽)[约达为]?\s*([\d.]+)\s*(?:米|m)', message)
        if not w_match:
            w_match = re.search(r'([\d.]+)\s*(?:米|m)\s*(?:宽|宽度)', message)
        if w_match:
            info["width"] = float(w_match.group(1))

        # Length patterns
        l_match = re.search(r'(?:长度|长)[约达为]?\s*([\d.]+)\s*(?:米|m)', message)
        if not l_match:
            l_match = re.search(r'([\d.]+)\s*(?:米|m)\s*(?:长|长度)', message)
        if l_match:
            info["length"] = float(l_match.group(1))

        # Weight patterns
        wt_match = re.search(r'(?:总重|总质量|重量|重)[约达为]?\s*([\d.]+)\s*(?:吨|t)', message)
        if not wt_match:
            wt_match = re.search(r'([\d.]+)\s*(?:吨|t)\s*(?:重|总重|重量)', message)
        if wt_match:
            info["total_weight"] = float(wt_match.group(1))

        # Axle count patterns
        ax_match = re.search(r'([\d六七八九十]+)\s*(?:轴|桥)', message)
        if ax_match:
            axle_str = ax_match.group(1)
            # Convert Chinese numeral if needed
            cn_num = {"六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            try:
                info["axle_count"] = int(axle_str)
            except ValueError:
                info["axle_count"] = cn_num.get(axle_str)

        return info

    # ---- LLM 流式回答 ----

    async def _llm_stream(self, user_msg: str, kb_text: str, route_text: str, bridge_text: str = "", construction_text: str = "", regulation_text: str = ""):
        """用 DeepSeek 流式生成回答。"""
        system = """你是一个专业的大件运输智能助手，名字叫"货导"。
你的职责是基于提供的【法规知识库查询】、【施工/事件精确匹配】、【桥梁安全性评估结果】、【路线规划数据】和【知识库检索结果】，回答用户的问题。

规则：
1. 法规知识库有确切数据的，直接引用法规原文和条目编号
2. 施工事件精确匹配中有明确的K值桩号重叠信息，请直接引用具体的施工路段和受影响程度
3. 桥梁评估数据中有明确的效应比值和安全性判断，请直接引用
4. 将施工数据与路线结合分析：如果路线经过施工路段且K值重叠，明确指出具体影响
5. 知识库没有的信息，诚实告知并建议查询渠道（12122、导航App等）
6. 用中文回答，简洁专业，结构清晰，先列事实再给建议
7. 当用户询问法规、许可、处罚、护送等问题时，优先引用法规知识库的原始条目"""

        regulation_section = f"\n\n{regulation_text}" if regulation_text else ""
        construction_section = f"\n\n{construction_text}" if construction_text else ""
        kb_section = f"【知识库检索结果（福建高速施工/事件数据）】\n{kb_text}" if kb_text else ""
        route_section = f"【路线规划结果】\n{route_text}" if route_text else ""
        bridge_section = f"\n\n{bridge_text}" if bridge_text else ""

        prompt = f"{regulation_section}{construction_section}\n\n{kb_section}\n\n{route_section}{bridge_section}\n\n【用户问题】\n{user_msg}\n\n请基于以上信息回答。法规知识库有数据就引用原文和条目编号，施工事件和桥梁评估有明确数据请引用，知识库有数据就引用原文，路线和施工有冲突请明确指出。"

        try:
            # Wrap the initial connection with a 60-second overall timeout
            # The executor thread still uses a 90s requests-level timeout for the stream itself
            r = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    _executor,
                    lambda: requests.post(
                        f"{self.llm_base}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.llm_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.llm_model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.3,
                            "max_tokens": 1500,
                            "stream": True,
                        },
                        timeout=90,
                        stream=True,
                    ),
                ),
                timeout=60,  # Overall deadline for the initial connection + headers
            )
            if r.status_code != 200:
                body = r.text[:300]
                logger.error(f"LLM stream HTTP {r.status_code}: {body}")
                # Fallback: non-streaming
                yield await self._llm_fallback(system, prompt)
                return

            for line in r.iter_lines(decode_unicode=True):
                if not line: continue
                if line.startswith("data: "): data_str = line[6:]
                elif line.startswith("data:"): data_str = line[5:]
                else: continue
                if data_str.strip() in ("[DONE]", ""): continue
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content: yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except asyncio.TimeoutError:
            logger.warning("LLM stream connection timed out after 60s, falling back")
            try:
                result = await self._llm_fallback(system, prompt)
                yield result
            except Exception as e2:
                yield f"[服务超时: {e2}]"
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            # Fallback: non-streaming
            try:
                result = await self._llm_fallback(system, prompt)
                yield result
            except Exception as e2:
                yield f"[服务异常: {e}]"

    async def _llm_fallback(self, system: str, prompt: str) -> str:
        """Non-streaming fallback when streaming fails."""
        try:
            r = await asyncio.get_event_loop().run_in_executor(
                _executor,
                lambda: requests.post(
                    f"{self.llm_base}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.llm_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500,
                        "stream": False,
                    },
                    timeout=60,
                ),
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            return f"[LLM错误: {r.status_code}]"
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"LLM fallback connection error: {e}")
            return "[服务连接失败，请检查网络或稍后重试]"
        except requests.exceptions.Timeout:
            logger.warning("LLM fallback timed out")
            return "[服务响应超时，请稍后重试]"
        except Exception as e:
            logger.error(f"LLM fallback error: {e}")
            return f"[服务不可用: {e}]"

    # ---- SSE ----

    @staticmethod
    def _sse(event: str, data) -> str:
        payload = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        return f"event: {event}\ndata: {payload}\n\n"

    # ---- 主入口 ----

    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        # Check if frontend already provided route context
        route_text = ""
        has_ctx = "[路线上下文]" in message
        user_only = message
        vehicle_info = {}  # Chat context may not include vehicle details

        # Extract route context if provided by frontend
        bridge_text = ""
        if has_ctx:
            parts = message.split("[用户问题]")
            if len(parts) >= 2:
                route_text = parts[0].replace("[路线上下文]", "").strip()
                user_only = parts[1].strip()
            else:
                user_only = message.replace("[路线上下文]", "").strip()

        # Phase 0: 法规知识库查询（检测是否法规相关问题）
        regulation_text = ""
        if self._is_regulation_query(user_only):
            yield self._sse("status", "正在查询法规知识库...")
            regulation_text = self._query_regulation_kb(user_only)
            if regulation_text:
                yield self._sse("regulation", regulation_text)
                yield self._sse("status", f"法规知识库查询完成 ({len(regulation_text)} 字符)")

        # Phase 1: 关键词检索
        yield self._sse("status", "正在搜索知识库...")
        kb_text = self._search_files(user_only)
        if kb_text:
            yield self._sse("status", f"找到相关文档 ({len(kb_text)} 字符)")

        # Phase 2: 路线规划 (only if no context provided)
        if not has_ctx:
            origin, dest = self._extract_od(user_only)
            if origin and dest:
                yield self._sse("status", f"正在规划 {origin} → {dest} 路线...")
                try:
                    route_text = await self._plan_route(origin, dest) or ""
                except Exception as e:
                    logger.error(f"Route plan error: {e}")
                    yield self._sse("status", "路线规划暂时不可用")
                    route_text = ""
                if route_text:
                    yield self._sse("route", route_text)

        # Phase 2.5: 综合路线评估（桥梁安全 + 施工匹配 + 尺寸合规）
        if route_text:
            yield self._sse("status", "正在评估路线安全性与施工影响...")
            try:
                bridge_text, construction_text = self._assess_route_comprehensive(route_text, vehicle_info)
            except Exception as e:
                logger.error(f"Route assessment error: {e}", exc_info=True)
                yield self._sse("status", "桥梁评估暂时不可用")
                bridge_text, construction_text = "", ""
            if bridge_text:
                yield self._sse("bridge", bridge_text)
            if construction_text:
                yield self._sse("construction", construction_text)

        # Phase 3: LLM 合成
        yield self._sse("status", "正在生成回答...")
        async for token in self._llm_stream(user_only, kb_text, route_text, bridge_text, construction_text, regulation_text):
            yield self._sse("token", token)

        yield self._sse("done", "")


agent_service = AgentService()
