# Solution Architect Skill

## Purpose

Guide how to decompose a problem from first principles, structure a solution narrative, and deliver it in a way that demonstrates clear reasoning over polished results.

## First-Principles Problem Decomposition

When facing a new challenge, follow this sequence strictly:

1. **Identify the core question.** Strip away context until you can state the problem in one sentence. For this challenge: "What are the highest-impact energy cost levers for Henkel Holthausen, measured in EUR/ton?"

2. **Map the constraint space.** Before proposing solutions, enumerate what limits the answer:
   - Physical constraints (thermodynamics, site layout, grid connection capacity)
   - Regulatory constraints (grid fee rules, emissions trading, building codes)
   - Data constraints (what we know publicly vs what we'd need from Henkel)
   - Economic constraints (CAPEX budgets, payback requirements, commodity prices)

3. **Rank use cases by impact, not by complexity.** For each candidate use case, estimate the EUR/ton delta it could deliver. Cut anything below a materiality threshold. Explain why you cut it.

4. **Show the reasoning chain, not just the answer.** For every assumption:
   - State the assumption explicitly
   - State where the number comes from (report, calculation, benchmark)
   - State what alternative you considered and why you rejected it
   - State what would change if the assumption were wrong (sensitivity)

5. Make sure delivered reasoning output is concise, defensible, and impactful.

## Deliverable Standards for RIZM

1. **Method Over Outcome:** RIZM explicitly states they evaluate *how you got there*, not whether the numbers are right. Prioritize clean reasoning chains over precise outputs.
2. **Direct Metric Translation:** Every energy optimization output MUST be translated into EUR/ton of industrial output (based on Henkel Holthausen's ~450,000 tons/yr product baseline).
3. **Clean Software Engineering:** Modern Python standard (`pyproject.toml`), environment reproducibility via `uv`, modular architecture separating IO from optimization, type hinting, and clear documentation.
4. **Toolchain Transparency:** RIZM requires explicit declaration of all tools, LLMs, and data sources used. Do not hide AI assistance -- declare it clearly in README.md.
5. **No Filler:** A great submission can be six paragraphs and one spreadsheet. Do not pad with tables or pages that do not carry reasoning. Every section must earn its place.

## On-Site Protocol Design

When recommending what to ask for in a first visit:
- **Data Request:** Choose the single dataset that would most reduce uncertainty in the model. Justify *why this dataset* eliminates more unknowns than any other single request. For this challenge: 15-minute coincidental time-series of steam demand by pressure level and electrical load.
- **Stakeholder Meeting:** Choose the single person who controls both operational data access and investment decision authority. Justify the choice. For this challenge: the Head of On-Site Energy & Infrastructure (Leiter Energieversorgung).

## Online References

| Topic | URL | What it provides |
|-------|-----|-----------------|
| RIZM Public Material | https://rizm.de | Company positioning, product vision, Agentic Energy OS concept |
| Fermi Estimation Techniques | https://www.lesswrong.com/tag/fermi-estimation | Structured approaches to back-of-envelope reasoning |
| First Principles Thinking | https://fs.blog/first-principles/ | Farnam Street guide to reasoning from fundamentals |
| McKinsey Problem Solving | https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/how-we-help-clients/problem-solving | Structured problem decomposition frameworks |
| Henkel Duesseldorf Site Facts | https://www.henkel.de/presse-und-medien/zahlen-und-fakten/standort-duesseldorf | Public data about the Henkel Holthausen manufacturing site |
