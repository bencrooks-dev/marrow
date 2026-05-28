# marrow — Market Research

> Compiled May 2026. Every figure below carries a named source, year, and URL. Where sources
> disagree, the range is shown and noted. Items with no credible figure are explicitly marked
> "no credible figure found." **Do not edit a number without re-checking its source.**
>
> Read the **Caveats & confidence** section at the end before putting any of these on a slide —
> some sources are marketing-grade (press-release report sellers) and some are analyst-grade
> (Gartner, Goldman Sachs, Morgan Stanley, Stack Overflow, LangChain first-party surveys).

---

## 1. AI Agents / Agentic AI market size and CAGR (global)

Two related-but-distinct markets are reported under similar names ("AI agents" vs. "agentic AI"),
so figures are not directly comparable. Both show CAGRs in the mid-40s to ~50%.

- **AI Agents market** — USD 7.63B in 2025 → USD 182.97B by 2033, CAGR 49.6% (2026–2033) — Source: Grand View Research, 2025, https://www.grandviewresearch.com/industry-analysis/ai-agents-market-report
- **AI Agents market (alt horizon)** — USD 50.31B by 2030, CAGR 45.8% (2025–2030) — Source: Grand View Research (PR Newswire release), 2025, https://www.prnewswire.com/news-releases/ai-agents-market-size-to-hit-50-31-billion-by-2030-at-cagr-45-8---grand-view-research-inc-302447060.html
- **AI Agents market** — USD 7.84B in 2025 → USD 52.62B by 2030, CAGR 46.3% — Source: MarketsandMarkets, 2025, https://www.marketsandmarkets.com/PressReleases/ai-agents.asp
- **Agentic AI market** — USD 7.06B in 2025 → USD 93.20B by 2032, CAGR 44.6% — Source: MarketsandMarkets, 2025, https://www.marketsandmarkets.com/PressReleases/agentic-ai.asp

**Range note:** 2025 base is tightly clustered (~USD 7.0–7.8B across all four). CAGR clusters
44–50%. The 2030/2032/2033 endpoints diverge widely (USD 50B → 183B) purely because of the
horizon year and the exponential CAGR — do not compare endpoints across different terminal years.

**Analyst-grade demand-side anchors (better for an investor slide than the report-seller TAM numbers):**
- **33% of enterprise software applications will include agentic AI by 2028**, up from <1% in 2024 — Source: Gartner, 2025, https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025
- **40% of enterprise applications integrated with task-specific AI agents by end of 2026**, up from <5% in 2025 — Source: Gartner, 2025, https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025
- **Cautionary counterpoint:** >40% of agentic AI projects will be canceled by end of 2027 (escalating cost, unclear value, inadequate risk controls) — Source: Gartner, 2025, https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027

---

## 2. Edge AI market size and CAGR

This is the noisiest topic — definitions (hardware-only vs. software vs. full ecosystem) drive a
3x spread in both size and CAGR. Show a range, not a point estimate.

- **Edge AI market** — USD 25.65B in 2025 → USD 118.69B by 2033, CAGR 21.7% (2026–2033) — Source: Grand View Research, 2025, https://www.grandviewresearch.com/industry-analysis/edge-ai-market-report
- **Edge AI market** — → USD 165.05B by 2035, CAGR 20.46% — Source: Precedence Research, 2025, https://www.precedenceresearch.com/edge-ai-market
- **Edge AI market** — → USD 56.8B by 2030, CAGR 36.9% (2025–2030) — Source: GlobeNewswire / report release, Oct 2025, https://www.globenewswire.com/news-release/2025/10/02/3160652/0/en/Edge-AI-Market-to-Grow-at-36-9-CAGR-Through-2030.html
- **Edge AI Hardware (subset)** — ~USD 26.14B in 2025 — Source: MarketsandMarkets, 2025, https://www.marketsandmarkets.com/Market-Reports/edge-ai-hardware-market-158498281.html
- **Edge AI (lower-bound definition)** — USD 11.8B (base year) — Source: BCC Research, 2025, https://www.bccresearch.com/market-research/information-technology/edge-ai-market.html

**Range note:** 2025 base spans ~USD 12B–26B; CAGR spans ~18%–37%. The ~20% CAGR figures
(Grand View, Precedence) are the most consistent and defensible; the 36.9% figure is an outlier.

---

## 3. Humanoid robotics market / broader embodied AI

These are the strongest analyst-grade figures in this whole document (bank research desks, not
report sellers). Best material for an embodied-AI slide.

- **Humanoid robot total addressable market ~USD 38B by 2035** (revised up 6x from an earlier
  USD 6B estimate); modeled ~502,000 global shipments by end of 2032 — Source: Goldman Sachs, 2024 (report; reiterated 2025), https://www.goldmansachs.com/insights/articles/the-global-market-for-robots-could-reach-38-billion-by-2035
- **Humanoid robot market ~USD 5 trillion by 2050**; ~13 million units in service by 2035 (mostly factories/warehouses) — Source: Morgan Stanley, 2025, https://www.morganstanley.com/insights/articles/humanoid-robot-market-5-trillion-by-2050
- **Humanoid shipments: ~18,000 units in 2025 → ~10 million units/yr by end of 2035, ~88% CAGR** — Source: BofA Global Research, 2025 (as reported), https://www.morganstanley.com/insights/articles/humanoid-robot-market-5-trillion-by-2050 (BofA figure cited via secondary coverage; see caveats)

**Broader "embodied AI" as a single named market** — no credible standalone figure found. "Embodied
AI" is used qualitatively in the literature; the quantified proxies are the humanoid-robot forecasts
above plus the edge AI / TinyML markets (sections 2 and 4). Flag this explicitly if asked for an
"embodied AI TAM."

---

## 4. On-device / embedded AI inference (TinyML, edge inference)

- **TinyML market** — USD ~1.53B in 2025 → USD 9.65B by 2035, CAGR 20.2% — Source: DataM Intelligence, 2025, https://www.datamintelligence.com/research-report/tinyml-market
- **TinyML market (more bullish horizon)** — → USD 10.80B by 2030, CAGR 24.8% (2024–2030) — Source: NextMSC, 2025, https://www.nextmsc.com/report/tinyml-market
- **TinyML / on-device range** — USD 5–10.8B by 2030, CAGR 24.8%–38.1% across sources — Source: aggregated (DataM, NextMSC, Roots Analysis), 2025
- **IoT install base context** — ~21.1B connected IoT devices by end of 2025 (~14% YoY growth) — Source: cited in TinyML market coverage, 2025, https://www.datamintelligence.com/research-report/tinyml-market (secondary; original is IoT Analytics — verify before slide use)

**Range note:** TinyML/edge-inference is small in absolute dollars today (~USD 1.5B) but one of the
faster-growing slices (CAGR 20–38%). This is the most on-thesis market for marrow's wedge, but
the absolute TAM is modest — frame it as "fast-growing enabling layer," not a giant TAM.

---

## 5. Incumbent agent-framework adoption (developer-demand proxy)

GitHub stars and PyPI downloads as of late 2025 / early 2026. Star counts shift daily and differ
across reporting sources — ranges shown where they conflict.

- **LangChain (langchain-ai/langchain) — ~128k–138k GitHub stars** (sources report 128k, ~136k, 137,753) — Source: GitHub org page / repo, 2026, https://github.com/langchain-ai/langchain
- **LangGraph (langchain-ai/langgraph) — 24,800+ GitHub stars; ~38.8M PyPI downloads/month** — Source: repo + framework-comparison coverage, 2026, https://github.com/langchain-ai/langgraph and https://www.buildmvpfast.com/blog/langgraph-vs-crewai-vs-autogen-swarms-agent-framework-2026
- **CrewAI — ~44,300 GitHub stars; ~5.2M PyPI downloads/month** — Source: framework-comparison coverage, 2026, https://www.buildmvpfast.com/blog/langgraph-vs-crewai-vs-autogen-swarms-agent-framework-2026
- **AutoGen (Microsoft) — ~54,000 GitHub stars before merge into the unified Microsoft Agent Framework; ~1.3M PyPI downloads/month** — Source: framework-comparison coverage, 2026, https://www.buildmvpfast.com/blog/langgraph-vs-crewai-vs-autogen-swarms-agent-framework-2026

**Key insight (defensible, supports the marrow thesis):** Stars and downloads tell different
stories — LangGraph leads actual production usage (~38.8M downloads/mo, ~30x AutoGen) despite fewer
stars. **All four incumbents are Python.** This is the gap marrow targets (native C++ runtime).

**Confidence note:** LangChain's own star count is solid (first-party repo). LangGraph/CrewAI/AutoGen
download counts come from a third-party comparison blog, NOT from PyPIStats/pepy.tech directly —
treat as directionally correct, verify exact numbers at pepy.tech before quoting on a slide.

---

## 6. MCP (Model Context Protocol) adoption signals since late-2024 launch

Qualitative + quantitative. MCP is complementary to marrow (marrow is the runtime layer; MCP
is the tool-connection layer), so strong MCP adoption is a tailwind, not a competitor.

- **97M+ monthly SDK downloads** across all languages (reported Dec 2025) — Source: Anthropic, reported Dec 2025, via https://guptadeepak.com/the-complete-guide-to-model-context-protocol-mcp-enterprise-adoption-market-trends-and-implementation-strategies/ (secondary citation of Anthropic figure — verify against Anthropic primary)
- **10,000+ active MCP servers in production; hundreds of distinct AI clients integrated** — Source: Anthropic (reported), Dec 2025, https://en.wikipedia.org/wiki/Model_Context_Protocol
- **Server-catalog growth: ~1,000 servers early 2025 → ~5,800 connectors by April 2025** — Source: MCP adoption coverage, 2025, https://guptadeepak.com/the-complete-guide-to-model-context-protocol-mcp-enterprise-adoption-market-trends-and-implementation-strategies/
- **Vendor adoption: OpenAI officially adopted MCP March 2025** (ChatGPT desktop + products); also adopted by Google DeepMind and Microsoft Copilot — Source: Wikipedia (citing primary announcements), 2025, https://en.wikipedia.org/wiki/Model_Context_Protocol
- **Governance: Anthropic donated MCP to the Agentic AI Foundation (AAIF) under the Linux Foundation in Dec 2025** (co-founded with Block and OpenAI) — Source: Wikipedia, 2025, https://en.wikipedia.org/wiki/Model_Context_Protocol

**Range note:** "Number of servers" varies wildly by source and definition (500 public / 1,000 /
5,800 connectors / 10,000 active) — these count different things (public registry vs. all active vs.
connectors). The cleanest single headline is the Anthropic 97M+ monthly SDK downloads + 10,000+
active servers (Dec 2025).

---

## 7. AI-developer population & enterprises running agents in production

- **AI agents in production — 57% of respondents have agents in production** (2025 survey of 1,340 respondents, Nov 18–Dec 2 2025); up from 51% in the 2024 survey — Source: LangChain "State of AI Agents" / "State of Agent Engineering," 2025, https://www.langchain.com/stateofaiagents and https://www.langchain.com/state-of-agent-engineering
- **Latency is the #2 production challenge (20%)**, behind quality (32%) — Source: LangChain State of AI Agents, 2025, https://www.langchain.com/stateofaiagents (directly supports marrow's latency thesis)
- **Enterprise agent maturity — 62% of organizations experimenting with AI agents, only 23% scaling them** — Source: McKinsey / State of AI 2025 (as reported), 2025, https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai
- **AI-developer population — 17.4M developers using AI/ML tools** (up from 15.5M in 2023), ~64% of all developers; total developer community ~27M (2024) — Source: derived from Stack Overflow / SlashData-style coverage, 2025, https://blog.arcade.dev/global-ai-developer-community-statistics (secondary aggregation — see caveats)
- **84% of developers use or plan to use AI tools; 51% of professional devs use AI daily** — Source: Stack Overflow Developer Survey 2025, https://survey.stackoverflow.co/2025/ai/
- **Retool "State of AI" — ~750 tech professionals surveyed** (2024 edition) — Source: Retool, 2024 (exact production-agent % not captured in this research pass — verify on retool.com before quoting)

---

## 8. Real-time / latency constraints making Python unsuitable for robots/edge ("can't ship Python into a robot")

Best available cited support for the core marrow thesis. Mix of engineering commentary and
academic feasibility studies. None is a single authoritative "you can't ship Python" quote from a
top-tier analyst — it's an engineering consensus, cited below.

- **Python GIL limits true multi-core parallelism; interpretation overhead adds latency unacceptable for ultra-low-latency workloads** — Source: GMI Cloud engineering guide, 2026, https://www.gmicloud.ai/en/blog/how-to-achieve-ultra-low-latency-llm-inference-in-the-cloud-2026-engineering-guide
- **"If you need consistent 1–5 ms loop timing, Python is the wrong layer"; real-time control (100–1000 Hz loops) needs C/C++ for deterministic deadlines** — Source: TheLinuxCode robotics languages guide, 2026, https://thelinuxcode.com/top-6-programming-languages-to-learn-for-robotics-2026-a-senior-engineers-practical-guide/
- **Deterministic-timing / safety-critical control (motor, flight controllers) uses C/C++ for guaranteed response times** — Source: ThinkRobotics, 2026, https://thinkrobotics.com/blogs/indepths/what-coding-language-is-best-for-robotics-complete-guide
- **Academic feasibility study of Python-based embedded real-time control** (confirms the constraints / mitigations are non-trivial) — Source: MDPI Electronics, 2023, https://www.mdpi.com/2079-9292/12/6/1426/htm
- **Ultra-low-latency embedded LLM inference relies on optimized C++ libraries (e.g., TensorRT-LLM compiled to a binary execution graph)** — Source: GMI Cloud, 2026, https://www.gmicloud.ai/en/blog/how-to-achieve-ultra-low-latency-llm-inference-in-the-cloud-2026-engineering-guide
- **On-device VLA / multimodal control research targeting quantized embedded robotics** (evidence the field is actively pushing inference onto the device) — Source: arXiv (LiteVLA-Edge), 2026, https://arxiv.org/pdf/2603.03380

**Cross-reference:** LangChain's own 2025 survey naming **latency as the #2 production challenge (20%)**
(section 7) is the strongest *first-party, agent-specific* data point supporting this thesis — pair it
with the C/C++ deterministic-timing engineering quotes above.

---

## Caveats & confidence

**Analyst-grade / high confidence (safe for an investor slide):**
- Gartner enterprise-software agentic-AI predictions (33% by 2028; 40% of apps by 2026; 40% cancellation by 2027). First-party Gartner press releases.
- Goldman Sachs USD 38B humanoid (2035) and Morgan Stanley USD 5T (2050) — first-party bank research.
- LangChain State of AI Agents 57% in production + latency as #2 challenge — first-party survey, n=1,340, dated Nov–Dec 2025.
- Stack Overflow Developer Survey 2025 (84% use/plan AI; 51% daily) — first-party, large-n.
- LangChain repo star count — first-party GitHub.

**Marketing-driven / report-seller (use the RANGE, not a point; treat as directional):**
- Grand View Research, MarketsandMarkets, Precedence, DataM, NextMSC, BCC, Roots Analysis — all
  syndicated-report vendors. Their 2025 base years cluster tightly (good sign) but terminal-year
  endpoints and CAGRs diverge by methodology. Quote as ranges with the horizon year explicit.

**Soft / needs primary verification before quoting exact numbers:**
- LangGraph / CrewAI / AutoGen PyPI download counts — from a third-party comparison blog, NOT pepy.tech/PyPIStats. Verify exact figures at pepy.tech.
- BofA humanoid figures (18k units 2025 → 10M/yr 2035, 88% CAGR) — cited via secondary coverage, not a BofA primary link captured here.
- MCP "97M monthly SDK downloads" and "10,000+ active servers" — Anthropic figures cited via secondary sources; confirm against Anthropic's primary statement.
- "17.4M AI developers" — secondary aggregation (Arcade.dev citing SlashData/Stack Overflow style data); verify original SlashData report.
- IoT "21.1B devices by 2025" — secondary (original is likely IoT Analytics); verify.
- Retool State of AI production-agent percentage — not captured this pass.

**Where sources diverge widest:**
- Edge AI market: 2025 base USD ~12B–26B; CAGR 18%–37% (definition-driven). Biggest spread in the doc.
- "AI agents" vs. "agentic AI" are reported as separate markets — never sum or directly compare them.
- Humanoid forecasts span USD 38B (2035, Goldman) to USD 5T (2050, Morgan Stanley) — different terminal years AND different scope (robot hardware TAM vs. total economic market). Do not put them side by side without noting the year/scope difference.

**No credible figure found for:**
- A standalone, quantified "embodied AI" market TAM (only humanoid-robot + edge/TinyML proxies exist).
- A single authoritative analyst quote stating "you cannot ship a Python runtime into a robot" — the
  thesis is supported by engineering consensus (GIL, deterministic timing) + LangChain's latency
  data, not by one citable analyst soundbite.
