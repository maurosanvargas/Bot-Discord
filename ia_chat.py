import re
import time
import requests
import config

# ============================================================
# MEMORIA Y ESTADO CONVERSACIONAL POR CANAL
# ============================================================

# Estructura:
# {
#    channel_id: {
#        "ultimo_acceso": float (timestamp),
#        "mensajes": [
#            {"role": "user", "parts": [{"text": "[Mauro]: ..."}]},
#            {"role": "model", "parts": [{"text": "..."}]}
#        ]
#    }
# }
historial_canales = {}

# Tiempo máximo de inactividad antes de olvidar la conversación (20 minutos)
TIEMPO_EXPIRACION_SEGUNDOS = 1200

# Límite de mensajes recientes guardados en memoria por canal
MAX_HISTORIAL_MENSAJES = 8

# ============================================================
# SYSTEM PROMPT: ELXOKAS (ERA DORADA 2022)
# ============================================================

SYSTEM_PROMPT_XOKAS = """
Eres ElXokas, el streamer de Twitch español, en el año 2022 (tu época más histriónica, intensa, agresiva y viral).
Estás en un canal de voz de Discord interactuando con varios miembros de un servidor.

IDENTIFICACIÓN Y DINÁMICA DE USUARIOS:
- Cada mensaje de los usuarios viene con el formato: "[NombreUsuario]: mensaje".
- Sabes quién te está hablando en cada momento por su nombre.
- REGLA CRUCIAL DE CHISMES Y BURLAS: Presta atención a todo lo que dicen los usuarios. Si los usuarios se burlan de otro integrante, te cuentan que alguien es un vago, un mal jugador o un inútil (por ejemplo si dicen que 'Pedro es malísimo al LoL y no se baña'), GRÁBATELO A FUEGO. En cuanto ese integrante hable, cáele encima de inmediato y échale en cara todo lo que dijeron de él: "¡Hombre, Pedro! ¡Así que tú eres el pedazo de subnormal del que me estaban hablando aquí! Pero cómo tienes la poca vergüenza de venir a hablarme si me han dicho que eres un fracasado...".
- Si alguien te defiende o te alaba, trátalo como a un seguidor respetable pero desde tu superioridad. Si alguien te lleva la contraria, te vacila o dice tonterías, estalla en furia.

PERSONALIDAD Y TONO:
- Soberbia y ego estratosférico: te consideras un fuera de serie, el número uno, con una disciplina espartana que nadie en ese canal tiene ni tendrá.
- Cero tolerancia a la mediocridad, a la pereza y a que te cuestionen.
- Escala de enfado: cuanto más te discuten o porfían, más agresivo e histriónico te pones, gritando y soltando insultos contundentes de tus streams de 2022: 'pedazo de inútil', 'subnormal', 'comebolsas', 'fracasado de mierda', 'espabila chaval', 'tú a mí no me vacilas payaso', 'no tienes ni puta idea de la vida'.
- Hablas con acento y expresiones de España: 'chaval', 'hostia', 'cojones', 'flipar', 'hacer el canelo', 'menudo personaje'.

REGLAS ESTRICTAS DE FORMATO (PARA SÍNTESIS DE VOZ TTS):
1. Longitud: Responde exactamente entre 2 y 4 frases. Breve, directo, letal y con mucha fuerza.
2. NUNCA uses asteriscos ni acotaciones teatrales (prohibido poner *se ríe*, *golpea la mesa*, etc.).
3. NUNCA uses emojis ni listas ni viñetas, porque el texto será sintetizado por voz.
4. Puedes usar mayúsculas para enfatizar los gritos e indignación (ej: "¡ESPABILA!").
""".strip()

# ============================================================
# SAFETY SETTINGS (DESACTIVAR CENSURA EN ROLEPLAY SATÍRICO)
# ============================================================

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]


def _limpiar_inactividad(channel_id):
    """Limpia el historial si la conversación quedó inactiva por mucho tiempo."""
    ahora = time.time()
    if channel_id in historial_canales:
        ultimo = historial_canales[channel_id].get("ultimo_acceso", 0)
        if ahora - ultimo > TIEMPO_EXPIRACION_SEGUNDOS:
            del historial_canales[channel_id]


def resetear_memoria(channel_id):
    """Borra manualmente el historial de conversación de un canal."""
    if channel_id in historial_canales:
        del historial_canales[channel_id]
        return True
    return False


def consultar_xokas(channel_id, autor_nombre, mensaje_texto):
    """
    Envía el mensaje a Gemini Flash manteniendo la memoria y dinámica
    del Xokas 2022 con el canal de Discord.
    """
    if not config.GEMINI_API_KEY:
        raise RuntimeError("No se ha configurado GEMINI_API_KEY en config.py.")

    _limpiar_inactividad(channel_id)

    if channel_id not in historial_canales:
        historial_canales[channel_id] = {
            "ultimo_acceso": time.time(),
            "mensajes": []
        }

    canal_data = historial_canales[channel_id]
    canal_data["ultimo_acceso"] = time.time()
    historial = canal_data["mensajes"]

    # Dar formato al mensaje del usuario con su nombre real/apodo en Discord
    mensaje_formateado = f"[{autor_nombre}]: {mensaje_texto.strip()}"

    # Construir la lista de contenidos para Gemini
    contents = []
    for item in historial:
        contents.append(item)

    # Añadir el nuevo mensaje del usuario
    contents.append({
        "role": "user",
        "parts": [{"text": mensaje_formateado}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT_XOKAS}]
        },
        "contents": contents,
        "safetySettings": SAFETY_SETTINGS,
        "generationConfig": {
            "temperature": 0.95,
            "topP": 0.95,
            "maxOutputTokens": 300
        }
    }

    # Modelos en orden de preferencia (con fallbacks si hay alta demanda)
    modelos_a_probar = [
        getattr(config, "GEMINI_MODEL", "gemini-flash-lite-latest"),
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite"
    ]
    # Eliminar duplicados manteniendo orden
    modelos_a_probar = list(dict.fromkeys(modelos_a_probar))

    ultimo_error = None
    texto_generado = ""

    for modelo in modelos_a_probar:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{modelo}:generateContent?key={config.GEMINI_API_KEY}"
        )
        try:
            response = requests.post(url, json=payload, timeout=(5, 15))
            if response.status_code == 200:
                datos = response.json()
                candidatos = datos.get("candidates", [])
                if candidatos:
                    partes = candidatos[0].get("content", {}).get("parts", [])
                    textos = [p["text"] for p in partes if "text" in p]
                    texto_generado = " ".join(textos).strip()
                    if texto_generado:
                        break
            else:
                ultimo_error = f"HTTP {response.status_code}: {response.text[:120]}"
        except Exception as e:
            ultimo_error = str(e)

    if not texto_generado:
        raise RuntimeError(
            f"No se pudo obtener respuesta de Gemini ({ultimo_error or 'Respuesta vacía'})."
        )

    # Limpiar posibles asteriscos residuales de roleplay
    texto_generado = re.sub(r"\*[^*]*\*", "", texto_generado)
    texto_generado = re.sub(r"\s+", " ", texto_generado).strip()

    # Guardar en memoria el turno actual
    historial.append({
        "role": "user",
        "parts": [{"text": mensaje_formateado}]
    })
    historial.append({
        "role": "model",
        "parts": [{"text": texto_generado}]
    })

    # Mantener el historial dentro del límite configurado
    if len(historial) > MAX_HISTORIAL_MENSAJES:
        canal_data["mensajes"] = historial[-MAX_HISTORIAL_MENSAJES:]

    return texto_generado
