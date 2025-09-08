import imaplib
import os
import smtplib
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv
from email.parser import BytesParser
from email import policy

from utils import getEnv

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"


def get_email(imap_server, EMAIL, PASSWORD):
    """Busca o primeiro email NÃO lido em formato RFC822 (bytes) e marca como lido"""
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(EMAIL, PASSWORD)
    imap.select("INBOX")

    status, messages = imap.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        return None

    email_id = messages[0].split()[0]  # pega o primeiro não lido
    status, data = imap.fetch(email_id, "(RFC822)")
    if status != "OK":
        imap.logout()
        return None

    imap.store(email_id, '+FLAGS', '\\Seen')
    imap.logout()

    return data[0][1]  # conteúdo bruto


def decode_header_value(value):
    """Decodifica corretamente um header (ex: Subject, Date, Name)"""
    if not value:
        return ""
    decoded = decode_header(value)
    parts = []
    for part, encoding in decoded:
        if isinstance(part, bytes):
            part = part.decode(encoding or "utf-8", errors="ignore")
        parts.append(part)
    return "".join(parts).replace("\n", " ").replace("\r", " ").strip()


def get_address_header(value):
    """Decodifica corretamente nome + email"""
    if not value:
        return ""
    name, addr = parseaddr(value)
    name = decode_header_value(name)
    if name:
        return f"{name} <{addr}>"
    return addr


def forward_email(smtp_server, EMAIL, PASSWORD, raw_email_bytes, forward_to):
    """Reencaminha o email preservando corpo e anexos + cabeçalho Forwarded"""
    original = message_from_bytes(raw_email_bytes)

    # Cabeçalho "Forwarded message"
    header_text = (
        "---------- Forwarded message ---------\n"
        f"From: {get_from_email(raw_email_bytes)}\n"
        f"Date: {decode_header_value(original.get('Date'))}\n"
        f"Subject: {decode_header_value(original.get('Subject'))}\n"
        f"To: {get_address_header(original.get('To'))}\n\n"
    )

    fwd = EmailMessage()
    fwd["From"] = EMAIL
    fwd["To"] = forward_to
    fwd["Subject"] = "Fwd: " + decode_header_value(original.get("Subject"))

    plain_body = None
    html_body = None
    attachments = []

    if original.is_multipart():
        for part in original.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                filename = part.get_filename()
                if filename:
                    payload = part.get_payload(decode=True)
                    attachments.append((
                        payload,
                        part.get_content_maintype(),
                        part.get_content_subtype(),
                        decode_header_value(filename)
                    ))
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    plain_body = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
    else:
        payload = original.get_payload(decode=True)
        if payload:
            plain_body = payload.decode(original.get_content_charset() or "utf-8", errors="ignore")

    # Monta corpo final
    final_plain = (header_text + (plain_body or "")).strip()
    final_html = None
    if html_body:
        final_html = f"<pre>{header_text}</pre><br>" + html_body

    # Primeiro define o corpo
    if final_html:
        fwd.set_content(final_plain)  # corpo texto
        fwd.add_alternative(final_html, subtype="html")  # corpo html
    else:
        fwd.set_content(final_plain)

    # Só depois adiciona os anexos
    for payload, maintype, subtype, filename in attachments:
        fwd.add_attachment(payload, maintype=maintype, subtype=subtype, filename=filename)

    # Envia o email
    with smtplib.SMTP(smtp_server, 587) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(fwd)

    print("✅ Email reencaminhado com sucesso!")

def get_from_email(raw_email: bytes) -> str:
    # Faz o parse do raw email
    msg = BytesParser(policy=policy.default).parsebytes(raw_email)
    
    # Extrai o campo From
    name, addr = parseaddr(msg["From"])
    return addr



# if __name__ == "__main__":
#     load_dotenv()
#     access = getEnv("QUOTEBOX", "json")
#     EMAIL = access.get("email")
#     PASSWORD = access.get("password")
#     print(f"🔍 Waiting for new emails...")
#     while True:
#         raw_email = get_email(IMAP_SERVER, EMAIL, PASSWORD)
#         # print(get_from_email(raw_email))
#         if (raw_email):
#             forward_email(SMTP_SERVER, EMAIL, PASSWORD, raw_email, EMAIL)
