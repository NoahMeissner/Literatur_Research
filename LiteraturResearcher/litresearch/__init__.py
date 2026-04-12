# src/__init__.py
# Lazy imports — each submodule is only loaded when explicitly accessed.
# This avoids crashing if optional dependencies (e.g. langchain, PyMuPDF)
# are not installed in the current environment.


def __getattr__(name):
    """Lazy-load top-level convenience imports."""
    _LAZY = {
        "clean_html_entities":        (".utils.clean",              "clean_html_entities"),
        "detect_german_titles":       (".utils.detect_lang",        "detect_german_titles"),
        "safe_detect":                (".utils.detect_lang",        "safe_detect"),
        "DBLPConferenceExtractor":    (".extractors.DBLP_Extractor","DBLPConferenceExtractor"),
        "OpenAlexFetcher":            (".api_clients.request_openAlex", "OpenAlexFetcher"),
        "PDFExtractor":               (".extractors.pdf_extractor", "PDFExtractor"),
        "IOSPressDownloader":         (".extractors.iospress_extractor", "IOSPressDownloader"),
    }

    if name in _LAZY:
        module_path, attr = _LAZY[name]
        import importlib
        mod = importlib.import_module(module_path, package=__name__)
        return getattr(mod, attr)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "clean_html_entities",
    "detect_german_titles",
    "DBLPConferenceExtractor",
    "OpenAlexFetcher",
    "safe_detect",
    "PDFExtractor",
    "IOSPressDownloader",
]
