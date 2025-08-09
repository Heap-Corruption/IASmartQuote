from flask import Flask, request, jsonify
import google.generativeai as genai
import os
import re
import json

API_KEY = "AIzaSyDMzV4fOLS3_IcCPUjlkokMm8xbO6awGbg"
PORTA = 5000

INSTRUCAO_DE_SISTEMA = """
Você é um assistente de compras. Sua tarefa é ler um texto de cotação e extrair os dados solicitados.
Para cada produto mencionado, você deve criar um objeto JSON com os seguintes campos:

- cliente: Nome do cliente
- email: E-mail do cliente
- telefone: Número de telefone
- produto: Nome do produto
- quantidade: Quantidade
- local: Local completo de entrega
- data_entrega: Data de entrega no formato YYYY-MM-DD (se houver)
- data_pedido: Data e hora que o e-mail foi enviado no formato ISO 8601

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

    if not pergunta:
        return jsonify({'erro': 'Pergunta não fornecida'}), 400

    try:
        resposta = model.generate_content(
            f"{INSTRUCAO_DE_SISTEMA}\n\nTexto da cotação:\n{pergunta}"
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
