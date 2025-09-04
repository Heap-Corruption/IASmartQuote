from flask import Flask, request, jsonify
import google.generativeai as genai
import os, re, json
from multiprocessing import Process
from mailer import run_service

emailProcess = Process(target=run_service)
emailProcess.start()

API_KEY = "AIzaSyDMzV4fOLS3_IcCPUjlkokMm8xbO6awGbg"
PORTA = 5000

INSTRUCAO_DE_SISTEMA = """
Você é um assistente de compras. Sua tarefa é ler um texto de cotação e extrair os dados solicitados.
Para cada produto mencionado, você deve criar um objeto JSON com os seguintes campos:

- clientName: Nome do cliente
- clientEmail: E-mail do cliente
- clientPhone: Número de telefone
- product: Nome do produto
- quantity: Quantidade
- destination: Local completo de entrega
- dueDate: Data de entrega no formato YYYY-MM-DD (se houver)
- sentAt: Data e hora que o e-mail foi enviado no formato ISO 8601
- taxa: Taxa aplicada ao item (se houver)

Regras:
1. Sempre responda como **lista JSON** (`[ {...}, {...} ]`), mesmo que haja apenas um item.
2. Não adicione comentários ou explicações fora do JSON.
3. Se algum campo não for informado no texto, retorne-o como string vazia.
"""

app = Flask(__name__)
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(model_name="gemma-3-27b-it")

def string_para_json_seguro(texto):
    """Tenta limpar e converter uma string em JSON."""
    if not isinstance(texto, str):
        return None
    texto_limpo = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(texto_limpo)
    except json.JSONDecodeError:
        pass
    try:
        match = re.search(r'(\{.*\}|\[.*\])', texto_limpo, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except json.JSONDecodeError:
        pass
    return None

@app.route('/ia', methods=['POST'])
def responder():
    data = request.get_json()
    pergunta = data.get('pergunta', '')
    instrucao_extra = data.get('instrucao', '')

    if not pergunta:
        return jsonify({'erro': 'Pergunta não fornecida'}), 400

    # Usa a instrução recebida, senão a padrão
    instrucao = instrucao_extra if instrucao_extra else INSTRUCAO_DE_SISTEMA

    try:
        resposta = model.generate_content(
            f"{instrucao}\n\nTexto da cotação:\n{pergunta}"
        )
        texto = resposta.text.strip()
        dados = string_para_json_seguro(texto)

        # Garante que a resposta seja sempre lista
        if isinstance(dados, dict):
            dados = [dados]
        elif not isinstance(dados, list):
            return jsonify({'erro': 'Formato inválido retornado pela IA'}), 500

        return jsonify(dados)

    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Servidor de IA rodando na porta {PORTA}...")
    app.run(host='0.0.0.0', port=PORTA)
