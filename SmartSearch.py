import os
import json
import re
import requests
from dotenv import load_dotenv
from routes import API_ROUTES
from utils import getEnv


# product = {'clientEmail': 'angeloquissanga55@gmail.com', 'clientName': '', \
#      'clientPhone': '', 'destination': 'processador intel i7', 'dueDate': '', \
#         'product': 'Impressora HP DeskJet Inspiron', 'quantity': '1', 'sentAt': '2025-09-02T15:13:00', 'taxa': ''}

# products = """[
#         {
#             "id": "8e31cc13-23bf-4613-afa7-8761c152ccaa",
#             "name": "Notebook Dell Inspiron",
#             "description": "Notebook de 15 polegadas com processador Intel i7",
#             "supplierId": "2ea686ab-71b8-4cc8-bdfe-67b515ffbb5a",
#             "category": "Tecnologia",
#             "unitPrice": "0",
#             "unit": "pcs",
#             "isActive": true,
#             "tax": "0",
#             "createdAt": "2025-08-28T20:20:22.000Z",
#             "updatedAt": "2025-08-28T20:20:22.000Z"
#         },
#         {
#             "id": "f30571d3-60e9-4d7b-a6e0-128af72cacca",
#             "name": "Impressora HP DeskJet Inspiron",
#             "description": "Impressora multifuncional jato de tinta",
#             "supplierId": "2ea686ab-71b8-4cc8-bdfe-67b515ffbb5a",
#             "category": "Tecnologia",
#             "unitPrice": "0",
#             "unit": "pcs",
#             "isActive": true,
#             "tax": "0",
#             "createdAt": "2025-08-28T20:20:42.000Z",
#             "updatedAt": "2025-08-28T20:20:42.000Z"
#         },
#         {
#             "id": "02a4c9a3-e034-45c0-92a0-1742452c3679",
#             "name": "Lanborguiny",
#             "description": "Luxurious",
#             "supplierId": "2ea686ab-71b8-4cc8-bdfe-67b515ffbb5a",
#             "category": "Keyboard",
#             "unitPrice": "0",
#             "unit": "gaffas",
#             "isActive": true,
#             "tax": "0",
#             "createdAt": "2025-09-04T16:38:01.000Z",
#             "updatedAt": "2025-09-05T09:13:58.000Z"
#         }]"""

# Configuração do servidor IA

INSTRUCTION = """Voce agora é um analizador de produtos que identifica o produto que o cliente deseja comprar em uma lista de produtos e retorna o produto se tiver na lista do mesmo jeito que estiver na lista, sem nenhuma adulteracao. Se o produto nao estiver na lista
, retorne o produto a ser procurado do mesmo jeito que foi enviado.
    * Analise todos os factores principais (Nome, Descricao, Categoria, preco).
    * A resposta deve ser um único objeto JSON.
    * Vc so pode retornar o mesmo json do produto encontrado ou o json do produto a ser procurado.
    * Nao adicione comentarios ou explicacoes fora do JSON."""

def find_BD_Products(products, product):
    lists = []
    sp = [word.lower() for word in product.get("product", "").split()]
    for p in products:
        if (any(word in p.get("name", "").lower() for word in sp)):
            if (p["tax"] == None):
                p["tax"] = 0
            lists.append(p)
    return lists

def askIA(product, products):
    load_dotenv()
    payload = {
            "pergunta": f"""Busque o produto {product} nesta lista de produtos {products} e retorne o produto se encontrado. Se nao encontrar, retorne o produto a ser procurado.""",
            "instrucao": INSTRUCTION
        }
    response = requests.post(getEnv("API_FLASK", "string"), json=payload)
    if response.ok:
        response = response.json()
    else:
        raise Exception(f"IA error: {response.text}")
    if (isinstance(response, list) and len(response) > 0):
        if (response[0] == product):
            return None
        return response[0]
    else:
        raise Exception("Resposta inválida da IA ao detectar o produto.")

def smart_search(product, products):
    load_dotenv()
    resultado = None
    try:
        pd = find_BD_Products(products, product)
        loteSize = 10
        produtos_lista = pd
        for i in range(0, len(produtos_lista), loteSize):
            batch = produtos_lista[i:i+loteSize]
            resultado = askIA(product, batch)
            if resultado:
                break
        return resultado
    except Exception as e:
        raise Exception(e)

# if __name__ == "__main__":
#     print(smart_search(product, json.loads(products)))