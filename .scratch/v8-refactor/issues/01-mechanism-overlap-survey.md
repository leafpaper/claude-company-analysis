# 01 机制重叠盘点

Type: research
Status: resolved

## Question

v7.0 的各判断机制——10 维评分(§四)、4.11 状态评估、§五 赔率层(P=F+N / 反向DCF / 叙事SOTP / 回报路径)、§七 决策内核(三元组/三分/行动档位)、6.4 左尾防护、§六 红旗审计——在框架文档与实际已发布报告中,各自产出什么判断?哪些互相重叠、冗余甚至矛盾?

产出要求:机制 × 产出的重叠矩阵 + 每处重叠的具体证据(报告原文引用),落盘为 `.scratch/v8-refactor/research/01-mechanism-overlap.md`。这是[判断链收敛方案](02-judgment-chain-convergence.md)的证据地基。

信息源:
- 本仓库 `references/`(四份框架文档)、`assets/templates/report-skeleton.md`、`agents/phase3-part*.md`、`agents/reviewer-*.md`
- 已发布真实报告:优先本地 Inves-Report 克隆(旧机器在 `C:\Users\Administrator\Inves-Report`,本机为 tinyb 用户、系统重装过,需自行探测 `$env:INVES_REPORT_DIR` 或常见路径);找不到则从 https://github.com/leafpaper/Inves-Report 的 `reports/`(如 `002384_东山精密`)抓最近 1-2 份 `*-analysis-*.md`

## Answer

- 「值不值得买」被 ≥6 套机制各答一遍(评分信号→定性方向→赔率判定→行动档位→决断卡→§一结论);东山精密报告里「贵不贵」答了约 9 次、「该等什么(中报)」写了约 7 处。
- 真正产判断的只有三处:4.11 状态、§五 5.1-5.7 赔率、6.4 路径;§七 7.1-7.3 是制度化复述层,§一 是 §七 的四份抄本(决断卡/一句话/RATING_TRIO/one_liner),3 个 reviewer 里 2 个专职校验抄写一致。
- 综合评分与定性综合方向已"名存实亡"——两份报告合计 5 处免责声明"这不是投资结论",但仍占 §一 头条与主页卡片 verdict 字段(结论双轨)。
- 框架文档矛盾:scoring-rubric 与骨架是两套不同的 10 维度+权重;rubric「定性叠加/调整后综合分」指向已被 qualitative v3 删除的打分制;rubric 投资信号表(4.9=建议放弃)与 §七 行动档位(等证据临界)平行未收敛;估值锚 vs SOTP 分歧 55%~3 倍、超 v4.2 自定的 20% 红线却以"方向一致"带过。
- 6.1 致命快筛在两案均空转(全 PASS+免责"快筛 PASS≠安全");5.6 建议仓位与 7.4 行动档位曾给不同档("回避" vs "等证据临界+期权仓")。
- 两案判断链内部零实质矛盾——代价不是结论打架,是篇幅+抄写校验成本+三个"结论假面"干扰读者。详见 [../research/01-mechanism-overlap.md](../research/01-mechanism-overlap.md)。
