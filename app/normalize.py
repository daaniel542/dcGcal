import re
import string

def normalize(text):
    """
    Normalize a dish name for comparison:
    - lowercase
    - strip leading/trailing whitespace
    - remove punctuation
    - collapse multiple spaces into one
    - strip the '|| ...' suffix pattern (e.g. "Build Your Own Omelette || Fried Eggs to Order")
    """
    # Remove anything after '||' (secondary dish descriptions)
    text = text.split('||')[0]

    text = text.lower().strip()

    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


if __name__ == "__main__":
    # Quick sanity tests
    tests = [
        "  Chicken Tikka Masala  ",
        "Build Your Own Omelette || Fried Eggs to Order",
        "Mac & Cheese",
        "ORANGE   CHICKEN",
        "Carnitas Tacos (GF)",
    ]
    for t in tests:
        print(f"{t!r:50s} -> {normalize(t)!r}")
