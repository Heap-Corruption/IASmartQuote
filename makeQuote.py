import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from find import scrape_products
from sendMailer import sendEmail


# Configuração do servidor IA

def getAdm(users):
    adms = []
    for user in users:
        if user.get("role") == "admin":
            adms.append(user)
    return adms

def alertAdmins(header, routeGetUsers):
    users = requests.get(routeGetUsers, headers=header)
    if (users.ok is False):
        raise Exception("Não foi possível obter os usuários.")
    users = getAdm(users.json()["data"])
    for user in users:
        sendEmail(user["email"], "SmartQuote: Sugestões de produtos não encontrados", os.getenv("MAILBODY"), is_html=True)
    return 0



API_ROUTES = {
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products?name=",
    "login": "https://smart-quote-back.onrender.com/v1/api/users/login",
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products",
    "getQuote": "https://smart-quote-back.onrender.com/v1/api/quotes",
    "getTips": "https://smart-quote-back.onrender.com/v1/api/tips",
    "getUsers": "https://smart-quote-back.onrender.com/v1/api/users",
    "getquoteItems": "https://smart-quote-back.onrender.com/v1/api/quote-items",
    "getquoteItemsNotFound": "https://smart-quote-back.onrender.com/v1/api/quote-items-not-found"
}



def postTo(data, url, headers):
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        return response.json()
    else:
        raise Exception(f"Post to {url} error :" + response.text)

def getFrom(url, headers):
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()
    else:
        raise Exception(f"Get from {url} error :" + response.text)

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
    clean = re.sub(r"[^\d.,]", "", price_str)
    clean = clean.replace(",", ".")
    if not clean:
        return 0.0
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
                    # print("\n\n✅ Resposta da IA:", ia_response)

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
                        # "metadata": {"source": "email", "priority": "high"},
                        "sentAt": ia_response[0].get("sentAt", "")
                    }
                    if (token["status"] != "success"):
                        raise Exception("Não foi possível autenticar na API.")
                    header = {"Authorization": f"Bearer {token['token']}", "Content-Type": "application/json"}
                    quoteId = requests.post(API_ROUTES["getQuote"], json=quote, headers=header)
                    if (quoteId.ok is False):
                        raise Exception("Error to create quote: " + quoteId.text)
                    quoteId = quoteId.json()["data"]
                    bdProducts = getFrom(API_ROUTES["getProducts"], header)
                    bdProducts = bdProducts["data"]
                    notfoundList = getFrom(API_ROUTES["getTips"], header)
                    notfoundList = notfoundList["data"]
                    for item in ia_response:
                        bdProduct = find_product(bdProducts, item["product"], "name")
                        if (bdProduct):
                            # print(f"\n\nProduto encontrado: {bdProduct}\n\n")
                            quoteItem = {"quoteId": quoteId, "productId": bdProduct["id"], "quantity": item["quantity"], "description": bdProduct["description"], \
                                "unitPrice": bdProduct["unitPrice"], "notes": "",\
                                "totalPrice": (float)(bdProduct["unitPrice"]) * (float)(item["quantity"]) + bdProduct.get("tax", 0), "tax": bdProduct.get("tax", 0)}
                            quoteItem = postTo(quoteItem, API_ROUTES["getquoteItems"], header)
                            # print(f"\n\n✅Item de cotação criado: {quoteItem}\n\n")
                        else:
                            notItem = find_product(notfoundList, item["product"], "product")
                            if (notItem is None):
                                # print("\n\nIndo para web")
                                scrapResult = scrape_products(item)[:3]
                                scrapResult = []
                                if (len(scrapResult) == 0):
                                    data = {
                                    "quoteId": quoteId,
                                    "product": "None",
                                    "price": 0,
                                    "imageUrl": "None",
                                    "description": "None",
                                    "site": (json.loads(os.getenv("WEBSITE", "[]")) or [""])[0],
                                    "link": "None"
                                }
                                    data = postTo(data, API_ROUTES["getTips"], header)
                                    data = data["data"]
                                    notFoundItem = {"quoteId": quoteId, "notFoundId": data, "quantity": 0, "description": "None", \
                                    "unitPrice": 0.01,  "totalPrice": 0.01, "tax": 0}
                                    data = postTo(notFoundItem, API_ROUTES["getquoteItemsNotFound"], header)
                                    # print(f"\n\n✅Tips NULL criada: {data}\n\n")
                                else:
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
                                        data = postTo(data, API_ROUTES["getTips"], header)
                                    # print(f"\n\n✅Scrape result: {scrapResult}\n\n")
                                    alertAdmins(header, API_ROUTES["getUsers"])
                else:
                    raise Exception("Erro da IA: " + response.text)

    except Exception as e:
        print(str(e))
        return 1
    return 0