import os
import requests
from dotenv import load_dotenv
from routes import API_ROUTES
from sendMailer import sendEmail
from utils import getAdm






def alertAdmins(header, subject, msg):
    load_dotenv()
    users = requests.get(API_ROUTES["getUsers"], headers=header)
    if (users.ok is False):
        raise Exception("Não foi possível obter os usuários.")
    users = getAdm(users.json()["data"])
    for user in users:
        sendEmail(user["email"], subject, msg, is_html=True)
    # print("Alerta enviado para os administradores.")
    return 0

def alertSupport(subject, msg):
    load_dotenv()
    BODYALERT = f"<!DOCTYPE html><html lang='pt'><head><meta charset='UTF-8'><title>Alerta de Suporte</title></head><body style='font-family: Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 20px; background-color: #f9f9f9;'><table width='100%' border='0' cellspacing='0' cellpadding='0' style='max-width: 600px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><tr><td><h4>Olá, equipe de suporte,</h4><p>Foi registrado um <strong>novo alerta</strong> que requer sua atenção imediata.</p><p>Por favor, verifique os detalhes no sistema e tome as ações necessárias o quanto antes.</p><br><p> ERRO: {msg} </p><br><p>Atenciosamente,</p><p><b>Sistema de Monitoramento da RCS Angola</b></p></td></tr></table></body></html>"
    email = os.getenv("MAILSUPPORT")
    if email is None or email == "":
        return 0
    print("Alerta enviado para a equipe de suporte.")
    sendEmail(email, subject, BODYALERT, is_html=True)
    return 0