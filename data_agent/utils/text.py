def normalize_text_filter(value: str | None) -> str | None:
    text = value.strip() if isinstance(value, str) else ""
    return text or None
