# Contexto técnico del proyecto: Loquendo Discord

## Propósito

Este proyecto es un bot personal de Discord escrito en Python. Su función principal es convertir texto en audio mediante Fish Audio, combinarlo con sonidos MP3 locales y reproducir el resultado en un canal de voz de Discord.

El nombre histórico del proyecto es `Loquendo Discord`, pero Loquendo ya fue eliminado completamente del código. El motor TTS actual y único es Fish Audio.

No es un SaaS, no tiene página web, no tiene API propia, no tiene cuentas de usuario y no utiliza base de datos.

## Estado actual

- El bot funciona localmente en Windows.
- También fue probado dentro de un contenedor Docker Linux.
- La imagen Docker se construye correctamente.
- Fish Audio, los sonidos, FFmpeg, las colas y la reproducción de Discord funcionan.
- Loquendo, sus comandos, su configuración y sus pruebas fueron eliminados.
- El despliegue previsto en una plataforma externa es un proceso persistente tipo Background Worker.
- Render detecta Docker, pero su Background Worker no es gratuito en el plan mostrado durante la configuración.

## Flujo principal

```text
Usuario de Discord
        |
        v
Comando !dross, !freezer, etc.
        |
        v
Cola independiente del servidor/guild
        |
        v
Separación del texto en segmentos
        |
        +--> Texto TTS -> Fish Audio -> MP3 temporal
        |
        +--> Marcador (sonido) -> sonidos/nombre.mp3
        |
        v
FFmpeg mezcla y concatena los segmentos
        |
        v
Discord Voice mediante FFmpegPCMAudio
```

Un mensaje puede combinar texto, sonidos y hasta tres modelos de voz Fish Audio.

Ejemplo:

```text
!dross Este es el texto (dross1). !freezer Segunda voz (pistol).
```

Conceptualmente se procesa como:

1. Fish Audio con el modelo `dross` para el primer texto.
2. `sonidos/dross1.mp3`.
3. Fish Audio con el modelo `freezer` para el segundo texto.
4. `sonidos/pistol.mp3`.
5. FFmpeg concatena todo respetando el orden.

## Estructura relevante

```text
Loquendo Discord/
├── bot.py
├── config.py                 # Configuración local, ignorada por Git
├── config.example.py         # Plantilla sin secretos
├── fish_audio.py             # Cliente HTTP de Fish Audio
├── Dockerfile
├── .dockerignore
├── Iniciar Bot.bat           # Arranque local en Windows
├── README.md
├── requirements.txt
├── test_fish.py              # Prueba manual con petición real a Fish
├── test_fish_module.py       # Prueba manual del módulo Fish
├── test_fish_segments.py    # Pruebas del parser de voces y sonidos
├── test_import.py            # Comprueba el SDK de Fish instalado
├── screamer/
│   ├── grito.mp3
│   └── screamer.jpg
├── sonidos/                  # Cualquier MP3 se convierte en marcador
└── temp/                     # Archivos temporales generados
```

`config.py`, `.env`, `temp/`, `__pycache__/` y los archivos compilados están excluidos por `.gitignore` o `.dockerignore` según corresponda.

## `bot.py`

`bot.py` contiene toda la lógica principal del bot:

- Configuración de `discord.py`.
- Registro dinámico de comandos Fish.
- Detección de sonidos locales.
- Separación de texto, voces y efectos.
- Generación de audio Fish.
- Composición mediante FFmpeg.
- Cola y worker independiente por guild.
- Reproducción de audio en Discord.
- Auto-leave cuando el canal queda vacío.
- Comandos generales y comando `!comandos`.

### Comandos actuales

Los nombres de comandos son insensibles a mayúsculas y minúsculas gracias a `case_insensitive=True`.

Comandos generales:

- `!join`: conecta el bot al canal de voz del usuario.
- `!leave`: desconecta el bot.
- `!skip`: detiene el audio que se está reproduciendo.
- `!ping`: prueba básica del bot.
- `!comandos`: muestra comandos, voces y sonidos disponibles.
- `!screamer`: envía la imagen del screamer y puede reproducir su sonido.
- `!shutdown`: apaga el bot; requiere permisos de administrador.

Comandos Fish:

- `!freezer`
- `!gohan`
- `!babidick`
- `!illojuan`
- `!arthur`
- `!dross`
- `!xokas`
- `!fernanfloo`
- `!rubius`
- `!auron`
- `!robot`
- `!caca`
- `!gaspi`
- `!walter`
- `!john`

Los comandos Fish se crean automáticamente desde `config.MODELOS_IA`. No hay una función independiente escrita manualmente para cada voz.

## Sistema de sonidos

El directorio `sonidos/` se escanea automáticamente en tiempo de ejecución.

Para cada archivo:

```text
sonidos/pistol.mp3 -> (pistol)
sonidos/dross1.mp3 -> (dross1)
```

Reglas importantes:

- Los sonidos deben escribirse entre paréntesis.
- El nombre del marcador corresponde al nombre del archivo sin `.mp3`.
- El sistema no está limitado a una lista fija de sonidos.
- Los nombres se normalizan a minúsculas internamente.
- No reemplazar este sistema por una lista fija de `dross1`, `dross2` y `dross3`.
- Los marcadores de sonidos no son comandos de Discord.

## Cola y reproducción

La cola es completamente local y está almacenada en memoria:

- `colas_audio`: una cola por guild.
- `workers`: tarea encargada de procesar cada cola.
- `workers_iniciados`: evita iniciar workers duplicados.
- `reproduciendo`: registra guilds con audio activo.

No se utilizan Redis, Celery, bases de datos ni servicios externos para la cola. Para este proyecto personal se debe conservar esta arquitectura sencilla salvo que exista una necesidad concreta.

Cada elemento de la cola contiene el contexto de Discord, el texto, el motor y el modelo Fish. El worker genera el audio, lo reproduce, espera a que termine y elimina los archivos temporales.

## Fish Audio

`fish_audio.py` realiza una petición HTTP `POST` a:

```text
https://api.fish.audio/v1/tts
```

Envía:

- el texto,
- el `reference_id` del modelo,
- formato `mp3`,
- la API key en la cabecera Authorization.

La integración activa utiliza `requests`. El SDK de Fish aparece en `test_import.py`, pero la generación principal del bot utiliza la API HTTP.

## Configuración

La plantilla `config.example.py` utiliza variables de entorno:

```python
TOKEN = os.getenv("DISCORD_TOKEN", "")
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
```

En Render/Docker se deben configurar:

```text
DISCORD_TOKEN
FISH_AUDIO_API_KEY
```

`TEMP_PATH` es opcional. Si no se especifica, se crea una carpeta `temp` junto al código.

Para uso local, `config.py` está ignorado por Git y puede contener la configuración local. Nunca incluir claves reales en este documento ni en `config.example.py`.

## Dependencias

`requirements.txt` contiene actualmente:

- `discord.py==2.7.1`
- `PyNaCl==1.6.0`
- `davey`
- `requests>=2.31.0`

Además, FFmpeg debe estar disponible en el sistema. `davey` es necesario para que la versión actual de `discord.py` pueda conectarse a canales de voz.

## Arranque local

En Windows se puede utilizar:

```text
Iniciar Bot.bat
```

El `.bat` cambia automáticamente a la carpeta donde se encuentra el propio archivo y ejecuta:

```text
python bot.py
```

También se puede iniciar manualmente:

```powershell
python bot.py
```

Para uso diario local no es obligatorio utilizar Docker.

## Docker

El `Dockerfile` actual:

- utiliza `python:3.11-slim`,
- instala FFmpeg mediante `apt-get`,
- instala `requirements.txt`,
- copia el proyecto,
- genera `config.py` desde `config.example.py`,
- crea `temp`,
- ejecuta `python bot.py`.

Construcción:

```powershell
docker build -t discord-tts-bot .
```

Arranque local del contenedor:

```powershell
docker run --rm --env-file .env discord-tts-bot
```

El archivo `.env` local debe contener, sin comillas:

```env
DISCORD_TOKEN=valor_real
FISH_AUDIO_API_KEY=valor_real
```

`.env` está excluido del repositorio.

## Pruebas y validación

Validación de sintaxis:

```powershell
python -m py_compile bot.py config.py config.example.py fish_audio.py
```

Pruebas del parser Fish y sonidos:

```powershell
python -m unittest test_fish_segments.py
```

`test_fish.py` y `test_fish_module.py` realizan peticiones reales a Fish Audio y pueden generar archivos de audio. No deben ejecutarse como pruebas automáticas sin tener en cuenta ese consumo.

## Límites y decisiones actuales

- El bot está diseñado principalmente para Discord.
- La cola vive en memoria y se pierde al reiniciar.
- Los archivos temporales son locales y efímeros.
- No se ha implementado una API web.
- No se ha implementado una interfaz web.
- No se ha convertido el proyecto en SaaS.
- No se utiliza una base de datos.
- No se debe reintroducir Loquendo.
- No se debe eliminar FFmpeg porque también se usa para reproducir y mezclar audio.
- No se debe eliminar `subprocess` porque se utiliza para ejecutar FFmpeg.
- No se debe romper la detección dinámica de sonidos.
- No cambiar los nombres de los comandos Fish salvo que sea estrictamente necesario.

## Objetivo futuro

La idea futura es separar progresivamente:

```text
Motor TTS
    -> Procesamiento de audio
        -> Integraciones/clientes
```

Esto podría permitir Discord, OBS, Twitch, una página web o una API. Esa separación no debe implementarse todavía. El objetivo actual sigue siendo:

```text
Fish Audio + Discord + sonidos locales + FFmpeg
```

## Instrucciones para otra IA

Antes de modificar código:

1. Inspeccionar los archivos reales disponibles.
2. Explicar qué archivo y qué flujo se modificará.
3. Evitar cambios destructivos sin explicar el comportamiento perdido.
4. Mantener Fish Audio, FFmpeg, sonidos, cola y reproducción de Discord.
5. Ejecutar pruebas después de cada cambio.
6. No inventar contenido de archivos que no se hayan inspeccionado.
7. No añadir Redis, Celery, bases de datos, APIs web ni arquitectura SaaS sin una petición explícita.
8. Mantener Python 3.11.
9. Mantener Docker funcional para plataformas con Background Worker.
10. No pedir que se suba el proyecto a GitHub; el repositorio ya se gestiona manualmente.
