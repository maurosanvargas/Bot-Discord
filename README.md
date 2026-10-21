# Bot TTS

Bot de Discord para reproducir voces de Fish Audio, combinando texto, voces y sonidos de forma dinámica.

## Características

- Soporte para voces de Fish Audio con marcadores tipo `!freezer` o `!dross`.
- **Conversación con IA en tiempo real:** Habla con ElXokas (`!xokas_ia`) con respuestas generadas por Google Gemini Flash y reproducidas en voz con su modelo clonado en Fish Audio.
- **Memoria por canal con detección de cotilleos:** La IA recuerda quién habla y qué dicen de otros miembros del canal para echárselo en cara.
- Mezcla de texto, sonidos MP3 y voces en una sola reproducción.
- Cola por servidor para gestionar varias peticiones.
- Auto-leave cuando el canal queda vacío.

## Requisitos

- Python 3.11+
- FFmpeg disponible en PATH
- Discord bot token activo
- Clave API de Fish Audio
- Clave API de Google Gemini (Google AI Studio)

## Instalación

1. Clona el repositorio.
2. Crea un entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Instala dependencias:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Crea tu archivo local de configuración a partir de `config.example.py`:
   ```bash
   copy config.example.py config.py
   ```
5. Define las credenciales en `config.py` o mediante variables de entorno:
   - `DISCORD_TOKEN`
   - `FISH_AUDIO_API_KEY`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL` (opcional, por defecto `gemini-flash-lite-latest`)
6. Inicia el bot:
   ```bash
   python bot.py
   ```

## Uso rápido

- `!join` para entrar al canal de voz.
- `!xokas_ia <pregunta>`: habla directamente con ElXokas de 2022.
- `!xokas_reset`: reinicia la memoria del Xokas en el canal actual.
- `!dross Hola, soy Dross.`
- `!freezer Que tal?`
- `!comandos` para ver la lista completa de voces y sonidos.

## Seguridad

No subas credenciales reales a GitHub. El repositorio incluye un `.gitignore` para excluir archivos sensibles como:

- `config.py`
- `temp/`
- `__pycache__/`
- variables de entorno

## Estructura principal

- `bot.py`: lógica principal del bot y comandos de Discord
- `ia_chat.py`: integración con Google Gemini, memoria rodante por canal y personalidad
- `config.example.py`: plantilla de configuración
- `fish_audio.py`: integración HTTP con Fish Audio
- `sonidos/`: sonidos permanentes del bot
- `temp/`: archivos temporales generados durante la ejecución

## Notas

Este proyecto utiliza FFmpeg para generar y reproducir audio. La configuración actual de desarrollo local utiliza rutas de Windows.

