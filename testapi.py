import os
import time
import json
import email
import imaplib
import requests
import tempfile
import pdfplumber
from datetime import datetime
from dotenv import load_dotenv
from email.header import decode_header

# Configurações de e-mail
load_dotenv()

# Configuração do servidor IA

API_ROUTES = {
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products?name=",
    "login": "https://smart-quote-back.onrender.com/v1/api/users/login"
}
# API_SECUNDARIA = "http://127.0.0.1:8000/v1/api/quotes"

# Intervalo entre verificações (em segundos)
INTERVALO_VERIFICACAO = 1


# QUota todos os produtos
def quote_products(ia_response, headers, idquote):
    product_list = []
    for item in ia_response:
        if (item["product"] is None):
            continue
        products = requests.get(API_ROUTES["getProducts"]+item["product"], headers=headers).json()["data"]
        print(products)
        if products:
            product_list.append(products[0].json())
        else:
            product_list.append({
                "productId": None,
                "quoteId": idquote,
                "name": item["product"],
                "quantity": item["quantity"],
                "unitPrice": 0,
                "taxa": 0,
                "notes": "",
                "description": "",
                "totalPrice": 0,
            })
    return product_list


def getName(rem):
    name = rem.split()
    if name:
        name.pop()
    return " ".join(name)

def processar_emails():
    try:
        token = requests.post(API_ROUTES["login"], json=json.loads(os.getenv("LOGIN")))
        if (token.status_code != 200):
            raise Exception("Não foi possível autenticar na API.")
        token = token.json()
        print(f"Token: {token}\n\n")
        if (token["status"] != "success"):
            raise Exception("Não foi possível autenticar na API.")
        header = {"Authorization": f"Bearer {token['token']}", "Content-Type": "application/json"}
        notfound = requests.get("https://smart-quote-back.onrender.com/v1/api/tips", headers=header)
        if (notfound.status_code == 200):
            notfound = notfound.json()
            print(f"\n\nNotFound response: {notfound}\n\n")
        # response = requests.post(os.getenv("API_FLASK"), json=payload)
        # if response.status_code == 200:
        #     ia_response = response.json()
        #     if isinstance(ia_response, list):
        #         for item in ia_response:
        #             item["clientName"] = getName(remetente)
        #             item["clientEmail"] = remetente_email
        #             item["sentAt"] = data_pedido_iso
        #     print("\n\n✅ Resposta da IA:", ia_response)
            # quote = {
            #     "userId": token["data"]["id"],
            #     "clientName": ia_response[0].get("clientName", ""),
            #     "clientEmail": ia_response[0].get("clientEmail", ""),
            #     "clientPhone": ia_response[0].get("clientPhone", ""),
            #     "destination": ia_response[0].get("destination", ""),
            #     "dueDate": ia_response[0].get("dueDate", ""),
            #     "subject": assunto_raw,
            #     "requirements": {"data": [{"product": item["product"], "quantity": item["quantity"]} for item in ia_response]},
            #     "metadata": assunto_raw,
            #     "sentAt": ia_response[0].get("sentAt", "")
            # }
            # print("Quote to send:", quote)
            # qt = requests.post("https://smart-quote-back.onrender.com/v1/api/quotes", json=quote, headers=header)
            # if (qt.status_code == 200):
            #     qt = qt.json()
            #     print(f"\n\nQuote criado com sucesso: {qt}\n\n")
            # else:
            #     print("Erro ao criar quote:", qt.text)
            # product_list = quote_products(ia_response, headers=header)
            # print("\n\nLista de produtos:", product_list)

    except Exception as e:
        print("There was an error:", str(e))

if __name__ == "__main__":
        processar_emails()
        time.sleep(INTERVALO_VERIFICACAO)