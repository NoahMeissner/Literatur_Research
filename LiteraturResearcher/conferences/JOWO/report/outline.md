# JOWO Topic Analysis — Report Outline
*Noah Meissner*

---

## 1. Introduction & Motivation

The Joint Ontology Workshops (JOWO) have been held annually since 2015 as a satellite event of FOIS (Formal Ontology in Information Systems), bringing together a broad spectrum of ontology-related workshops under one roof. Over the past decade, the ontology research landscape has shifted considerably — driven by the rise of knowledge graphs, large language models, and applied AI. This raises the question of whether JOWO's thematic focus has followed suit.

**Research Questions:**

> **RQ1**: How has JOWO evolved in terms of topics over the past ten years? Are there emerging trends, or topics that have become less prominent?

> **RQ2**: How does JOWO's thematic profile compare to FOIS — the more selective, formally oriented main conference it accompanies?

**Scope**: The analysis is based on keyword-level data extracted from 492 JOWO papers (2017–2025) and 145 FOIS papers (7 biennial editions: 2016–2025). JOWO 2015 and 2016 are listed in DBLP but could not be extracted and are excluded.

---

## 2. Methodology

### 2.1 Data Collection

Paper metadata (title, authors, year, URL) was collected from DBLP using the following conference scope:

```python
conference_dict = {
    "JOWO": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "FOIS": [2016, 2018, 2020, 2021, 2023, 2024, 2025]
}
```

Since DBLP does not provide abstracts, a custom **PDF Extraction Pipeline** was used to extract abstracts and keywords directly from the papers (see `01_Extraction.ipynb`).

#### PDF Extraction Pipeline

A fault-tolerant, multi-stage pipeline:

1. **Download & Parsing**: PDFs are downloaded from CEUR-WS / IOS Press and the first 5 pages are parsed using `PyMuPDF`.
2. **Regex Extraction** *(fast path)*: Regular expressions attempt to locate abstract and keyword sections by matching structural markers (e.g., "Abstract", "Keywords:").
3. **LLM Fallback** *(slow path)*: If regex fails, the extracted text is passed to a local LLM (`phi4-mini` via Ollama) with a structured prompt to recover the missing fields.
4. **Incremental Storage**: Results are written to CSV after each paper, enabling seamless resumption after interruptions.

#### 2.1.1 Pipeline Evaluation

To assess pipeline quality, a sample of 20 papers was annotated manually against ground-truth keywords (collected via a separate CSV), and the following metrics were computed (see `evaluate_extraction.ipynb`):

| Metric | Method | Value | Assessment |
|---|---|---|---|
| Missing extractions | pipeline | **0.8%** | ✅ Excellent — nearly complete coverage |
| Exact match (keyword string) | sample vs. GT | **85%** | ✅ Good |
| ø Sequence similarity | SequenceMatcher | **0.949** | ✅ Very high textual fidelity |
| Suspiciously short/long | length heuristic | **0%** | ✅ No obvious malformed outputs |
| Sanity check (1st kw in abstract) | substring match | **52%** | ✅ Normal for KR domain |

**Evaluation methodology details:**
- Ground truth keywords were collected manually into `gt.csv` (semicolon-delimited).
- Predicted keywords (`keywords_pdf`) were normalized: lowercased, whitespace-collapsed, then compared using `SequenceMatcher` (character-level similarity) and Jaccard similarity (token-level overlap).
- The sanity check tests whether the first extracted keyword appears anywhere in the abstract — ~52% is expected in the knowledge representation domain where keywords are often technical terms not explicitly repeated in abstracts.
- Papers with neither abstract nor keywords (completely failed PDF parse) were excluded from the evaluation sample; the 0.5% missing rate refers to keyword-level failures among papers with a valid abstract.

**Limitations of the evaluation:**
- The sample size (n = 20) is small; results should be treated as indicative rather than statistically significant.
- Ground truth was manually entered, introducing potential human annotation noise.
- The evaluation only covers keywords, not abstract quality.

### 2.2 Keyword Clustering

To identify high-level topics, extracted keywords were clustered using the following pipeline (see `02_Cluster.ipynb`):

1. **Semantic Embeddings**: Each unique keyword was embedded using the `embeddinggemma` model (via Ollama), capturing distributional meaning.
2. **Dimensionality Reduction**: Embeddings were L2-normalized and reduced to 30 dimensions with PCA.
3. **Optimized K-Means**: K-Means was applied for $k \in [5, 24]$; the Silhouette Score selected $k = 5$ as optimal. The 8 raw clusters were then merged by hand into 5 interpretable macro-clusters based on the most frequent keywords in each:

| Cluster ID | Representative keywords | Macro-label |
|---|---|---|
| 0 | knowledge graph, semantic web, knowledge representation, LLMs, machine learning | **Knowledge Graphs & AI** |
| 1 | ontology, basic formal ontology, ontology engineering, applied ontology | **Ontology Engineering** |
| 2 | mereology, realizable entity, mereotopology, semantics, cognition | **Mereology & Cognition** |
| 3 | disposition, OWL, role, UFO, function, BFO, OntoUML | **Formal Ontology Concepts** |
| 4 | conceptual modeling, formal modeling, enterprise modeling, model | **Conceptual Modeling** |

### 2.3 Visualization

Interactive visualizations were built with Plotly in `04_Analysis.ipynb`:

| Plot | Purpose |
|---|---|
| Stacked area (RQ1) | Full topic composition per year, all clusters stacked to 100% |
| Trend line chart (RQ1) | Per-cluster share over time with computed linear slope annotations |
| Heatmap (RQ1) | Compact share matrix (year × cluster) |
| Top keywords (RQ1) | Top-6 keywords per cluster (all JOWO years combined) |
| Grouped bar (RQ2) | JOWO vs. FOIS average cluster shares side-by-side |
| Divergence heatmap (RQ2) | JOWO − FOIS per-cluster per-FOIS-edition |
| Radar chart (RQ2) | Thematic profile overlay for both venues |
| Faceted timeline (RQ2) | JOWO as continuous line; FOIS as diamond markers at edition years only — no interpolation between editions |

> **FOIS comparison note**: FOIS is biennial. Connecting FOIS data points with a line would imply continuous yearly data that does not exist. All FOIS-vs-JOWO comparisons therefore use either aggregate means or per-edition scatter markers.

---

## 3. Results

### 3.1 RQ1 — JOWO Topic Evolution (2017–2025)

> *JOWO 2016 is listed in DBLP but no papers could be extracted. Analysis covers 492 papers across 9 editions (2017–2025).*

#### Cluster shares per year (%)

| Year | KG & AI | Ont. Eng. | Formal Ont. | Mereology | Concept. Mod. | Papers |
|:----:|--------:|----------:|------------:|----------:|--------------:|------:|
| 2017 | 27.6 | 20.4 | 33.1 | 17.5 | 1.5 | 64 |
| 2018 | 7.2 | 29.0 | 42.0 | 20.3 | 1.4 | 15 |
| 2019 | 24.3 | 21.1 | 35.8 | 16.3 | 2.4 | 79 |
| 2020 | 27.6 | 12.2 | 34.7 | 24.5 | 1.0 | 24 |
| 2021 | 22.0 | 19.9 | 37.9 | 16.8 | 3.5 | 79 |
| 2022 | 26.2 | 11.5 | 34.6 | 24.6 | 3.1 | 29 |
| 2023 | 32.0 | 18.2 | 28.3 | 19.0 | 2.4 | 53 |
| 2024 | **38.9** | 20.7 | 24.5 | 11.6 | 4.3 | 79 |
| 2025 | 28.1 | 17.1 | 36.4 | 17.1 | 1.3 | 70 |

#### Trend summary

| Cluster | 2017 | 2025 | Linear slope | Direction |
|---|---:|---:|---:|---|
| **Knowledge Graphs & AI** | 27.6% | 28.1% | **+1.84%/yr** | ▲ Growing |
| Formal Ontology Concepts | 33.1% | 36.4% | −0.91%/yr | → Stable (volatile) |
| Ontology Engineering | 20.4% | 17.1% | −0.74%/yr | ▼ Slight decline |
| Mereology & Cognition | 17.5% | 17.1% | −0.36%/yr | → Stable |
| Conceptual Modeling | 1.5% | 1.3% | +0.17%/yr | → Marginal niche |

#### Key findings

- **Knowledge Graphs & AI** is the only cluster showing clear upward growth (+1.84%/yr), peaking at **38.9% in 2024** — likely reflecting the community's growing engagement with large language models, semantic web technologies, and data-driven ontology use cases.
- **Formal Ontology Concepts** remains the single largest cluster on average, but is the most volatile (range: 24.5%–42.0%). Year-to-year swings likely reflect variation in which workshops are co-located with JOWO in a given year.
- **Ontology Engineering** and **Mereology & Cognition** are stable but show a gradual retreat, consistent with foundational topics becoming proportionally smaller as the applied wing of JOWO grows.
- **Conceptual Modeling** is a persistent but marginal niche (<5% in every year).
- Overall: JOWO shows a **gradual applied turn** — the share of AI/knowledge-graph work has grown at the expense of foundational formal ontology topics, though the shift is moderate rather than dramatic.

---

### 3.2 RQ2 — JOWO vs. FOIS

> *FOIS coverage: 7 editions (2016, 2018, 2020, 2021, 2023, 2024, 2025), 145 papers. Comparison uses average cluster shares across all available editions. Direct year-by-year comparison is not used due to FOIS's biennial publication schedule.*

#### Average cluster shares across all editions

| Cluster | JOWO | FOIS | Δ (JOWO − FOIS) |
|---|---:|---:|:---:|
| **Knowledge Graphs & AI** | 26.0% | 15.6% | **+10.4 pp** |
| Ontology Engineering | 18.9% | 21.6% | −2.7 pp |
| **Formal Ontology Concepts** | 34.1% | 38.4% | −4.2 pp |
| Mereology & Cognition | 18.6% | 22.0% | −3.4 pp |
| Conceptual Modeling | 2.3% | 2.8% | −0.5 pp |

#### Key findings

- **FOIS is more foundational**: Formal Ontology Concepts (38.4%) and Mereology & Cognition (22.0%) together account for ~60% of FOIS keyword clusters, reflecting its role as the primary venue for philosophically- and logically-grounded ontology theory.
- **JOWO is more applied**: Knowledge Graphs & AI dominates with 26.0% — a **+10.4 percentage-point gap** over FOIS, the largest structural difference across all clusters.
- Ontology Engineering is slightly stronger at FOIS (21.6% vs. 18.9%), suggesting FOIS attracts more work on formal ontology methods and upper-level standards, while JOWO's engineering papers lean more toward practical KG tooling.
- Conceptual Modeling is equally minor at both venues (~2–3%).

#### Interpretation

FOIS and JOWO serve **complementary roles** in the applied ontology research ecosystem:

- **FOIS** → formal foundations, philosophical depth, mereology, upper ontologies
- **JOWO** → applied breadth, knowledge graphs, AI integration, workshop diversity

The KG & AI divergence (+10.4 pp) is the clearest empirical signal of this split. It also aligns with JOWO's workshop structure: the co-located workshops (e.g., WOMoCoE, OAEI-related, KGC) explicitly target applied knowledge representation, pulling the aggregate JOWO profile toward applied/AI topics even within a foundational conference series.

> **Caveat**: The comparison is structurally unequal — 9 JOWO editions vs. 7 FOIS editions. Numbers should be read as directional.

---

## 4. Discussion & Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| **JOWO 2015–2016 missing** | Reduces temporal scope; trend analysis starts at 2017 | Annotated in all plots; n=5 remaining years sufficient for slope estimation |
| **Small evaluation sample** (n=20) | Evaluation metrics not statistically robust | Results are indicative; the 0.8% missing rate across the full corpus provides a complementary coverage signal |
| **5 macro-clusters only** | Within-cluster shifts invisible (e.g., LLMs within "KG & AI") | Deliberate tradeoff for interpretability; finer-grained analysis would require more labeled data |
| **FOIS biennial schedule** | Year-for-year trend comparison infeasible | Aggregate means + per-edition divergence heatmap used instead of trend lines |
| **Keyword extraction bias** | Papers with no PDF access or poorly formatted PDFs are excluded | 82–100% coverage per year; excluded papers unlikely to be systematically biased in topic |
| **Cluster assignment subjectivity** | Macro-cluster labels assigned by human inspection | Representative keywords listed; silhouette-optimized k=5 provides objective base |