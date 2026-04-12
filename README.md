# LiteraturResearcher

> An automated pipeline for the systematic extraction, clustering, and thematic analysis of scientific publications — designed for multi-conference bibliometric studies.

---

## What This Project Does

`LiteraturResearcher` collects paper metadata from scientific databases, extracts abstracts and keywords from PDFs using a multi-stage LLM-assisted pipeline, clusters keywords into thematic topics, and produces interactive visualizations to answer bibliometric research questions.

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
├── conferences/                  # One subdirectory per conference / case study
│   └── <ConferenceName>/
│       ├── notebooks/
│       │   ├── 01_Extraction.ipynb   # DBLP pull + PDF extraction
│       │   ├── 02_Cluster.ipynb      # Keyword embedding + K-Means clustering
│       │   └── 04_Analysis.ipynb     # Research question visualizations (Plotly)
│       └── report/
│           └── outline.md            # Full analysis report
│
└── data/
    ├── raw/conferences/
    └── processed/
```

---

## Case Studies & Reports

Detailed findings, research questions, and analysis results are documented in the respective conference reports:

| Conference | Report |
|---|---|
| JOWO & FOIS (2017–2025) | [conferences/JOWO/report/outline.md](conferences/JOWO/report/outline.md) |

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

Create a `.env` file in the project root (for Open Alex):

```env
MY_EMAIL = 
API_KEY = 
```
### Run a conference analysis

```
1. conferences/<Name>/notebooks/01_Extraction.ipynb   ← collect papers + extract PDFs
2. conferences/<Name>/notebooks/02_Cluster.ipynb       ← embed + cluster keywords
3. conferences/<Name>/notebooks/04_Analysis.ipynb      ← visualize research questions
```

See the corresponding `report/outline.md` inside the conference folder for full results and interpretation.

---

## Data Notes

- Raw data lives in `data/raw/` and is excluded from version control (see `.gitignore`).
- Each conference folder manages its own extracted datasets under `data/raw/conferences/`.
