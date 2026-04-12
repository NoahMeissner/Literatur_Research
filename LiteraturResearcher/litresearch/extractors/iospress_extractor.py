import requests
import re
from typing import Optional

class IOSPressDownloader:
    """
    Downloads PDFs from IOS Press publications given their URL.
    Instead of standard GET requests, IOS Press uses a POST request 
    to an internal endpoint with the publication ID.
    """
    
    DOWNLOAD_ENDPOINT = "https://ebooks.iospress.nl/Download/Pdf"
    
    def __init__(self, request_timeout: int = 30):
        self.request_timeout = request_timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://ebooks.iospress.nl/'
        }

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extracts the publication ID from an IOS Press URL."""
        # 1. Faster path: extract directly from /publication/12345
        match = re.search(r'/publication/(\d+)', url)
        if match:
            return match.group(1)
        
        # 2. Fallback: if it's a DOI link like /doi/10.3233/FAIA... we need to fetch the page
        # and look for the download form ID.
        try:
            r = requests.get(url, headers=self.headers, timeout=self.request_timeout)
            if r.status_code == 200:
                match = re.search(r'<input type=\"hidden\" name=\"id\" value=\"(\d+)\" />', r.text)
                if match:
                    return match.group(1)
        except:
            pass
            
        return None

    def download_pdf_bytes(self, url: str) -> Optional[bytes]:
        """
        Downloads a PDF from IOS Press and returns the raw bytes.
        Returns None if extraction fails.
        """
        pub_id = self._extract_id_from_url(url)
        if not pub_id:
            print(f"  ✗ Konnte keine Publikations-ID aus der URL extrahieren: {url}")
            return None

        try:
            resp = requests.post(
                self.DOWNLOAD_ENDPOINT,
                data={'id': pub_id},
                headers=self.headers,
                timeout=self.request_timeout
            )
            resp.raise_for_status()
            
            # Check if we actually got a PDF
            if 'application/pdf' not in resp.headers.get('Content-Type', '').lower():
                print(f"  ✗ Server hat kein PDF zurückgegeben für ID {pub_id}")
                return None
                
            return resp.content
        except Exception as e:
            print(f"  ✗ Download für IOS Press fehlgeschlagen: {e}")
            return None

    def save_pdf(self, url: str, output_path: str) -> bool:
        """
        Downloads the PDF from the given URL and saves it to output_path.
        Returns True if successful, False otherwise.
        """
        pdf_bytes = self.download_pdf_bytes(url)
        if pdf_bytes:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            return True
        return False
