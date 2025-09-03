from pydoc import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os


load_dotenv()

# ...existing code...

def sendEmail(to_email, subject, message, is_html=False):
    load_dotenv()
    from_email = os.getenv("MAILUSER")
    password = os.getenv("MAILPASSWORD")

    if not from_email or not password:
        raise ValueError("Credenciais de email não configuradas.")

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "html" if is_html else "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()

        print("✅ Email enviado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
    return 0

# if __name__ == "__main__":
#     mailbody = os.getenv("MAILBODY")
#     if mailbody is None:
#         mailbody = "Corpo do email não definido."
#     sendEmail("angeloquissanga55@gmail.com", "SmartQuote: Sugestões de produtos não encontrados", mailbody, is_html=True)