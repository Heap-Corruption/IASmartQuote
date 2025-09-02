import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from find import scrape_products
from sendMailer import sendEmail


# Configuração do servidor IA

API_ROUTES = {
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products?name=",
    "login": "https://smart-quote-back.onrender.com/v1/api/users/login",
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products",
    "getQuote": "https://smart-quote-back.onrender.com/v1/api/quotes",
    "getTips": "https://smart-quote-back.onrender.com/v1/api/tips",
    "getquoteItems": "https://smart-quote-back.onrender.com/v1/api/quote-items"
}



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


def parse_price(price_str):
    # Pega apenas números, vírgula e ponto
    clean = re.sub(r"[^\d.,]", "", price_str)
    # Trocar vírgula por ponto se necessário
    clean = clean.replace(",", ".")
    return float(clean)


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

def make_quote(payload, remetente, remetente_email, data_pedido_iso, assunto_raw, body):
    load_dotenv()
    try:
                response = requests.post(os.getenv("API_FLASK"), json=payload)
                if response.ok:
                    ia_response = response.json()
                    if isinstance(ia_response, list):
                        for item in ia_response:
                            item["clientName"] = getName(remetente)
                            item["clientEmail"] = remetente_email
                            item["sentAt"] = data_pedido_iso
                    print("\n\n✅ Resposta da IA:", ia_response)

                    # Access Datas
                    token = requests.post(API_ROUTES["login"], json=json.loads(os.getenv("LOGIN")))
                    if (token.ok is False):
                        raise Exception("Não foi possível autenticar na API.")
                    token = token.json()
                    quote = {
                        "userId": token["data"]["id"],
                        "quoteNumber": "003",
                        "clientName": ia_response[0].get("clientName", ""),
                        "clientEmail": ia_response[0].get("clientEmail", ""),
                        "clientPhone": ia_response[0].get("clientPhone", ""),
                        "destination": ia_response[0].get("destination", ""),
                        "dueDate": ia_response[0].get("dueDate", ""),
                        "subject": assunto_raw,
                        "body": body,
                        "requirements": {"data": [{"product": item["product"], "quantity": item["quantity"]} for item in ia_response]},
                        "metadata": {"source": "email", "priority": "high"},
                        "sentAt": ia_response[0].get("sentAt", "")
                    }
                    if (token["status"] != "success"):
                        raise Exception("Não foi possível autenticar na API.")
                    header = {"Authorization": f"Bearer {token['token']}", "Content-Type": "application/json"}
                    quoteId = requests.post(API_ROUTES["getQuote"], json=quote, headers=header)
                    if (quoteId.ok is False):
                        raise Exception("Error to create quote: " + quoteId.text)
                    quoteId = quoteId.json()["data"]
                    bdProducts = requests.get(API_ROUTES["getProducts"], headers=header)
                    if (bdProducts.ok is False):
                        raise Exception("GetProducts error :" + bdProducts.text)
                    bdProducts = bdProducts.json()["data"]
                    notfoundList = requests.get(API_ROUTES["getTips"], headers=header)
                    if (notfoundList.ok):
                        notfoundList = notfoundList.json()["data"]
                    else:
                        raise Exception("GetTips error :" + notfoundList.text)
                    
                    for item in ia_response:
                        bdProduct = find_product(bdProducts, item["product"], "name")
                        if (bdProduct):
                            print(f"\n\nProduto encontrado: {bdProduct}\n\n")
                            quoteItem = {"quoteId": quoteId, "productId": bdProduct["id"], "quantity": item["quantity"], "description": bdProduct["description"], \
                                "unitPrice": bdProduct["unitPrice"], "notes": "",\
                                "totalPrice": (float)(bdProduct["unitPrice"]) * (float)(item["quantity"]) + bdProduct.get("tax", 0), "tax": bdProduct.get("tax", 0)}
                            quoteItem = requests.post(API_ROUTES["getquoteItems"], json=quoteItem, headers=header)
                            if (quoteItem.ok is False):
                                raise Exception("SetItems error :" + quoteItem.text)
                            quoteItem = quoteItem.json()
                            print(f"\n\n✅Item de cotação criado: {quoteItem}\n\n")
                        else:
                            notItem = find_product(notfoundList, item["product"], "product")
                            if (notItem is None):
                                print("\n\nIndo para web")
                                scrapResult = scrape_products(item)[:3]
                                for iter in scrapResult:
                                    data = {
                                        "quoteId": quoteId,
                                        "product": iter.get("name", ""),
                                        "price": parse_price(iter.get("price", "0")),
                                        "imageUrl": iter.get("image_url", ""),
                                        "description": iter.get("description", ""),
                                        "site": (json.loads(os.getenv("WEBSITE", "[]")) or [""])[0],
                                        "link": iter.get("product_url", "")
                                    }
                                    data = requests.post(API_ROUTES["getTips"], json=data, headers=header)
                                    if (data.ok is False):
                                        raise Exception("SetTips error :" + data.text)
                                print(f"\n\n✅Scrape result: {scrapResult}\n\n")
                                sendEmail("angeloquissanga55@gmail.com", "SmartQuote: Sugestões de produtos não encontrados", os.getenv("MAILBODY"), is_html=True)
                                # print("Falta alertar o adm sobre possiveis sugestões de produtos.")
                else:
                    raise Exception("Erro da IA: " + response.text)

    except Exception as e:
        print(str(e))
        return 1
    return 0