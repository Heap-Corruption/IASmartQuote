from flask import Flask, request, jsonify
import google.generativeai as genai
import os


API_KEY = "AIzaSyDMzV4fOLS3_IcCPUjlkokMm8xbO6awGbg" 
PORTA = 5000 
INSTRUCAO_DE_SISTEMA = """
Você é um assistente de compras. Leia um texto de cotação e extraia os itens pedidos com:
- Nome do produto
- Quantidade
- Local completo de entrega
- Data de entrega (se houver)
:pino: Exemplo:
Texto:
"Olá, gostaria de solicitar uma cotação para os seguintes materiais de construção:
- 20 sacos de cimento para entrega em Luanda, Talatona, edifício ISPTEC até o dia 15 de agosto.
- 10 pacotes de massa para entrega em Benguela, bairro da Graça, no dia 17 de agosto.
- 30 varas de ferro de 12mm para entrega no Kilamba, em Luanda, no dia 20 de agosto."
Resposta esperada:
[
  {
    "produto": "cimento",
    "quantidade": 20,
    "local": "Luanda - Talatona - Edifício ISPTEC",
    "data_entrega": "2025-08-15"
  },
  {
    "produto": "massa",
    "quantidade": 10,
    "local": "Benguela - Bairro da Graça",
    "data_entrega": "2025-08-17"
  },
  {
    "produto": "ferro 12mm",
    "quantidade": 30,
    "local": "Luanda - Kilamba",
    "data_entrega": "2025-08-20"
  }
]

Responda sempre em formato JSON, independentemente da solicitação.
Não inclua nenhuma informação adicional fora do JSON. Seja objetivo.

"""
import re
import json

app = Flask(__name__)

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(
    model_name="gemma-3-27b-it",
    #system_instruction=INSTRUCAO_DE_SISTEMA
)


def string_para_json_seguro(texto):
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
        resposta = model.generate_content(INSTRUCAO_DE_SISTEMA + "agora responde este: " + pergunta)
        texto = resposta.text.strip()
        return jsonify(string_para_json_seguro(texto))
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    print(f"Servidor de IA rodando na porta {PORTA}...")
    app.run(host='0.0.0.0', port=PORTA)




# Install dependencias em um ambiente virtual e depois rode novamente
# clear; curl -X POST http://127.0.0.1:5000/ia   -H "Content-Type: application/json"   -d '{"pergunta": "quero dois sacos de cimento e dezessete sacos de arroz para entrega em luanda - viana-capalanga casa numero 168"}'