# LiteraturResearcher

> An automated pipeline for the systematic extraction, clustering, and thematic analysis of scientific publications — with a dedicated case study on the Joint Ontology Workshops (JOWO) and FOIS.

---

## What This Project Does

`LiteraturResearcher` collects paper metadata from scientific databases, extracts abstracts and keywords from PDFs using a multi-stage LLM-assisted pipeline, clusters keywords into thematic topics, and produces interactive visualizations to answer bibliometric research questions.

**Current case study:** *Ten years of JOWO (2017–2025) — topic evolution and comparison to FOIS.*

### Key capabilities

| Capability | Details |
|---|---|
| **Metadata collection** | DBLP, OpenAlex, Semantic Scholar |
| **PDF extraction** | PyMuPDF + Regex → Ollama LLM fallback (phi4-mini) |
| **Keyword clustering** | Sentence embeddings (embeddinggemma) + PCA + K-Means |
| **Evaluation** | Manual ground-truth comparison with SequenceMatcher & Jaccard metrics |
| **Visualization** | Interactive Plotly charts (stacked area, heatmaps, radar, trend lines) |

---

## Project Structure

```
LiteraturResearcher/
├── litresearch/                  # Core Python library
│   ├── api_clients/
│   │   ├── request_openAlex.py   # OpenAlex API client
│   │   └── request_semantic_scholar.py
│   └── extractors/
│       ├── DBLP_Extractor.py     # DBLP metadata scraper
│       ├── pdf_extractor.py      # PDF download + Regex/LLM extraction
│       └── iospress_extractor.py # IOS Press-specific POST-based scraper
│
├── pipelines/                    # General-purpose notebooks
│   ├── 01_Extract.ipynb          # Base extraction pipeline
│   ├── 03_Open_Alex.ipynb        # OpenAlex enrichment
│   └── evaluate_extraction.ipynb # LLM extraction quality evaluation
│
├── conferences/
│   └── JOWO/                     # JOWO & FOIS case study
│       ├── notebooks/
│       │   ├── 01_Extraction.ipynb   # DBLP pull + PDF extraction for JOWO/FOIS
│       │   ├── 02_Cluster.ipynb      # Keyword embedding + K-Means clustering
│       │   └── 04_Analysis.ipynb     # RQ1 & RQ2 visualizations (Plotly)
│       └── report/
│           └── outline.md            # Full analysis report
│
└── data/
    ├── raw/conferences/ontology/
    │   ├── jowo_fois_with_abstracts.csv       # 637 papers with extracted abstracts & keywords
    │   └── jowo_fois_cluster_keywords.csv     # Keyword→cluster frequency table
    └── processed/
```

---

## JOWO Case Study — Research Questions

### RQ1 — How has JOWO evolved thematically over the past ten years?

Based on 492 JOWO papers (2017–2025), keyword clusters were tracked across years:

| Cluster | Avg. share | Trend |
|---|---:|---|
| Formal Ontology Concepts | ~34% | → stable (volatile) |
| Knowledge Graphs & AI | ~26% | **▲ +1.84%/yr** |
| Ontology Engineering | ~19% | ▼ slight decline |
| Mereology & Cognition | ~19% | → stable |
| Conceptual Modeling | ~2% | → marginal niche |

**Key finding:** JOWO shows a gradual applied turn — Knowledge Graphs & AI peaked at **38.9% in 2024**, while foundational topics (Mereology, Formal Ontology) are proportionally declining.

### RQ2 — How does JOWO compare to FOIS?

Based on 145 FOIS papers across 7 biennial editions (2016–2025):

| Cluster | JOWO | FOIS | Δ |
|---|---:|---:|---:|
| Knowledge Graphs & AI | 26.0% | 15.6% | **+10.4 pp** |
| Formal Ontology Concepts | 34.1% | 38.4% | −4.2 pp |
| Mereology & Cognition | 18.6% | 22.0% | −3.4 pp |
| Ontology Engineering | 18.9% | 21.6% | −2.7 pp |

**Key finding:** FOIS anchors foundational/philosophical ontology (~60% of topics in Formal Ontology + Mereology); JOWO increasingly embraces applied AI/KG work. The +10.4 pp gap in Knowledge Graphs & AI is the clearest structural difference.

> ⚠️ FOIS is biennial — year-by-year trend comparisons are not used; aggregate means and per-edition divergence heatmaps are used instead.

---

## PDF Extraction Pipeline

```
PDF URL
  └─► PyMuPDF (first 5 pages)
        ├─► Regex extraction  ──► ✅ abstract + keywords found
        └─► [fallback] Ollama LLM (phi4-mini)  ──► ✅ structured extraction
```

### Evaluation results (`evaluate_extraction.ipynb`)

Evaluated on a manually annotated sample (n = 20 papers, ground truth in `gt.csv`):

| Metric | Value |
|---|---|
| Missing extractions (full corpus) | **0.5%** |
| Exact keyword match (sample) | **85%** |
| ø Sequence similarity | **0.949** |
| Suspiciously short/long outputs | **0%** |
| Sanity check (1st keyword in abstract) | **52%** *(expected for KR domain)* |

---

## Setup

### Requirements

```bash
pip install pandas numpy plotly scikit-learn pymupdf requests python-dotenv jupyter
```

A local [Ollama](https://ollama.com/) instance is required for LLM-based extraction:

```bash
ollama pull phi4-mini
ollama pull embeddinggemma  # for keyword clustering
```

### Environment

Create a `.env` file in the project root:

```env
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

> ⚠️ Never commit `.env` to a public repository.

### Run the JOWO analysis

```
1. conferences/JOWO/notebooks/01_Extraction.ipynb   ← collect papers + extract PDFs
2. conferences/JOWO/notebooks/02_Cluster.ipynb       ← embed + cluster keywords
3. conferences/JOWO/notebooks/04_Analysis.ipynb      ← visualize RQ1 & RQ2
```

The full report is in [`conferences/JOWO/report/outline.md`](conferences/JOWO/report/outline.md).

---

## Data Notes

- Raw data lives in `data/raw/` and is excluded from version control (see `.gitignore`).
- JOWO 2015 and 2016 are listed in DBLP but could not be extracted — analysis starts at 2017.
- FOIS coverage: 7 editions (2016, 2018, 2020, 2021, 2023, 2024, 2025).
