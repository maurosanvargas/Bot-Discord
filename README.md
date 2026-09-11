# Bot TTS

Bot de Discord para reproducir voz con Loquendo y modelos de Fish Audio, combinando texto, voces y sonidos de forma dinámica.

## Características

- Generación de voz con Loquendo.
- Soporte para voces de Fish Audio con marcadores tipo `!freezer` o `!dross`.
- Mezcla de texto, sonidos MP3 y voces en una sola reproducción.
- Cola por servidor para gestionar varias peticiones.
- Auto-leave cuando el canal queda vacío.

## Requisitos

- Python 3.11+
- FFmpeg disponible en PATH
- Discord bot token activo
- Loquendo TTS 7 (para la ruta del generador de voz)
- Clave API de Fish Audio

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
5. Rellena los valores reales en `config.py` (`TOKEN`, `FISH_AUDIO_API_KEY`, rutas locales, etc.).
6. Inicia el bot:
   ```bash
   python bot.py
   ```

## Uso rápido

- `!join` para entrar al canal de voz
- `!dross Hola, soy Dross.`
- `!freezer Que tal?`
- `!decir Hola mundo`
- `!voz` para consultar o cambiar la voz Loquendo

## Seguridad

No subas credenciales reales a GitHub. El repositorio incluye un `.gitignore` para excluir archivos sensibles como:

- `config.py`
- `voz.json`
- `temp/`
- `__pycache__/`
- variables de entorno

## Estructura principal

- `bot.py`: lógica principal del bot
- `config.example.py`: plantilla de configuración
- `fish_audio.py`: integración con Fish Audio
- `sonidos/`: sonidos permanentes del bot
- `temp/`: archivos temporales generados durante la ejecución

## Notas

Este proyecto está pensado para ejecutarse en un entorno Windows, porque usa rutas locales de Loquendo y una ejecución específica con FFmpeg.
