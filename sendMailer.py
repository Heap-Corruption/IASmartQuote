from pydoc import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

from utils import getEnv

# ...existing code...

def sendEmail(to_email, subject, message, is_html=False):
    load_dotenv()
    AUTHOMATIONBOX = getEnv("AUTHOMATIONBOX", "json")
    from_email = AUTHOMATIONBOX.get("email", "")
    password = AUTHOMATIONBOX.get("password", "")

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

        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
    return 0

# if __name__ == "__main__":
#     mailbody = os.getenv("MAILBODY")
#     if mailbody is None:
#         mailbody = "Corpo do email não definido."
#     sendEmail("angeloquissanga55@gmail.com", "SmartQuote: Sugestões de produtos não encontrados", mailbody, is_html=True)