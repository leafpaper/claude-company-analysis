"""东山精密 002384 golden fixture — v8 装配层的行为基线(手写, 数据取自铁律推演验收稿)。

来源:
  .scratch/v8-refactor/research/02-dongshan-walkthrough.md  §1-§6(五节点判定 + 决断卡五行)
  .scratch/v8-refactor/research/05-dongshan-panel.md        §1-§2(赚钱面板 + 写手提名通道)
  .scratch/v8-refactor/research/03-dongshan-incremental.md  §1-§2(中报双向场景)

写手提名两条(research/05 §2 的机制在东山的两处真实落点):
  · 商誉对赌未披露 —— financial_audit 只测商誉/净资产比例, 测不到对赌条款;
  · 散户暴增+两融杠杆拥挤 —— audit 只有户数信号(🟡), 两融/大宗折价在 capital_flow 无红旗规则,
    而 research/02 §4 左尾④ 把它算进「踩踏放大回撤至 −75%~−98%」, 故按 🟠 提名。
"""
from __future__ import annotations

import copy

from scripts import red_flags as rf

# research/02 §6 决断卡五行(golden: 装配必须逐行一致)
RESEARCH_CARD = [
    "部分好——真卡位+平庸财务",
    "↑变好但未确认,注意力先行",
    "买完完美未来;锚区间 57-89 元 vs 现价 273 元",
    "高尾险·扛不住,高信仰 5/5",
    "先观察等证据临界,期权小仓 ≤2-3%",
]

# 面板里被红标命中的那条脚本红旗(现金含量与 FCF 共用, research/05 §1「随现金流红旗」)
CASH_FLAG_ID = rf.flag_id("Buffett Quality", "利润质量偏弱（OCF/NI）")
GOODWILL_FLAG_ID = rf.flag_id("Buffett Quality", "商誉占净资产过高")
PB_FLAG_ID = rf.flag_id("Valuation", "PB 历史分位")
NOMINATION_GOODWILL = "goodwill-vam-undisclosed"
NOMINATION_CROWDING = "retail-crowding-leverage"


def audit_result() -> dict:
    """financial_audit --json 的产物形态(framework/signal/severity/evidence/...)。"""
    flags = [
        ("Buffett Quality", "利润质量偏弱（OCF/NI）", "🟠 高",
         "2026Q1 营收 +52.7% 而经营现金流 −17.5%;FCF −24.01 亿",
         "净利润含水分,扩张靠融资"),
        ("Buffett Quality", "商誉占净资产过高", "🟠 高",
         "商誉=47.69 亿(单季 +26.5 亿并购形成),刨掉商誉清算净值约 −2~8 亿",
         "并购驱动增长,存在商誉减值悬崖风险"),
        ("Buffett Quality", "存货增速远高于营收", "🟡 中",
         "存货增速 +45.1% vs 营收增速 +9.1%(差 36pp)", "存货积压,未来可能计提跌价准备"),
        ("Shareholder Flow", "股东户数变化", "🟡 中",
         "8.17 万户 → 30.60 万户(+274%)", "散户涌入,高位接盘风险"),
        ("Shareholder Flow", "长期户数上升（筹码分散）", "🟡 中",
         "一年内户数上升 > 20%", "筹码分散,通常伴随股价拉升后的散户涌入"),
        ("Valuation", "PB 历史分位", "🟠 高",
         "PB 22.09,处于近 1 年 100% 分位", "估值偏高"),
        ("Valuation", "PB vs ROE 严重错配", "🟠 高",
         "PB 22.09 vs ROE 1.58%,错配 25.7 倍", "为低回报资产付高溢价"),
        ("Valuation", "PS 历史分位过高", "🟡 中", "PS 处于近 1 年 100% 分位", "营收端定价已透支"),
        ("Valuation", "股息率极低", "🟡 中", "股息率 0.02%", "无现金回报保护"),
        ("DuPont", "最新ROE 分解", "ℹ️ 信息",
         "净利率=3.73% × 资产周转 × 权益乘数=2.81", "ROE 改善来自杠杆而非经营效率"),
        ("Altman Z-Score", "Z=8.767", "🟢 低", "Z=8.767 落在安全区", "短期破产风险低"),
        ("Beneish M-Score", "M=-2.519", "🟢 低", "M=−2.519 < −1.78", "无盈余操纵迹象"),
    ]
    return {
        "bundle_dir": "output/东山精密/raw_data",
        "framework_status": {},
        "red_flags": [
            {
                "framework": fw, "signal": sig, "severity": sev,
                "value": None, "threshold": "—", "evidence": ev, "implication": impl,
            }
            for fw, sig, sev, ev, impl in flags
        ],
    }


def script_flags() -> list[dict]:
    return rf.normalize_audit(audit_result())


# ---------------------------------------------------------------- 五个节点 YAML 块

def quality_block() -> dict:
    sub = [
        ("生意模式赚钱吗", "✗", "集团毛利率 FY2025 14.09%、净利率 3.47%;PCB 红海长期把毛利压在 13~18%",
         "维度2 定价权证据"),
        ("赚钱质量真吗", "✗", "ROE 1.58%/净利率 3.73% peer 分位双 0% 垫底;2026Q1 营收 +52.7% 而 OCF −17.5%",
         "peer 分位 + audit DuPont"),
        ("护城河存在吗", "⚠️", "200G EML 光芯片 IDM「窄而深」是唯一硬壁垒,但光模块仅占营收 3.58%、未被订单坐实",
         "护城河框架"),
        ("管理层可信吗", "⚠️", "4 期业绩预告全部落入区间或略超上沿;袁永刚质押占其持股 34.6%",
         "管理层框架"),
        ("财务底子稳吗", "⚠️", "资产负债率 63.69% 为 18 期最高;Altman Z=8.767、Beneish M=−2.519",
         "audit 三评分"),
    ]
    return {
        "node": "quality",
        "verdict": "部分好——真卡位+平庸财务",
        "sub_verdicts": [
            {"question": q, "judgment": j, "hardest_evidence": [{"text": t, "mechanism": m}]}
            for q, j, t, m in sub
        ],
        "red_flag_nominations": [],
        "panel": {
            "industry_reason": "制造业并购扩张期,矛盾焦点在现金与回报质量 → 选默认五件套",
            "indicators": [
                {"name": "毛利率 / 净利率", "value": "14.09% / 3.47%",
                 "trend": "PCB 红海常年 13~18%,定价权弱", "peer_percentile": None,
                 "red_flag_ref": None, "note": None},
                {"name": "扣非占比", "value": "扣非 +166.99%,非经常仅 5,061 万",
                 "trend": "利润是经营性实锤", "peer_percentile": None,
                 "red_flag_ref": None, "note": None},
                {"name": "现金含量(OCF÷净利)", "value": "负",
                 "trend": "营收 +52.7% 而 OCF −17.5%,背离", "peer_percentile": None,
                 "red_flag_ref": CASH_FLAG_ID, "note": None},
                {"name": "FCF", "value": "−24.01 亿", "trend": "扩张全靠融资",
                 "peer_percentile": None, "red_flag_ref": CASH_FLAG_ID, "note": "随现金流红旗"},
                {"name": "ROE + peer 分位", "value": "1.58%",
                 "trend": "杜邦:改善靠杠杆 2.44→2.81 非经营效率", "peer_percentile": "0% 分位",
                 "red_flag_ref": None, "note": "难看但无 audit 规则命中 → 不标色"},
            ],
        },
    }


def state_block() -> dict:
    return {
        "node": "state",
        "verdict": "↑变好但未确认,注意力先行",
        "sub_verdicts": [
            {"question": "λ 载体在放量吗", "judgment": "实锤但被稀释",
             "hardest_evidence": [{"text": "索尔思毛利率 36.74% 全集团最高;高 λ 分部仅占 FY2025 营收 3.58%",
                                   "mechanism": "4.11 λ 载体"}]},
            {"question": "实锤还是传闻", "judgment": "利润实锤、大客户订单传闻",
             "hardest_evidence": [{"text": "2026Q1 归母 +143.47%(扣非 +166.99%)为实锤;NVIDIA/Meta 订单排至 2028 全是券商转述",
                                   "mechanism": "实锤/传闻分级 + 叙事四关③"}]},
            {"question": "身份切换坐实了吗", "judgment": "改名先行、里子未换",
             "hardest_evidence": [{"text": "市场按「算力追光者」定价(一年约 5 倍),业务本体仍 96% PCB/触控",
                                   "mechanism": "身份切换 P1→P4"}]},
        ],
        "red_flag_nominations": [],
        "critical_point": {"items": [
            "2026 中报(约 8 月,光模块首个完整 H1 分部数据)",
            "谷歌 200G EML 验证结果(2026Q2 末)",
        ]},
    }


def odds_block() -> dict:
    return {
        "node": "odds",
        "verdict": "买完完美未来",
        "sub_verdicts": [
            {"question": "价格分解 P=F+N", "judgment": "N 占约 80%,obligation 非 option",
             "hardest_evidence": [{"text": "F≈1,000 亿(成熟主业年化归母约 50 亿 × 20x),N≈4,000 亿 / 市值约 5,000 亿",
                                   "mechanism": "P=F+N"}]},
            {"question": "现价隐含什么", "judgment": "过度乐观",
             "hardest_evidence": [{"text": "隐含净利 +50%/年×5 年 + 光模块占比 3.58%→30%+ + 退出仍 30x",
                                   "mechanism": "反向 DCF"}]},
        ],
        "red_flag_nominations": [],
        "current_price": {"value": 273, "unit": "元"},
        "anchor_range": {
            "low": {"method": "SOTP", "value": 57, "unit": "元"},
            "high": {"method": "DCF(概率加权)", "value": 89, "unit": "元"},
            "same_direction": True,
            "divergence_note": "SOTP 只认已并表利润、DCF 允许 15% CAGR 温和放量,55% 分歧是信息;现价为高端 3.06 倍、低端 4.79 倍,两端同向",
        },
    }


def path_block() -> dict:
    return {
        "node": "path",
        "verdict": "高尾险·扛不住,高信仰 5/5",
        "sub_verdicts": [
            {"question": "左尾有多深", "judgment": "近资不抵债地板",
             "hardest_evidence": [{"text": "商誉 47.69 亿减值后清算净值约 −2~8 亿,最差 5 元(−98%)",
                                   "mechanism": "6.4 左尾防护"}]},
            {"question": "高信仰体检", "judgment": "5/5 满分(下跌时是波动放大器)",
             "hardest_evidence": [{"text": "PE 242.9x 全行业最贵 / 一年 +758% / 散户 30.60 万户 / 两融活跃 / 袁氏父子控盘 30.05%",
                                   "mechanism": "高信仰股体检"}]},
        ],
        "red_flag_nominations": [
            {"id": NOMINATION_GOODWILL, "level": "🟠", "title": "商誉对赌条款未披露",
             "evidence": "单季 +26.5 亿并购形成商誉 47.69 亿,并购公告未披露对赌条款(读 PDF 所得,脚本无此规则)",
             "source": "nomination", "node": "path", "metric_refs": ["goodwill"]},
            {"id": NOMINATION_CROWDING, "level": "🟠", "title": "散户 2.8 倍暴增+两融杠杆拥挤",
             "evidence": "散户 8.17 万→30.60 万户(约 2 个月 2.8 倍)+ 两融高于 60 日中位 33.4% + 大宗折价 −7.5% → 踩踏放大回撤至 −75%~−98%",
             "source": "nomination", "node": "path", "metric_refs": ["holder_count", "margin_balance"]},
        ],
        "falsifications": [
            {"condition": "H1 光模块营收 <40 亿或毛利率 <30%", "triggered": False},
            {"condition": "谷歌 200G EML 验证未过 / 订单证伪", "triggered": False},
            {"condition": "商誉任一减值", "triggered": False},
            {"condition": "营收增速连续 <25% 或现金流持续恶化", "triggered": False},
        ],
        "left_tail": [
            {"scenario": "商誉 47.69 亿减值 → 最差 5 元(−98%)", "note": "刨掉商誉净值约 −2~8 亿"},
            {"scenario": "叙事证伪 → 80% 想象溢价回吐(−86%~−98%)"},
            {"scenario": "关键人物:袁氏父子控盘 30.05% 高质押 + 索尔思技术团队绑定"},
            {"scenario": "散户 2.8 倍暴增 + 两融拥挤 → 踩踏放大回撤至 −75%~−98%"},
            {"scenario": "质押补仓压力与踩踏共振"},
        ],
    }


def decision_block() -> dict:
    return {
        "node": "decision",
        "verdict": "先观察等证据临界,期权小仓 ≤2-3%",
        "triad": {"state": "↑未确认", "odds": "买完完美未来", "path": "高尾险"},
        "action_gear": "等证据临界",
        "action_detail": "主基调先别动、现价 0 仓位持币(等待=选择权);想赌右尾最多总资金 2-3% 期权小仓、设硬止损",
        "position": "现价 0 仓位;期权小仓 ≤2-3% 总资金",
        "three_part": {
            "good_company": "部分是(引用①质地:部分好——真卡位+平庸财务)",
            "good_bet": "否(三乘子两差一弱)",
            "good_price": "否(现价为锚区间高端的 3 倍以上)",
        },
        "good_company_ref": "①质地 verdict:部分好——真卡位+平庸财务",
        "what_to_wait": [
            "2026 中报(约 8 月,引用②状态临界点)",
            "谷歌 200G EML 验证(2026Q2 末)",
            "价格条件:回调至乐观情景区约 160 元以内",
        ],
        "falsification_exit": [
            "H1 光模块营收 <40 亿或毛利率 <30%",
            "谷歌验证未过 / 订单证伪",
            "商誉任一减值",
        ],
        "gear_cap": {"triggered": False, "reason": None},
        "front_page_intro": (
            "老本行是赚辛苦钱的 PCB 红海龙头,新并的 200G EML 光芯片是真卡位——但它只占营收 3.58%,"
            "而市值已按「算力追光者」定价。现价 273 元是锚区间 57-89 元的 3 倍以上,买的是必须交付的完美未来。"
            "商誉 47.69 亿是薄地板,散户两个月增 2.8 倍、两融拥挤,跌起来是波动放大器。"
            "所以现在不是买点:等 2026 中报的光模块完整分部数据与谷歌验证结果,想赌右尾只用 ≤2-3% 期权小仓并设硬止损。"
        ),
    }


def nodes() -> dict[str, dict]:
    return {
        "quality": quality_block(),
        "state": state_block(),
        "odds": odds_block(),
        "path": path_block(),
        "decision": decision_block(),
    }


NODE_BODIES = {
    "quality": "## ① 质地——是不是好公司\n\n**判定**:部分好——真卡位+平庸财务。\n\n完整财务表见附录A。\n",
    "state": "## ② 状态——在变好吗\n\n**判定**:↑变好但未确认,注意力先行。\n\n该等什么见临界点。\n",
    "odds": "## ③ 赔率——贵不贵\n\n**判定**:买完完美未来。锚区间 57-89 元 vs 现价 273 元。\n",
    "path": "## ④ 路径——扛得住吗\n\n**判定**:高尾险·扛不住,高信仰 5/5。\n",
    "decision": "## ⑤ 怎么办——行动档位与证伪\n\n**判定**:先观察等证据临界,期权小仓 ≤2-3%。\n",
}


# ---------------------------------------------------------------- 增量复查双向场景(research/03)

def scenario_a_nodes() -> dict[str, dict]:
    """场景 A 中报兑现不足(利空):质地复用、状态翻转、档位 观察→回避。"""
    n = copy.deepcopy(nodes())
    n["quality"]["reused_from"] = "2026-06-22"          # 分诊未标脏 → 复用盖戳
    n["state"]["verdict"] = "λ 走弱——放量未兑现,叙事降温"
    n["state"]["sub_verdicts"][0]["judgment"] = "未兑现"
    n["path"]["falsifications"][0]["triggered"] = True   # H1 光模块 28 亿 < 40 亿
    n["odds"]["current_price"] = {"value": 210, "unit": "元"}
    n["decision"].update({
        "verdict": "回避:证伪已触发,期权仓退出",
        "action_gear": "回避",
        "triad": {"state": "λ走弱", "odds": "买完完美未来", "path": "高尾险"},
    })
    return n


def scenario_b_nodes() -> dict[str, dict]:
    """场景 B 超预期兑现(利好):分部占比跨档 → 质地标脏重评并翻转,档位 观察→期权仓。"""
    n = copy.deepcopy(nodes())
    n["quality"]["verdict"] = "偏好——卡位坐实+财务仍平庸"
    n["quality"]["sub_verdicts"][2]["judgment"] = "✓"    # 护城河:谷歌背书 + 完整 H1 分部数据
    n["state"]["verdict"] = "↑确认——传闻升实锤"
    n["odds"]["current_price"] = {"value": 310, "unit": "元"}
    n["decision"].update({
        "verdict": "小仓试错:右尾坐实但仍贵",
        "action_gear": "期权仓",
        "triad": {"state": "↑确认", "odds": "仍贵", "path": "高尾险"},
    })
    return n
