import os
import time
import threading
import requests
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static")
)
CORS(app)

# --------------------------------------------------
# 1) CONFIGURACIÓN DE MISTRAL Y SEMÁFORO
# --------------------------------------------------

client = None

def get_mistral_client():
    global client
    if client is not None:
        return client
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        return None
    key = key.strip().strip('"').strip("'")
    try:
        from mistralai.client import Mistral
        client = Mistral(api_key=key)
        return client
    except Exception as e:
        print(f"Error inicializando Mistral client: {e}")
        raise RuntimeError("No se pudo inicializar el cliente Mistral; revisa los logs de Runtime.") from e

# Modelos disponibles en el plan de Mistral (con fallback automático)
AVAILABLE_MODELS = [
    os.getenv("MISTRAL_MODEL", "ministral-8b-latest"),
    "open-mistral-7b",
    "ministral-3b-latest"
]

# Cuántos threads pueden llamar a Mistral simultáneamente
MAX_CONCURRENT_MISTRAL = 3
mistral_semaphore = threading.Semaphore(MAX_CONCURRENT_MISTRAL)

# --------------------------------------------------
# 2) FUNCIÓN DE LLAMADA CON FALLBACK Y BACKOFF ANTE 429/403
# --------------------------------------------------

def _call_mistral_with_backoff(
    messages: list,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> str:
    mistral_client = get_mistral_client()
    if not mistral_client:
        raise RuntimeError("MISTRAL_API_KEY no está configurada en las variables de entorno.")

    last_error = None

    for model_name in AVAILABLE_MODELS:
        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                resp = mistral_client.chat.complete(
                    model=model_name,
                    messages=messages,
                )
                if resp and resp.choices:
                    return resp.choices[0].message.content

            except Exception as e:
                last_error = e
                status_code = getattr(e, "status_code", None)
                if hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code

                # Si el modelo no está disponible en este plan (403), probar el siguiente modelo
                if status_code == 403:
                    break

                # Si es rate limit (429), reintentar con backoff o pasar al siguiente modelo
                if status_code == 429:
                    if attempt < max_retries:
                        time.sleep(delay)
                        delay *= 1.5
                        continue
                    else:
                        break

                # Para cualquier otro error, probar el siguiente modelo de respaldo
                break

    raise RuntimeError(f"Error al llamar a Mistral: {str(last_error)}")


def generate_response(user_message: str) -> str:
    """
    Envuelve la llamada a Mistral dentro de un semáforo para limitar concurrencia,
    con fallback automático de modelos.
    """
    system_prompt = (
        "Detecta el idioma del mensaje del usuario y responde en ese mismo idioma. "
        "Responde de forma concisa haciendo énfasis en la contaminación digital "
        "y no excedas las 30 palabras."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    with mistral_semaphore:
        try:
            return _call_mistral_with_backoff(messages)

        except Exception as e:
            return f"[Lo siento, en este momento no puedo procesar tu solicitud: {str(e)}]"

# --------------------------------------------------
# 3) ENDPOINTS DE FLASK Y LÓGICA DE POLUCIÓN DIGITAL
# --------------------------------------------------

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        index_path = os.path.join(base_dir, 'templates', 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        return f"Error loading index: {str(e)}", 500

@app.route('/health')
def health():
    key_configured = bool(os.getenv("MISTRAL_API_KEY"))
    return jsonify({
        "status": "ok",
        "app": "botpollution",
        "mistral_key_configured": key_configured
    })

@app.route("/generate", methods=["POST"])
def generate():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.json
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        bot_response = generate_response(user_message)

        # Cálculo de contaminación digital
        pollution_per_char = 0.02  # gramos de CO₂ por carácter
        user_pollution = len(user_message) * pollution_per_char
        bot_pollution = len(bot_response) * pollution_per_char
        total_pollution = user_pollution + bot_pollution
        cigarettes = round(total_pollution)  # 1 cigarro ≈ 1g CO₂

        pollution_summary = f"{total_pollution:.2f}g CO₂ ≈ {cigarettes} cigarros"

        return jsonify({
            "response": bot_response,
            "pollution_summary": pollution_summary,
        })

    except Exception as e:
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, threaded=True)
