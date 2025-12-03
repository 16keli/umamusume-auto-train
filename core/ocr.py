import re

import easyocr
import numpy as np

reader = easyocr.Reader(["en"], gpu=True)


def extract_text(img_np: np.ndarray, allowlist: str | None = None) -> str:
    result = reader.readtext(img_np, allowlist=allowlist)
    texts = [text[1] for text in result]
    return " ".join(texts)


def extract_number(img_np: np.ndarray) -> int:
    result = reader.readtext(img_np, allowlist="0123456789")
    texts = [text[1] for text in result]
    joined_text = "".join(texts)

    digits = re.sub(r"[^\d]", "", joined_text)

    if digits:
        return int(digits)

    return -1
