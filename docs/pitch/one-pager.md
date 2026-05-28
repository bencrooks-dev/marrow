# marrow — one-pager

**The embeddable agent runtime for AI that runs where you can't ship Python.**
Reference implementation of **ARI**, the open Agent Runtime Interface.

---

**Problem.** AI agents are moving into production (57% of teams run agents in prod
— *LangChain, 2025*) and escaping the data center — into robots, edge devices, and
native apps. Every mature framework (LangChain, LangGraph, CrewAI, AutoGen) is
**Python-locked**, and latency is already the **#2 production blocker** (*LangChain,
2025*). You cannot ship a CPython runtime into a real-time robot or a customer's
native binary.

**Solution.** **marrow** is a native **C++17** agent runtime — state, providers,
tools, routing, lifecycle — embeddable with **no managed runtime required**,
ergonomic from Python. It is the **reference implementation of ARI**, an open
standard for the agent *runtime* layer that sits **beneath MCP and A2A**
(complementary, not competitive).

**Why it wins (the moat).** ARI's **Embedded profile** is defined by constraints a
Python framework *structurally cannot meet* — native core, bounded memory,
mandatory cancellation/timeouts, near-zero dependencies. We own both the
**standard** and its **reference implementation**, plus a **conformance kit** that
makes "ARI-conformant" falsifiable by anyone. Standard + implementation + proof.

**Market (cited, framed honestly).** AI-agents market ~$7B in 2025 at ~44–50% CAGR
(*syndicated; range*); humanoid robotics TAM **~$38B by 2035** (*Goldman Sachs*);
enterprise agentic-AI adoption **33% of apps by 2028** (*Gartner*). Our wedge
(embedded/embodied) is the fastest-growing enabling layer — an early-mover window.

**Status (honest).** Pre-alpha (0.1.0). Shipped: ARI spec v0.1, reference
implementation, conformance kit, STRIDE threat model + security hardening + CI
scanning. **External users: 0.** First deployment target: Tilo (humanoid).

**Traction / Team / Ask.** *Template — replace with real figures, do not present as
fact:* design partners `[e.g., 1 robotics + 1 trading]`; founder `[name +
background]`; raising `[$1.5M pre-seed, illustrative]` for `[embedded runtime, Tilo
integration, a second conformant implementation, standards evangelism]`.

**Links.** Spec: `ARI-SPEC.md` · Strategy: `docs/ari-strategy.md` · Threat model:
`THREAT-MODEL.md` · Repo: github.com/bencrooks-dev/marrow
