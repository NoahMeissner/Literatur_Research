import time
import math
import requests
import csv
import os
import re
import pandas as pd
from urllib.parse import quote
from tqdm import tqdm


class RateLimitException(Exception):
    pass


DOI_PATTERN = re.compile(r'^10\.\d{4,}/.+', re.IGNORECASE)


def normalize_doi(value) -> str:
    if not value or pd.isna(value):
        return ""
    clean = str(value).strip()
    clean = re.sub(r'^https?://(dx\.)?doi\.org/', '', clean)
    clean = re.sub(r'^doi:\s*', '', clean, flags=re.IGNORECASE)
    return clean.lower()


def is_valid_doi(value) -> bool:
    return bool(DOI_PATTERN.match(normalize_doi(value)))


class OpenAlexFetcher:
    DEFAULT_OUTPUT_FILE = "openalex_results.csv"
    FIELDNAMES = ["original_index", "oa_id", "author_keywords", "ai_concepts", "abstract"]
    LIST_COST   = 0.0001
    SEARCH_COST = 0.001

    def __init__(
        self,
        email: str,
        api_key: str = None,
        output_file: str = DEFAULT_OUTPUT_FILE,
        batch_size: int = 100,
        request_delay: float = 0.05,
        concept_min_level: int = 2,
        concept_min_score: float = 0.6,
        doi_fallback_to_title: bool = True,  # ← NEU
        **kwargs,
    ):
        self.email = email
        self.api_key = api_key
        self.output_file = output_file
        self.batch_size = batch_size
        self.request_delay = request_delay
        self.concept_min_level = concept_min_level
        self.concept_min_score = concept_min_score
        self.doi_fallback_to_title = doi_fallback_to_title

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _headers(self):
        return {"User-Agent": f"mailto:{self.email}"}

    def _add_api_key(self, url: str) -> str:
        if self.api_key:
            url += f"&api_key={self.api_key}"
        return url

    def _handle_rate_limit_headers(self, response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining:
            try:
                if float(remaining) < 0.05:
                    print(f"\n[WARNUNG] Budget fast aufgebraucht (${float(remaining):.4f}). Pausiere 300s...")
                    time.sleep(300)
            except ValueError:
                pass

    def _exponential_backoff(self, attempt: int):
        wait = min(2 ** attempt * 5, 300)
        print(f"\n[429] Backoff: Warte {wait}s (Versuch {attempt})...")
        time.sleep(wait)

    def _check_budget(self):
        if not self.api_key:
            return
        try:
            r = requests.get(
                f"https://api.openalex.org/rate-limit?api_key={self.api_key}",
                headers=self._headers(), timeout=10
            )
            if r.status_code == 200:
                data = r.json().get("rate_limit", {})
                remaining = data.get("daily_remaining_usd")
                if remaining is not None:
                    print(f"  Budget heute noch: ${remaining:.4f}")
                    if remaining < 0.05:
                        reset_in = data.get("resets_in_seconds", 3600)
                        raise RateLimitException(
                            f"Budget aufgebraucht. Reset in {reset_in//3600}h {(reset_in%3600)//60}m"
                        )
        except requests.RequestException:
            pass

    # ── Resume-Support ────────────────────────────────────────────────────────

    def _load_processed(self) -> set:
        """Lädt bereits erfolgreich verarbeitete Indizes (inkl. NOT_FOUND aus Phase 1)."""
        if not os.path.exists(self.output_file):
            return set()
        try:
            ex = pd.read_csv(self.output_file)
            valid = ex[
                (ex["oa_id"] != "RATE_LIMIT") &
                (ex["oa_id"] != "NOT_FOUND") & 
                (~ex["oa_id"].astype(str).str.startswith("ERROR_"))
            ]
            return set(valid["original_index"].unique())
        except Exception:
            return set()

    def _load_not_found(self) -> set:
        """Gibt Indizes zurück die in Phase 1 als NOT_FOUND markiert wurden."""
        if not os.path.exists(self.output_file):
            return set()
        try:
            ex = pd.read_csv(self.output_file)
            return set(ex[ex["oa_id"] == "NOT_FOUND"]["original_index"].unique())
        except Exception:
            return set()

    # ── API-Calls ─────────────────────────────────────────────────────────────

    def _fetch_batch_by_doi(self, rows: list) -> dict:
        doi_map = {
            normalize_doi(r.get("doi", "")): r.name
            for r in rows
            if is_valid_doi(r.get("doi", ""))
        }
        if not doi_map:
            return {}

        all_results = {}
        current_batch = []
        current_length = 0
        MAX_URL_LENGTH = 4000
        base_url_length = len(
            "https://api.openalex.org/works?filter=doi:"
            "&select=id,display_name,doi,keywords,concepts,abstract_inverted_index"
            "&per_page=100"
        )
        if self.api_key:
            base_url_length += len(f"&api_key={self.api_key}")

        for doi in doi_map.keys():
            addition = len(doi) + 3
            if current_length + base_url_length + addition > MAX_URL_LENGTH and current_batch:
                all_results.update(self._fetch_doi_subbatch(current_batch))
                current_batch = []
                current_length = 0
            current_batch.append(doi)
            current_length += addition

        if current_batch:
            all_results.update(self._fetch_doi_subbatch(current_batch))

        return all_results

    def _fetch_doi_subbatch(self, dois: list) -> dict:
        url = self._add_api_key(
            f"https://api.openalex.org/works"
            f"?filter=doi:{'|'.join(dois)}"
            f"&select=id,display_name,doi,keywords,concepts,abstract_inverted_index"
            f"&per_page=100"
        )
        time.sleep(self.request_delay)
        resp = requests.get(url, headers=self._headers(), timeout=30)
        self._handle_rate_limit_headers(resp)

        if resp.status_code == 429:
            self._exponential_backoff(attempt=1)
            raise RateLimitException("429 auf DOI-Batch")
        if resp.status_code == 400:
            print(f"\n[400] Sub-Batch übersprungen ({len(dois)} DOIs zu lang)")
            return {}
        resp.raise_for_status()
        return {
            normalize_doi(hit.get("doi", "")): hit
            for hit in resp.json().get("results", [])
        }

    def _fetch_single_by_title(self, row) -> "dict | None":
        title, year = row.get("title"), row.get("year")
        if pd.isna(title):
            return None

        url = self._add_api_key(
            f"https://api.openalex.org/works"
            f"?filter=title.search:{quote(str(title))},publication_year:{int(year)}"
            f"&select=id,display_name,keywords,concepts,abstract_inverted_index"
            f"&per_page=1"
        )
        time.sleep(self.request_delay)
        resp = requests.get(url, headers=self._headers(), timeout=15)
        self._handle_rate_limit_headers(resp)

        if resp.status_code == 429:
            raise RateLimitException("429 auf Title-Search")
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return results[0] if results else None
        return None

    def _write_title_search(self, row, writer, f):
        """Title-Search mit Retry für eine einzelne Row."""
        for attempt in range(3):
            try:
                hit = self._fetch_single_by_title(row)
                writer.writerow(
                    self._parse_hit(hit, row.name) if hit
                    else {**self._empty_result(row.name), "oa_id": "NOT_FOUND"}
                )
                f.flush()
                break
            except RateLimitException:
                if attempt == 2:
                    raise
                self._exponential_backoff(attempt + 1)

    # ── Haupt-Methode ─────────────────────────────────────────────────────────

    def fetch(self, df: pd.DataFrame) -> pd.DataFrame:
        has_doi = "doi" in df.columns and df["doi"].apply(is_valid_doi).any()

        processed = self._load_processed()
        rows_todo = [row for _, row in df.iterrows() if row.name not in processed]

        if not rows_todo:
            print("Nichts mehr zu tun – alle Papers bereits verarbeitet.")
            return pd.read_csv(self.output_file) if os.path.exists(self.output_file) else pd.DataFrame()

        n = len(rows_todo)
        if has_doi:
            n_doi    = sum(1 for r in rows_todo if is_valid_doi(r.get("doi", "")))
            n_no_doi = n - n_doi
            if self.doi_fallback_to_title:
                cost = math.ceil(n_doi / self.batch_size) * self.LIST_COST + n_no_doi * self.SEARCH_COST
            else:
                cost = math.ceil(n_doi / self.batch_size) * self.LIST_COST
            print(f"Verbleibend: {n} | Mit DOI: {n_doi} (Batch) | Ohne DOI: {n_no_doi} (Title-Search)")
        else:
            cost = n * self.SEARCH_COST
            print(f"Verbleibend: {n} | Nur Title-Search")

        mode = "mit Fallback" if self.doi_fallback_to_title else "Phase 1 (kein Fallback)"
        print(f"Geschätzte Kosten: ${cost:.3f} | Modus: {mode} | Output: {self.output_file}")

        write_header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0

        with open(self.output_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            if write_header:
                writer.writeheader()

            for batch_start in tqdm(range(0, n, self.batch_size)):
                batch = rows_todo[batch_start: batch_start + self.batch_size]

                if batch_start > 0 and batch_start % (50 * self.batch_size) == 0:
                    self._check_budget()

                if has_doi:
                    doi_rows    = [r for r in batch if is_valid_doi(r.get("doi", ""))]
                    no_doi_rows = [r for r in batch if not is_valid_doi(r.get("doi", ""))]

                    # DOI-Batch
                    if doi_rows:
                        hits = self._fetch_batch_by_doi(doi_rows)
                        for row in doi_rows:
                            hit = hits.get(normalize_doi(row.get("doi", "")))
                            if hit:
                                writer.writerow(self._parse_hit(hit, row.name))
                            elif self.doi_fallback_to_title:
                                # Phase 2-Modus: sofort Title-Search
                                self._write_title_search(row, writer, f)
                            else:
                                # Phase 1-Modus: NOT_FOUND speichern, Phase 2 holt sie
                                writer.writerow({**self._empty_result(row.name), "oa_id": "NOT_FOUND"})

                    # Rows ohne DOI im Batch
                    for row in no_doi_rows:
                        if self.doi_fallback_to_title:
                            self._write_title_search(row, writer, f)
                        else:
                            writer.writerow({**self._empty_result(row.name), "oa_id": "NOT_FOUND"})
                else:
                    for row in batch:
                        self._write_title_search(row, writer, f)

                f.flush()

        print(f"\nFertig! Ergebnisse in: {self.output_file}")
        return pd.read_csv(self.output_file)

    # ── Parser ────────────────────────────────────────────────────────────────

    def _parse_hit(self, hit: dict, idx) -> dict:
        raw_keywords = hit.get("keywords") or []
        author_keywords_str = "; ".join(k["display_name"] for k in raw_keywords)

        raw_concepts = hit.get("concepts") or []
        filtered = [
            c["display_name"] for c in raw_concepts
            if c["level"] >= self.concept_min_level and c["score"] >= self.concept_min_score
        ]
        if not filtered and raw_concepts:
            filtered = [c["display_name"] for c in raw_concepts if c["level"] >= 1][:3]

        return {
            "original_index": idx,
            "oa_id":           hit.get("id"),
            "author_keywords": author_keywords_str,
            "ai_concepts":     "; ".join(filtered),
            "abstract":        self._reconstruct_abstract(hit.get("abstract_inverted_index")),
        }

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict) -> str:
        if not inverted_index:
            return ""
        word_positions = [
            (pos, word)
            for word, positions in inverted_index.items()
            for pos in positions
        ]
        word_positions.sort()
        return " ".join(word for _, word in word_positions)

    @staticmethod
    def _empty_result(idx) -> dict:
        return {"original_index": idx, "oa_id": "ERROR",
                "author_keywords": "", "ai_concepts": "", "abstract": ""}
