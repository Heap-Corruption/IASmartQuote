import json
import os
import re

def getName(rem):
    name = rem.split()
    if name:
        name.pop()
    return " ".join(name)


def parse_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    
    # Remove tudo que não for número, vírgula ou ponto
    clean = re.sub(r"[^\d.,]", "", price_str)

    # Caso não reste nada
    if not clean:
        return 0.0

    # Se tiver mais de um ponto, trata como separador de milhar
    if clean.count(".") > 1:
        parts = clean.split(".")
        clean = "".join(parts[:-1]) + "." + parts[-1]

    # Se tiver mais de uma vírgula, trata como separador de milhar
    if clean.count(",") > 1:
        parts = clean.split(",")
        clean = "".join(parts[:-1]) + "," + parts[-1]

    # Converte vírgula decimal para ponto
    if "," in clean and "." in clean:
        # Ex.: "1.234,56" -> "1234.56"
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "")
            clean = clean.replace(",", ".")
        else:
            clean = clean.replace(",", "")
    else:
        clean = clean.replace(",", ".")

    try:
        return float(clean)
    except ValueError:
        return 0.0
    

def find_product(products, name_to_check, field):
    for p in products:
        if p.get(field, "").lower() == name_to_check.lower():
            if (p["tax"] == None):
                p["tax"] = 0
            status = p.get("status", "unknown")
            if status == "unknown":
                return p
            if status != "active":
                pass
            return p
    return None

def getAdm(users):
    adms = []
    for user in users:
        if user.get("role") == "admin":
            adms.append(user)
    return adms

def getEnv(envName, typeEnv):
    from dotenv import load_dotenv
    load_dotenv()
    if typeEnv == "array":
        js = json.loads(os.getenv(envName, "[]")) or [""]
        if not js or not isinstance(js, list):
            raise Exception(f"Invalid environment variable {envName}. Expected a JSON array.")
    if (typeEnv == "string"):
        js = os.getenv(envName, "")
        if not js:
            raise Exception(f"Invalid environment variable {envName}. Expected a string.")
    if (typeEnv == "json"):
        js = json.loads(os.getenv(envName, "{}"))
        if not js or not isinstance(js, dict):
            raise Exception(f"Invalid environment variable {envName}. Expected a JSON object.")
    return js