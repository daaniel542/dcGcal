"""
Text normalizer for dish name comparison.

Normalizes dish names by:
  - lowercasing
  - stripping whitespace
  - removing '||' suffixes (e.g. "Omelette || Fried Eggs")
  - removing punctuation
  - collapsing multiple spaces
"""

import re
import string


def normalize(text):
    """
    Normalize a dish name for fuzzy comparison.

    Args:
        text: Raw dish name string.

    Returns:
        Cleaned, lowercased string suitable for comparison.
    """
    if not text:
        return ""

    # Remove anything after '||' (secondary dish descriptions)
    text = text.split('||')[0]

    text = text.lower().strip()

    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


if __name__ == "__main__":
    tests = [
        "  Chicken Tikka Masala  ",
        "Build Your Own Omelette || Fried Eggs to Order",
        "Mac & Cheese",
        "ORANGE   CHICKEN",
        "Carnitas Tacos (GF)",
        "",
        None,
    ]
    for t in tests:
        print(f"{t!r:50s} -> {normalize(t)!r}")
