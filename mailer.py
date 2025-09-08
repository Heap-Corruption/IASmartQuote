import os
import time
import json
import email
import imaplib
import tempfile
import pdfplumber
from datetime import datetime
from dotenv import load_dotenv
from email.header import decode_header
from alerts import alertSupport
from makeQuote import make_quote
from email.parser import BytesParser
from email import policy
from utils import getEnv
from email.utils import parseaddr
from resent import get_email, forward_email, get_from_email
from sendMailer import sendEmail
from mailContent import SYSTEMDOWNBODY


# Configurações de e-mail
load_dotenv()

# Intervalo entre verificações (em segundos)
INTERVALO_VERIFICACAO = 1


def get_from_email(raw_email: bytes) -> str:
    # Faz o parse do raw email
    msg = BytesParser(policy=policy.default).parsebytes(raw_email)
    
    # Extrai o campo From
    name, addr = parseaddr(msg["From"])
    return addr

# Cota todos os produtos
def emailProcessing():
    try:
        res = 0
        mail = imaplib.IMAP4_SSL(getEnv("SERVIDOR_IMAP", "string"))
        AUTHOMATIONBOX = getEnv("AUTHOMATIONBOX", "json")
        mail.login(AUTHOMATIONBOX.get("email", ""), AUTHOMATIONBOX.get("password", ""))
        mail.select("inbox")
        status, mensagens = mail.search(None, 'UNSEEN')
        if status != "OK" or not mensagens[0]:
            mail.logout()
            return 2  # Nenhum email não lido encontrado
        for num in mensagens[0].split():
            status, dados = mail.fetch(num, "(RFC822)")
            mensagem = email.message_from_bytes(dados[0][1])
            # print(f"\n\n\n📧 New email from: {}")

            # Decodificar assunto
            subject_raw = mensagem["Subject"]
            encoding = decode_header(subject_raw)[0]

            remetente_raw = mensagem.get("From")
            remetente_decodificado, encoding = decode_header(remetente_raw)[0]
            if isinstance(remetente_decodificado, bytes):
                remetente = remetente_decodificado.decode(encoding or "utf-8")
            else:
                remetente = remetente_decodificado
            data_email = mensagem["Date"]

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
                            # print(f"📎 Anexo encontrado: {nome_arquivo}")
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

            print(f"\n✅ Email body: {body}")
            # Metadados
            try:
                sentAt = datetime.strptime(data_email, "%a, %d %b %Y %H:%M:%S %z").isoformat()
            except:
                sentAt = datetime.utcnow().isoformat()
            clientEmail = get_from_email(dados[0][1])
            clientName = mensagem.get("From")

            payload = {
                "pergunta": body,
                "cliente": clientName,
                "email": clientEmail,
                "data_pedido": sentAt
            }
            if ("cotação" in str(subject_raw).lower()) or ("orçamento" in str(subject_raw).lower()) or ("cotacao" in str(subject_raw).lower()) or ("orcamento" in str(subject_raw).lower()):
                res = make_quote(payload, remetente, clientEmail, sentAt, subject_raw, body)
            if (res == 0):
                mail.store(num, '+FLAGS', '\\Seen')
            else:
                mail.store(num, '-FLAGS', '\\Seen')
        mail.logout()
        # print(f"\n\n\nEmail client: {get_from_email(mensagens)}\n\n")
        return res
    except Exception as e:
        print("\n🛑 Error processing emails:", str(e))
        alertSupport("SmartQuote: problemas técnicos", str(e))
        return -1  # Indica erro grave

def run_service():
    state = "on"
    while True:
        res = emailProcessing()
        if (res == -1):
            state = "off"
            break
        if (res != 0):
            break
    return state
if __name__ == "__main__":
    IMAP_SERVER = "imap.gmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    load_dotenv()
    print(f"Main:Monitor de e-mails iniciado! Checando a cada {INTERVALO_VERIFICACAO} segundos...")
    quotebox = getEnv("QUOTEBOX", "json")
    authomationbox = getEnv("AUTHOMATIONBOX", "json")
    state = "on"
    while True:
        raw_email = get_email(IMAP_SERVER, quotebox.get("email"), quotebox.get("password"))
        # print(get_from_email(raw_email))
        if (raw_email):
            forward_email(SMTP_SERVER, quotebox.get("email"), quotebox.get("password"), raw_email, authomationbox.get("email"))
        if (state == "on"):
            state = run_service()
        if (state == "off" and raw_email):
            sendEmail(get_from_email(raw_email), "SmartQuote offline", SYSTEMDOWNBODY, is_html=True)
            print("✅ Client notification successful.")
        time.sleep(INTERVALO_VERIFICACAO)