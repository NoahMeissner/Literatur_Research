import requests
import pandas as pd
import time
from typing import List, Dict, Optional
from datetime import datetime


class DBLPConferenceExtractor:
    def __init__(self, base_url: str = "https://dblp.org/search/publ/api", log_file: Optional[str] = None):
        self.base_url = base_url
        self.hits_per_page = 1000
        self.log_file = log_file
        
        if self.log_file:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"DBLP Extraction Log - Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")
    
    def _log(self, message: str, console: bool = True):
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        if console:
            print(message)
    
    def fetch_conference_papers(
        self, 
        conference_query: str,
        venue_filter: Optional[List[str]] = None,
        venue_filter_mode: str = "contains",
        year_start: int = 1985, 
        year_end: int = 2025,
        max_results: Optional[int] = None,
        verbose: bool = False,
        console_output: bool = False  # NEU: Console-Ausgabe an/aus
    ) -> List[Dict]:
        
        all_papers = []
        
        if verbose:
            self._log(f"\n{'='*70}", console_output)
            self._log(f"Fetching: {conference_query}", console_output)
            self._log(f"Venue filter: {venue_filter} (mode: {venue_filter_mode})", console_output)
            self._log(f"{'='*70}", console_output)
        
        total_hits = self._get_total_count(conference_query, verbose, console_output)
        if total_hits == 0:
            if verbose:
                self._log("⚠️  No results found - check query and venue filter!", console_output)
            return []
        
        if max_results:
            total_hits = min(total_hits, max_results)
        
        num_requests = (total_hits // self.hits_per_page) + 1
        
        if verbose:
            self._log(f"  Fetching in {num_requests} requests...\n", console_output)
        
        for page in range(num_requests):
            first_result = page * self.hits_per_page
            
            params = {
                'q': conference_query,
                'h': self.hits_per_page,
                'f': first_result,
                'format': 'json'
            }
            
            if verbose:
                msg = f"Request {page+1}/{num_requests}: results {first_result}-{first_result + self.hits_per_page}..."
                if console_output:
                    print(msg, end="")
                
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                hits = data.get('result', {}).get('hits', {}).get('hit', [])
                
                if not hits:
                    if verbose:
                        self._log(f" No more results", console_output)
                    break
                
                page_papers = self._process_hits(
                    hits, 
                    year_start, 
                    year_end, 
                    venue_filter,
                    venue_filter_mode
                )
                
                all_papers.extend(page_papers)
                
                if verbose:
                    result_msg = f" ✓ {len(page_papers)} papers (Total: {len(all_papers)})"
                    if console_output:
                        print(result_msg)
                    else:
                        self._log(msg + result_msg, False)
                
                time.sleep(1)
                
            except Exception as e:
                if verbose:
                    error_msg = f" ✗ Error: {e}"
                    if console_output:
                        print(error_msg)
                    else:
                        self._log(msg + error_msg, False)
                continue
        
        if verbose:
            self._log(f"\n{'='*70}", console_output)
            self._log(f"✓ Total papers found: {len(all_papers)}", console_output)
            self._log(f"{'='*70}\n", console_output)
        
        return all_papers
    
    def _get_total_count(self, query: str, verbose: bool, console_output: bool) -> int:
        params = {'q': query, 'h': 1, 'format': 'json'}
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            total_hits = int(data['result']['hits']['@total'])
            
            if verbose:
                self._log(f"Total hits in DBLP: {total_hits}", console_output)
            
            return total_hits
            
        except Exception as e:
            if verbose:
                self._log(f"✗ Error getting total count: {e}", console_output)
            return 0
    
    def _process_hits(
        self, 
        hits: List[Dict], 
        year_start: int, 
        year_end: int,
        venue_filter: Optional[List[str]],
        venue_filter_mode: str = "contains"
    ) -> List[Dict]:
        
        papers = []
        
        for hit in hits:
            info = hit.get('info', {})
            
            year = self._extract_year(info)
            if not year or year < year_start or year > year_end:
                continue
            
            venue = self._extract_venue(info)
            
            if venue_filter:
                venue_lower = venue.lower().strip()
                
                if venue_filter_mode == "exact":
                    if not any(venue_lower == vf.lower().strip() for vf in venue_filter):
                        continue
                else:
                    if not any(vf.lower() in venue_lower for vf in venue_filter):
                        continue
            
            paper = {
                'title': info.get('title', ''),
                'year': year,
                'authors': self._extract_authors(info),
                'doi': self._extract_field(info, 'doi'),
                'url': self._extract_field(info, 'url'),
                'ee': self._extract_field(info, 'ee'),
                'venue': venue,
                'pages': str(info.get('pages', '')),
                'type': str(info.get('type', ''))
            }
            
            papers.append(paper)
        
        return papers
    
    def _extract_year(self, info: Dict) -> Optional[int]:
        year = info.get('year')
        if year:
            try:
                return int(year)
            except:
                pass
        return None
    
    def _extract_authors(self, info: Dict) -> str:
        authors_data = info.get('authors')
        
        if not authors_data:
            return ''
        
        author_list = authors_data.get('author', [])
        
        if not isinstance(author_list, list):
            author_list = [author_list]
        
        author_names = []
        for author in author_list:
            if isinstance(author, dict):
                name = author.get('text', '') or author.get('@pid', '')
                if name:
                    author_names.append(name)
            elif isinstance(author, str):
                author_names.append(author)
        
        return '; '.join(author_names)
    
    def _extract_venue(self, info: Dict) -> str:
        venue_raw = info.get('venue', '')
        
        if isinstance(venue_raw, list):
            return ' '.join([str(v) for v in venue_raw])
        elif isinstance(venue_raw, dict):
            return venue_raw.get('text', '')
        else:
            return str(venue_raw)
    
    def _extract_field(self, info: Dict, field: str) -> str:
        value = info.get(field, '')
        
        if isinstance(value, dict):
            return value.get('text', '')
        elif isinstance(value, list):
            value = value[0] if value else ''
            if isinstance(value, dict):
                return value.get('text', '')
            return str(value)
        else:
            return str(value)
