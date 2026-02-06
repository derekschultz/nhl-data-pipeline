"""Data cleaning functions for NHL data."""

import unicodedata


def normalize_player_name(name: str) -> str:
    """Normalize a player name by removing accents and standardizing format.

    Examples:
        >>> normalize_player_name("Léon Draisaitl")
        'Leon Draisaitl'
        >>> normalize_player_name("  Connor McDavid  ")
        'Connor McDavid'
    """
    # Strip whitespace
    name = name.strip()

    # Remove accents/diacritics
    nfkd = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not unicodedata.combining(c))

    # Collapse multiple spaces
    name = " ".join(name.split())

    return name
