"""
PDF Abstract & Keyword Extractor
================================
Mehrstufige Extraktion:
  1. Regex (schnell, kostenlos)
  2. Ollama-Fallback (lokal, kostenlos, braucht laufenden Ollama-Server)

Usage:
    from src.extractors.pdf_extractor import PDFExtractor

    extractor = PDFExtractor(ollama_model="phi4-mini")

    # Einzelnes PDF
    result = extractor.extract_from_url("https://ceur-ws.org/Vol-3882/...")
    print(result)  # {"abstract": "...", "keywords": "...", "source": "regex"}

    # Ganzer DataFrame
    df_enriched = extractor.run_pipeline(df, url_column="ee")
"""

import re
import time
import json
import requests
import io
from typing import Optional, Tuple, Dict

import pandas as pd

from litresearch.extractors.iospress_extractor import IOSPressDownloader

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import ollama as _ollama
except ImportError:
    _ollama = None


class PDFExtractor:
    """Extracts abstract and keywords from scientific PDFs (URL → text → regex → Ollama)."""

    def __init__(
        self,
        ollama_model: str = "phi4-mini",
        use_ollama_fallback: bool = True,
        request_timeout: int = 30,
    ):
        self.ollama_model = ollama_model
        self.use_ollama_fallback = use_ollama_fallback
        self.request_timeout = request_timeout

        if fitz is None:
            raise ImportError(
                "PyMuPDF wird benötigt: pip install PyMuPDF"
            )

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def extract_from_url(self, pdf_url: str) -> Dict[str, Optional[str]]:
        """
        Lade ein PDF von *pdf_url* herunter und extrahiere Abstract + Keywords.

        Returns dict mit keys: abstract, keywords, source
        source ist "regex", "regex+ollama", oder "failed"
        """
        text = self._download_and_extract_text(pdf_url)
        if not text:
            return {"abstract": None, "keywords": None, "source": "failed"}

        return self._extract_metadata(text)

    def run_pipeline(
        self,
        df: pd.DataFrame,
        url_column: str = "ee",
        delay: float = 0.5,
        save_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Verarbeite einen DataFrame: für jede Zeile PDF herunterladen und
        Abstract/Keywords extrahieren. Mit Resume-Support über 'save_path'.

        Parameters
        ----------
        df : pd.DataFrame
            Muss eine Spalte *url_column* mit PDF-URLs enthalten.
        url_column : str
            Name der Spalte mit den PDF-Links (default: "ee").
        delay : float
            Pause zwischen Downloads in Sekunden.

        Returns
        -------
        pd.DataFrame
            Kopie des Inputs mit neuen Spalten:
            abstract_pdf, keywords_pdf, extraction_source
        """
        # ── Setup & Resume Logic ──
        df = df.copy()
        
        # Sicherstellen, dass unsere Ziel-Spalten existieren
        for col in ["abstract_pdf", "keywords_pdf", "extraction_source"]:
            if col not in df.columns:
                df[col] = None

        # Wenn save_path existiert, laden wir die alten Ergebnisse um fortzusetzen
        import os
        if save_path and os.path.exists(save_path):
            print(f"  -> Lade bereits verarbeiteten Stand von: {save_path}")
            df_saved = pd.read_csv(save_path)
            
            for col in ["abstract_pdf", "keywords_pdf", "extraction_source"]:
                if col in df_saved.columns:
                    # Wir mappen über die URL, da to_csv(index=False) den Pandas Index verliert
                    valid_saved = df_saved.dropna(subset=[url_column])
                    # Erzeuge URL -> Wert Mapping
                    mapping = dict(zip(valid_saved[url_column], valid_saved[col]))
                    
                    for idx, url in df[url_column].items():
                        if url in mapping:
                            val = mapping[url]
                            # Pandas liest leere strings oft als NaN ein, das berücksichtigen
                            if pd.notna(val) or isinstance(val, str):
                                df.at[idx, col] = val

        urls = df[url_column].fillna("")
        total = len(df)
        stats = {"regex": 0, "regex+ollama": 0, "failed": 0, "skipped": 0}

        for i, (idx, url) in enumerate(urls.items()):
            title = str(df.at[idx, "title"])[:55] if "title" in df.columns else ""
            
            # Überspringen, wenn es in diesem Durchlauf schon einen Eintrag gibt
            # "failed" versuchen wir neu, wenn es davor wegen DOI abgebrochen ist
            current_source = str(df.at[idx, "extraction_source"])
            if current_source in ["regex", "regex+ollama"]:
                print(f"[{i+1}/{total}] Überspringe (bereits extrahiert): {title}")
                stats["skipped"] += 1
                continue
                
            print(f"[{i+1}/{total}] Extrahiere: {title}")

            if not url or not isinstance(url, str) or not url.startswith("http"):
                print("  ✗ Keine gültige URL\n")
                df.at[idx, "extraction_source"] = "failed"
                stats["failed"] += 1
                continue

            result = self.extract_from_url(url)

            df.at[idx, "abstract_pdf"] = result["abstract"]
            df.at[idx, "keywords_pdf"] = result["keywords"]
            df.at[idx, "extraction_source"] = result["source"]
            stats[result["source"]] = stats.get(result["source"], 0) + 1

            a = "✓" if result["abstract"] else "✗"
            k = "✓" if result["keywords"] else "✗"
            print(f"  [{result['source']}] abstract={a}  keywords={k}\n")
            
            # Progressives Speichern nach jedem Paper!
            if save_path:
                df.to_csv(save_path, index=False)

            if delay > 0:
                time.sleep(delay)

        print("─" * 50)
        print(f"✓ Nur Regex:        {stats.get('regex', 0)}")
        print(f"✓ Regex + Ollama:   {stats.get('regex+ollama', 0)}")
        print(f"✗ Fehlgeschlagen:   {stats.get('failed', 0)}")
        print(f"⏭ Übersprungen:     {stats.get('skipped', 0)}")

        return df

    # ──────────────────────────────────────────────
    # PDF Download & Text-Extraktion
    # ──────────────────────────────────────────────

    def _download_and_extract_text(self, url: str) -> Optional[str]:
        """Download PDF and extract text with PyMuPDF (first 5 pages)."""
        try:
            if "iospress.nl" in url or "10.3233" in url:
                downloader = IOSPressDownloader(request_timeout=self.request_timeout)
                pdf_bytes = downloader.download_pdf_bytes(url)
                if not pdf_bytes:
                    return None
            else:
                resp = requests.get(url, timeout=self.request_timeout)
                resp.raise_for_status()
                pdf_bytes = resp.content
        except Exception as e:
            print(f"  ✗ Download fehlgeschlagen: {e}")
            return None

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages_to_read = min(5, len(doc))
            text = "\n".join(
                doc[p].get_text("text") for p in range(pages_to_read)
            )
            doc.close()
            return text
        except Exception as e:
            print(f"  ✗ PDF-Parsing fehlgeschlagen: {e}")
            return None

    # ──────────────────────────────────────────────
    # Stufe 1: Regex-Extraktion
    # ──────────────────────────────────────────────

    @staticmethod
    def _extract_with_regex(text: str) -> Tuple[Optional[str], Optional[str]]:
        """Versuche Abstract und Keywords mit Regex zu finden."""
        # Normalize whitespace
        text_clean = re.sub(r'[ \t]+', ' ', text)
        text_clean = re.sub(r'\n{3,}', '\n\n', text_clean)

        abstract = None
        keywords = None

        # ── Abstract ────────────────────────────────
        abs_patterns = [
            # "Abstract" gefolgt von Text bis "Keywords", "Introduction", etc.
            r'(?i)\babstract\b[.\s:—-]*\n(.*?)'
            r'(?=\n\s*(?:keywords?|index\s*terms?|1[\.\s]+intro|\bintroduction\b|categories|acm))',
            # Fallback: "Abstract" gefolgt von 1-3 Absätzen
            r'(?i)\babstract\b[.\s:—-]*\n(.*?)(?:\n\n)',
        ]
        for pat in abs_patterns:
            m = re.search(pat, text_clean, re.DOTALL)
            if m:
                candidate = re.sub(r'\s+', ' ', m.group(1)).strip()
                if len(candidate) > 50:  # mindestens ~50 Zeichen
                    abstract = candidate
                    break

        # ── Keywords ────────────────────────────────
        kw_patterns = [
            r'(?i)(?:keywords?|index\s*terms?|key\s*words?)[:\s—·.,-]*\n?(.*?)'
            r'(?=\n\s*(?:\d+[\.\s]+|\bintroduction\b|\n\n|ACM|Categories))',
            r'(?i)(?:keywords?|key\s*words?)[:\s—·.,-]*(.*?)(?:\n\n|\.\s*\n)',
        ]
        for pat in kw_patterns:
            m = re.search(pat, text_clean, re.DOTALL)
            if m:
                candidate = re.sub(r'\s+', ' ', m.group(1)).strip()
                # Mindestens 5 Zeichen und nicht zu lang (> 500 = wahrscheinlich falsch)
                if 5 < len(candidate) < 500:
                    keywords = candidate
                    break

        return abstract, keywords

    # ──────────────────────────────────────────────
    # Stufe 2: Ollama-Fallback
    # ──────────────────────────────────────────────

    def _extract_with_ollama(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Nutze ein lokales LLM via Ollama als Fallback."""
        if _ollama is None:
            print("    ⚠️ ollama-Paket nicht installiert (pip install ollama)")
            return None, None

        try:
            response = _ollama.chat(
                model=self.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract from this scientific paper text. "
                            "Return ONLY valid JSON: "
                            '{"abstract": "...", "keywords": "..."} '
                            "Use null if not found. No explanation."
                        ),
                    },
                    {"role": "user", "content": text[:3000]},
                ],
                format="json",
                options={"temperature": 0},
            )
            result = json.loads(response["message"]["content"])
            return result.get("abstract"), result.get("keywords")
        except Exception as e:
            print(f"    ✗ Ollama-Fehler: {e}")
            return None, None

    # ──────────────────────────────────────────────
    # Mehrstufige Logik
    # ──────────────────────────────────────────────

    def _extract_metadata(self, text: str) -> Dict[str, Optional[str]]:
        """Regex zuerst, dann Ollama-Fallback für fehlende Felder."""
        abstract, keywords = self._extract_with_regex(text)

        regex_abs = abstract is not None
        regex_kw = keywords is not None

        # Wenn beides gefunden → fertig
        if regex_abs and regex_kw:
            return {"abstract": abstract, "keywords": keywords, "source": "regex"}

        # Ollama-Fallback nur wenn aktiviert
        if self.use_ollama_fallback and (not regex_abs or not regex_kw):
            print(
                f"    → Regex: abstract={'✓' if regex_abs else '✗'}  "
                f"keywords={'✓' if regex_kw else '✗'}  → Ollama..."
            )
            llm_abs, llm_kw = self._extract_with_ollama(text)

            if not regex_abs:
                abstract = llm_abs
            if not regex_kw:
                keywords = llm_kw

            return {"abstract": abstract, "keywords": keywords, "source": "regex+ollama"}

        # Nur Regex-Ergebnis (Ollama deaktiviert)
        source = "regex" if (regex_abs or regex_kw) else "failed"
        return {"abstract": abstract, "keywords": keywords, "source": source}
