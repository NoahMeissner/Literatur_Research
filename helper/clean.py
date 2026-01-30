import html
from langdetect import detect, LangDetectException

def clean_html_entities(df):
    """
    Decode HTML entities in text columns.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with text columns containing HTML entities
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with decoded text
    """
    df_cleaned = df.copy()
    
    text_columns = ['title', 'authors']
    
    for col in text_columns:
        if col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].apply(
                lambda x: html.unescape(x) if isinstance(x, str) else x
            )
    
    return df_cleaned


def detect_german_titles(df, conference: str = "KI"):
    """
    Detect German titles using langdetect.
    """
    def safe_detect(text):
        try:
            if isinstance(text, str) and len(text.strip()) > 0:
                return detect(text)
            return None
        except LangDetectException:
            return None
    ki_mask = df['conference'] == 'KI'
    df.loc[ki_mask, 'detected_lang'] = df.loc[ki_mask, 'title'].apply(safe_detect)
    ki_mask = df['conference'] == conference
    german_count = (df['detected_lang'] == 'de').sum()
    print(f"Found German titles: {german_count}")
    
    return df

