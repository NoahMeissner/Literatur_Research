import requests, time, csv, os
import pandas as pd
from tqdm import tqdm

class SemanticScholarFetcher:
    """
    Fetcht Keywords, Abstract und externe IDs (inkl. DOI falls vorhanden)
    von Semantic Scholar – kostenlos, kein Tagesbudget, keine DOI nötig.
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    FIELDS   = "paperId,externalIds,title,year,abstract,tldr,fieldsOfStudy,s2FieldsOfStudy"
    FIELDNAMES = ["original_index", "s2_id", "doi", "abstract", "fields_of_study", "tldr"]

    def __init__(self, api_key: str, output_file: str, request_delay: float = 1.05):
        self.api_key = api_key          # Kostenlos via semanticscholar.org/product/api
        self.output_file = output_file
        self.request_delay = request_delay

    def _headers(self):
        return {"x-api-key": self.api_key}

    def _fetch_single(self, title: str, year: int) -> "dict | None":
        """Sucht ein Paper per Titel + Jahr."""
        params = {
            "query": title,
            "fields": self.FIELDS,
            "year":   f"{year}-{year}",
            "limit":  1,
        }
        resp = requests.get(self.BASE_URL, params=params, headers=self._headers(), timeout=15)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            print(f"\n[429] Warte {retry_after}s...")
            time.sleep(retry_after)
            # Einmal wiederholen
            resp = requests.get(self.BASE_URL, params=params, headers=self._headers(), timeout=15)

        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return data[0] if data else None
        return None

    def fetch(self, df: pd.DataFrame) -> pd.DataFrame:
        # Resume-Support: bereits verarbeitete Indizes überspringen
        processed = set()
        if os.path.exists(self.output_file):
            try:
                ex = pd.read_csv(self.output_file)
                valid = ex[~ex["s2_id"].astype(str).str.startswith("NOT_FOUND")]
                processed = set(valid["original_index"].unique())
            except Exception:
                pass

        rows_todo = [(idx, row) for idx, row in df.iterrows() if idx not in processed]
        print(f"Verbleibend: {len(rows_todo)} | Geschätzte Zeit: ~{len(rows_todo)//3600 + 1}h")

        write_header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0
        with open(self.output_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            if write_header:
                writer.writeheader()

            for idx, row in tqdm(rows_todo):
                time.sleep(self.request_delay)  # 1 req/s Limit einhalten
                hit = self._fetch_single(str(row["title"]), int(row["year"]))

                if hit:
                    writer.writerow({
                        "original_index":  idx,
                        "s2_id":           hit.get("paperId", ""),
                        "doi":             hit.get("externalIds", {}).get("DOI", ""),
                        "abstract":        hit.get("abstract") or hit.get("tldr", {}).get("text", "") or "",
                        "fields_of_study": "; ".join(
                            f["category"] for f in hit.get("s2FieldsOfStudy", [])
                        ),
                        "tldr":            (hit.get("tldr") or {}).get("text", ""),
                    })
                else:
                    writer.writerow({
                        "original_index": idx, "s2_id": "NOT_FOUND",
                        "doi": "", "abstract": "", "fields_of_study": "", "tldr": ""
                    })
                f.flush()

        return pd.read_csv(self.output_file)
