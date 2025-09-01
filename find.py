import os
import json
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import requests

INSTRUCAO_DE_SISTEMA = """Voce agora pode me ajudar a encontrar no maximo 4 opcoes de produtos tendo em conta o melhor custo beneficio entre uma lista de produtos.
## Regras:
1. Considere o preco e a qualidade dos produtos.
2. Retorne apenas os 4 melhores produtos.
3. Apresente os resultados em formato JSON e somente JSON conforme a lista fornecida.
"""

# ==========================
# Classe personalizada de erro
# ==========================
class FirecrawlError(Exception):
    """Erro genérico do Firecrawl."""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code

# ==========================
# Função wrapper para tratar erros
# ==========================
def extract_with_handling(app, **kwargs):
    try:
        result = app.extract(**kwargs)

        if not result.success:
            raise FirecrawlError(result.error or "Erro desconhecido", code="extract_failed")

        return result

    except ValueError as ve:
        raise FirecrawlError("API Key inválida ou ausente", code="invalid_api_key") from ve
    except Exception as e:
        msg = str(e).lower()
        if "unauthorized" in msg or "api key" in msg:
            raise FirecrawlError("API Key inválida", code="invalid_api_key") from e
        elif "payment required" in msg or "credits" in msg:
            raise FirecrawlError("Créditos esgotados", code="no_credits") from e
        elif "not found" in msg or "could not fetch" in msg:
            raise FirecrawlError("Site não encontrado ou inacessível", code="site_not_found") from e
        else:
            raise FirecrawlError(f"Erro inesperado: {e}", code="unknown") from e

# ==========================
# Schema de produto
# ==========================
schema = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "string"},
                    "image_url": {"type": "string"},
                    "description": {"type": "string"},
                    "product_url": {"type": "string"},
                },
                "required": ["name", "price", "image_url", "description", "product_url"]
            }
        }
    },
    "required": ["products"]
}

# ==========================
# Função de scraping
# ==========================
def scrape_products(product_json: dict):
    load_dotenv()
    """
    Recebe um JSON com { "product": "...", "price": "...", "website": "...", "limit": N }
    Faz scraping e retorna lista de produtos encontrados.
    """
    app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

    search_term = product_json.get("product")
    website = product_json.get("website", "https://itec.co.ao/*")
    product_limit = product_json.get("limit", 5)

    try:
        scrape_result = extract_with_handling(
            app,
            urls=[website],
            prompt=f"Extract up to {product_limit} products that match '{search_term}' from this website.",
            schema=schema
        )

        products = scrape_result.data.get("products", [])[:product_limit]

        print(f"✅ Produtos extraídos:\n\n{products}\n\n")

        # Montar corpo para a API Flask
        BODY = f""" Ache esse produto: {json.dumps(product_json, ensure_ascii=False)} nessa lista de produtos: {json.dumps(products, ensure_ascii=False)}"""
        payload = {
            "pergunta": BODY,
            "instruction": INSTRUCAO_DE_SISTEMA
        }

        response = requests.post(os.getenv("API_FLASK"), json=payload)
        print(f"Resposta da IA:\n\n{response.json()}\n\n")

        # Salvar no arquivo
        with open("Result.json", "w", encoding="utf-8") as f:
            json.dump({"products": products}, f, indent=2, ensure_ascii=False)

        return products

    except FirecrawlError as fe:
        print(f"❌ Erro Firecrawl ({fe.code}): {fe}")
        return []

# ==========================
# Exemplo de uso
# ==========================
if __name__ == "__main__":
    produto = {
        "product": "HP PROBOOK",
        "price": "KZ 999900.99",
        "website": "https://itec.co.ao/*",
        "limit": 5
    }

    scrape_products(produto)
