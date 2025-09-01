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
    "login": "https://smart-quote-back.onrender.com/v1/api/users/login",
    "getProducts": "https://smart-quote-back.onrender.com/v1/api/products",
    "getQuote": "https://smart-quote-back.onrender.com/v1/api/quotes",
    "getTips": "https://smart-quote-back.onrender.com/v1/api/tips",
    "getquoteItems": "https://smart-quote-back.onrender.com/v1/api/quotes/quote-items"
}
# API_SECUNDARIA = "http://127.0.0.1:8000/v1/api/quotes"

# Intervalo entre verificações (em segundos)
INTERVALO_VERIFICACAO = 1


# QUota todos os produtos

def find_product(products, name_to_check):
    for p in products:
        if p.get("name", "").lower() == name_to_check.lower():
            return p
    return None



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
        mail = imaplib.IMAP4_SSL(os.getenv("SERVIDOR_IMAP"))
        mail.login(os.getenv("MAILUSER"), os.getenv("MAILPASSWORD"))
        mail.select("inbox")

        status, mensagens = mail.search(None, 'UNSEEN')
        for num in mensagens[0].split():
            status, dados = mail.fetch(num, "(RFC822)")
            mensagem = email.message_from_bytes(dados[0][1])

            # Decodificar assunto
            assunto_raw = mensagem["Subject"]
            assunto_decodificado, encoding = decode_header(assunto_raw)[0]
            if isinstance(assunto_decodificado, bytes):
                assunto = assunto_decodificado.decode(encoding or "utf-8")
            else:
                assunto = assunto_decodificado

            remetente = mensagem.get("From")
            data_email = mensagem["Date"]

            print(f"Novo e-mail de: {remetente} | Assunto: {assunto}")

            corpo = ""
            if mensagem.is_multipart():
                for parte in mensagem.walk():
                    content_type = parte.get_content_type()
                    content_disposition = str(parte.get("Content-Disposition"))

                    # Texto simples
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = parte.get_content_charset() or "utf-8"
                        corpo += parte.get_payload(decode=True).decode(charset, errors="ignore")

                    # PDF anexo
                    if "application/pdf" in content_type:
                        nome_arquivo = parte.get_filename()
                        if nome_arquivo:
                            print(f"📎 Anexo encontrado: {nome_arquivo}")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                                temp_pdf.write(parte.get_payload(decode=True))
                                temp_pdf_path = temp_pdf.name
                            with pdfplumber.open(temp_pdf_path) as pdf:
                                texto_pdf = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
                                corpo += "\n" + texto_pdf
                            os.unlink(temp_pdf_path)
            else:
                charset = mensagem.get_content_charset() or "utf-8"
                corpo = mensagem.get_payload(decode=True).decode(charset, errors="ignore")

            print("Texto extraído:")
            print(corpo)

            # Metadados
            try:
                data_pedido_iso = datetime.strptime(data_email, "%a, %d %b %Y %H:%M:%S %z").isoformat()
            except:
                data_pedido_iso = datetime.utcnow().isoformat()

            remetente_email = remetente.split("<")[-1].replace(">", "").strip()
            cliente_nome = remetente.split("<")[0].strip().replace('"', '')

            payload = {
                "pergunta": corpo,
                "cliente": cliente_nome,
                "email": remetente_email,
                "data_pedido": data_pedido_iso
            }
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
                    token = requests.post(API_ROUTES["login"], json=json.loads(os.getenv("LOGIN")))
                    if (token.ok is False):
                        raise Exception("Não foi possível autenticar na API.")
                    token = token.json()
                    quote = {
                        "userId": token["data"]["id"],
                        "clientName": ia_response[0].get("clientName", ""),
                        "clientEmail": ia_response[0].get("clientEmail", ""),
                        "clientPhone": ia_response[0].get("clientPhone", ""),
                        "destination": ia_response[0].get("destination", ""),
                        "dueDate": ia_response[0].get("dueDate", ""),
                        "subject": assunto_raw,
                        "requirements": {"data": [{"product": item["product"], "quantity": item["quantity"]} for item in ia_response]},
                        "metadata": assunto_raw,
                        "sentAt": ia_response[0].get("sentAt", "")
                    }
                    print("\n\nQuote to send:", quote)
                    if (token["status"] != "success"):
                        raise Exception("Não foi possível autenticar na API.")
                    header = {"Authorization": f"Bearer {token['token']}", "Content-Type": "application/json"}
                    quoteId = requests.post("https://smart-quote-back.onrender.com/v1/api/quotes", json=quote, headers=header)
                    if (quoteId.ok is False):
                        raise Exception(quoteId.text)
                    quoteId = quoteId.json()["data"]
                    notfound = requests.get("https://smart-quote-back.onrender.com/v1/api/tips", headers=header)
                    if (notfound.ok):
                        notfound = notfound.json()["data"]
                        for item in ia_response:
                            if (find_product(notfound, item["product"])):
                                print(f"\n\nNao ir para web")
                            else:
                                print("\n\nIr para web")
                    else:
                        raise Exception(notfound.text)
                    # if (qt.status_code == 200):
                    #     qt = qt.json()
                    #     print(f"\n\nQuote criado com sucesso: {qt}\n\n")
                    # else:
                    #     print("Erro ao criar quote:", qt.text)
                    # product_list = quote_products(ia_response, headers=header)
                    # print("\n\nLista de produtos:", product_list)
                else:
                    print("Erro da IA:", response.text)

            except Exception as e:
                print("There was an error:", str(e))

            # Marcar como lido
            mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()

    except Exception as e:
        print("Erro ao processar e-mails:", str(e))

if __name__ == "__main__":
    print(f"Monitor de e-mails iniciado! Checando a cada {INTERVALO_VERIFICACAO} segundos...")
    while True:
        processar_emails()
        time.sleep(INTERVALO_VERIFICACAO)