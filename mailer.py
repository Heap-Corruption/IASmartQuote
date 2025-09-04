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
from makeQuote import make_quote

# Configurações de e-mail
load_dotenv()

# Intervalo entre verificações (em segundos)
INTERVALO_VERIFICACAO = 1


# Cota todos os produtos
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

            body = ""
            if mensagem.is_multipart():
                for parte in mensagem.walk():
                    content_type = parte.get_content_type()
                    content_disposition = str(parte.get("Content-Disposition"))

                    # Texto simples
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = parte.get_content_charset() or "utf-8"
                        body += parte.get_payload(decode=True).decode(charset, errors="ignore")

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
                                body += "\n" + texto_pdf
                            os.unlink(temp_pdf_path)
            else:
                charset = mensagem.get_content_charset() or "utf-8"
                body = mensagem.get_payload(decode=True).decode(charset, errors="ignore")

            print("Texto extraído:")
            print(body)

            # Metadados
            try:
                data_pedido_iso = datetime.strptime(data_email, "%a, %d %b %Y %H:%M:%S %z").isoformat()
            except:
                data_pedido_iso = datetime.utcnow().isoformat()

            remetente_email = remetente.split("<")[-1].replace(">", "").strip()
            cliente_nome = remetente.split("<")[0].strip().replace('"', '')

            payload = {
                "pergunta": body,
                "cliente": cliente_nome,
                "email": remetente_email,
                "data_pedido": data_pedido_iso
            }

            res = make_quote(payload, remetente, remetente_email, data_pedido_iso, assunto_raw, body)
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
else:
    print(f"Monitor de e-mails iniciado! Checando a cada {INTERVALO_VERIFICACAO} segundos...")
