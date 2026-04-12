from langdetect import detect, LangDetectException

def safe_detect(text):
    try:
        if isinstance(text, str) and len(text.strip()) > 0:
            return detect(text)
        return None
    except LangDetectException:
        return None

def detect_german_titles(df, conference: str = "KI"):
    """
    Detect German titles using langdetect.
    """
    
    ki_mask = df['conference'] == 'KI'
    df.loc[ki_mask, 'detected_lang'] = df.loc[ki_mask, 'title'].apply(safe_detect)
    ki_mask = df['conference'] == conference
    german_count = (df['detected_lang'] == 'de').sum()
    print(f"Found German titles: {german_count}")
    
    return df

