import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from find import scrape_products
from sendMailer import sendEmail
from alerts import alertAdmins, alertSupport
from utils import parse_price, getName, find_product
from doRequests import postTo, getFrom
from routes import API_ROUTES


# Configuração do servidor IA

def make_quote(payload, client, sentFrom, askDate, subject, body):
    load_dotenv()
    try:
        response = requests.post(os.getenv("API_FLASK"), json=payload)
        if response.ok:
            ia_response = response.json()
            if isinstance(ia_response, list):
                for item in ia_response:
                    item["clientName"] = getName(client)
                    item["clientEmail"] = sentFrom
                    item["sentAt"] = askDate
            print("✅ IA answered successfully")

            # Access Datas
            try:
                token = requests.post(API_ROUTES["login"], json=json.loads(os.getenv("LOGIN")))
                if (token.ok is False):
                    raise Exception(token)
                token = token.json()
                if (token["status"] != "success"):
                    raise Exception("Falha na autenticação.")
                print("✅ Login successfully")
                quote = {
                    "userId": token["data"]["id"],
                    "quoteNumber": "003",
                    "clientName": ia_response[0].get("clientName", ""),
                    "clientEmail": ia_response[0].get("clientEmail", ""),
                    "clientPhone": ia_response[0].get("clientPhone", ""),
                    "destination": ia_response[0].get("destination", ""),
                    "dueDate": ia_response[0].get("dueDate", ""),
                    "subject": subject,
                    "body": body,
                    "requirements": {"data": [{"product": item["product"], "quantity": item["quantity"]} for item in ia_response]},
                    "totalPrice": 0.0,
                    "sentAt": ia_response[0].get("sentAt", "")
                }
                header = {"Authorization": f"Bearer {token['token']}", "Content-Type": "application/json"}
                quoteId = postTo(quote, API_ROUTES["getQuote"], header)
                print("✅ Quote created successfully")

                quoteId = quoteId["data"]
                bdProducts = getFrom(API_ROUTES["getProducts"], header)
                print("✅ Products fetched successfully")
                bdProducts = bdProducts["products"]
                for item in ia_response:
                    # Buscar produto no BD
                    bdProduct = find_product(bdProducts, item["product"], "name")
                    if (bdProduct):
                        quoteItem = {"quoteId": quoteId, "productId": bdProduct["id"], "quantity": item["quantity"], "description": bdProduct["description"], \
                            "unitPrice": bdProduct["unitPrice"], "notes": "",\
                            "totalPrice": (float)(bdProduct["unitPrice"]) * (float)(item["quantity"]) + bdProduct.get("tax", 0), "tax": bdProduct.get("tax", 0)}
                        quoteItem = postTo(quoteItem, API_ROUTES["getquoteItems"], header)
                        print("✅ Quote item for product created successfully")
                    else:
                        notfoundList = getFrom(API_ROUTES["getTips"], header)
                        print("✅ Tips fetched successfully")
                        notfoundList = notfoundList["data"]
                        notItem = find_product(notfoundList, item["product"], "product")
                        if (notItem is None):
                            # Fazer scraping do produto
                            scrapResult = scrape_products(item)[:3]
                            print("✅ Scraping completed successfully")
                            if (len(scrapResult) == 0):
                                data = {
                                "quoteId": quoteId,
                                "product": item["product"],
                                "price": 0,
                                "imageUrl": "None",
                                "description": "None",
                                "site": (json.loads(os.getenv("WEBSITE", "[]")) or [""])[0],
                                "link": "None"
                            }
                                data = postTo(data, API_ROUTES["getTips"], header)
                                print("✅ Empty tips created successfully")
                                data = data["data"]
                                notFoundItem = {"quoteId": quoteId, "notFoundId": data, "quantity": 0, "description": "None", \
                                "unitPrice": 0,  "totalPrice": 0, "tax": 0}
                                data = postTo(notFoundItem, API_ROUTES["getquoteItemsNotFound"], header)
                                print("✅ Quote-item-not-found created successfully")
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
                                    print("✅ Tips created successfully")
                                # print("✅✅✅✅ Don't forget to alertAdmins")
                                alertAdmins(header, "SmartQuote: Sugestões de produtos não encontrados", os.getenv("MAILBODY"))
            except Exception as e:
                print("Internal API error: ", str(e))
                alertSupport(f"SmartQuote: Erro na API Interna", f"Acesso à API interna falhou: <strong>{str(e)}</strong><br> Tips: Verifique a sua chave da API, as credenciais de login e se o serviço está ativo.")
                return -1
        else:
            raise Exception(response.text)
    except Exception as e:
        print("IA error: ", str(e))
        alertSupport(f"SmartQuote: Erro na IA", f"Resposta inesperada da IA: <strong>{response.text}</strong><br> Tips: Verifique a sua chave da API Flask e se o serviço está ativo.")
        return -1
    return 0