def determine_mode(creative_ids: list[str]) -> str:
    """Choose the analysis mode for one to five distinct creative IDs."""
    if not 1 <= len(creative_ids) <= 5:
        raise ValueError("Informe de um a cinco IDs de criativos")

    if len(set(creative_ids)) != len(creative_ids):
        raise ValueError("Os IDs de criativos devem ser distintos")

    return "individual" if len(creative_ids) == 1 else "comparative"
