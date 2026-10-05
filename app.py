import os
import time
import threading
import requests
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from mistralai import Mistral

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
    if key:
        client = Mistral(api_key=key)
        return client
    return None

# Modelos: el principal y uno de respaldo
PRIMARY_MODEL = "mistral-large-latest"
FALLBACK_MODEL = "mistral-medium"

# Cuántos threads pueden llamar a Mistral simultáneamente
MAX_CONCURRENT_MISTRAL = 3
mistral_semaphore = threading.Semaphore(MAX_CONCURRENT_MISTRAL)

# --------------------------------------------------
# 2) FUNCIÓN DE LLAMADA CON BACKOFF EXPONENCIAL ANTE 429
# --------------------------------------------------

def _call_mistral_with_backoff(
    model_name: str,
    messages: list,
    max_retries: int = 4,
    initial_delay: float = 1.0
) -> str:
    """
    Llama a Mistral con una lista de mensajes y, si recibe 429, reintenta con backoff exponencial.
    Devuelve la respuesta en texto o lanza excepción al agotar reintentos.
    """
    mistral_client = get_mistral_client()
    if not mistral_client:
        raise RuntimeError("MISTRAL_API_KEY no está configurada en las variables de entorno.")

    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            resp = mistral_client.chat.complete(
                model=model_name,
                messages=messages,
            )
            return resp.choices[0].message.content

        except Exception as e:
            status_code = None
            if hasattr(e, "response") and isinstance(e.response, requests.Response):
                status_code = e.response.status_code

            if status_code == 429:
                retry_after = None
                if e.response is not None:
                    retry_after = e.response.headers.get("Retry-After")

                wait_seconds = delay
                if retry_after:
                    try:
                        wait_seconds = max(delay, int(retry_after))
                    except ValueError:
                        pass

                if attempt < max_retries:
                    time.sleep(wait_seconds)
                    delay *= 2
                    continue
                else:
                    raise

            raise

    raise RuntimeError("No se obtuvo respuesta de Mistral tras reintentos.")


def generate_response(user_message: str) -> str:
    """
    Envuelve la llamada a Mistral dentro de un semáforo para limitar concurrencia,
    e implementa fallback al modelo “medium” si “large” sigue devolviendo 429.
    """
    # Definimos un sistema que detecta el idioma y aplica el resto de instrucciones:
    system_prompt = (
        "Detecta el idioma del mensaje del usuario y responde en ese mismo idioma. "
        "Responde de forma concisa haciendo énfasis en la contaminación digital "
        "y no excedas las 30 palabras."
    )

    # Preparamos la conversación como lista de mensajes:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    with mistral_semaphore:
        try:
            return _call_mistral_with_backoff(PRIMARY_MODEL, messages)

        except Exception as e:
            status_code = None
            if hasattr(e, "response") and isinstance(e.response, requests.Response):
                status_code = e.response.status_code

            if status_code == 429:
                try:
                    return _call_mistral_with_backoff(FALLBACK_MODEL, messages)
                except Exception:
                    return (
                        "[Lo siento, en este momento no puedo procesar tu solicitud. "
                        "Intenta nuevamente más tarde.]"
                    )

            return f"[Error al solicitar al modelo: {str(e)}]"

# --------------------------------------------------
# 3) ENDPOINTS DE FLASK Y LÓGICA DE POLUCIÓN DIGITAL
# --------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/generate", methods=["POST"])
def generate():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.json
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Llamada a Mistral (dentro del semáforo + reintentos)
        bot_response = generate_response(user_message)

        # Cálculo de “contaminación digital”
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
