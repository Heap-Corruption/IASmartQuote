import re
import json

def extract_forward_header(body: str) -> dict:
    """
    Recebe o corpo do email (body) e retorna um JSON com os headers do forward
    """
    header_pattern = (
        r"-{5,}\s*Forwarded message\s*-{5,}\s*"   # aceita 5+ traços antes/depois
        r"From:\s*(?P<from>.+)\s*"
        r"Date:\s*(?P<date>.+)\s*"
        r"Subject:\s*(?P<subject>.*)\s*"
        r"To:\s*(?P<to>.+)\s*"
    )

    match = re.search(header_pattern, body, re.IGNORECASE)
    if not match:
        return {}

    result = {
        "from": match.group("from").strip(),
        "date": match.group("date").strip(),
        "subject": match.group("subject").strip(),
        "to": match.group("to").strip()
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


# 🔹 Exemplo de uso
body = """---------- Forwarded message ---------
From: Ângelo Quissanga <angeloquissanga55@gmail.com>
Date: Mon, 8 Sep 2025 12:57:03 +0100
Subject: Fwd:
To: Ângelo Quissanga <angeloquissanga55@gmail.com>

a
"""

if __name__ == "__main__":
    print(extract_forward_header(body))

