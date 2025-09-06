from flask import json
import requests
import os
from dotenv import load_dotenv

from routes import API_ROUTES
from utils import getEnv

def postTo(data, url, headers):
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        response = response.json()
        if (response.get("status") != "success"):
            raise Exception(f"Post to {url} error :" + response.get("message", "Unknown error"))
        return response
    else:
        raise Exception(f"Post to {url} error :" + response.text)

def getFrom(url, headers):
    response = requests.get(url, headers=headers)
    if response.ok:
        response = response.json()
        if (response.get("status") != "success"):
            raise Exception(f"Get from {url} error :" + response.get("message", "Unknown error"))
        return response
    else:
        raise Exception(f"Get from {url} error :" + response.text)
    
def login ():
    load_dotenv()
    token = requests.post(API_ROUTES["login"], json=getEnv("LOGIN", "json"))
    if (token.ok is False):
        raise Exception("Não foi possível autenticar na API.")
    if (token.json()["status"] != "success"):
        raise Exception("Falha na autenticação.")
    headers = {"Authorization": f"Bearer {token.json()['token']}"}
    return headers