import html

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


