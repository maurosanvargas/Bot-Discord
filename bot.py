import asyncio
import os
import re
import shutil
import subprocess
import uuid
import random

import discord
from discord.ext import commands

import config
import fish_audio


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    case_insensitive=True
)


# ============================================================
# ESTADO DEL BOT
# ============================================================

# Una cola independiente por servidor.
colas_audio = {}

# Un worker independiente por servidor.
workers = {}

# Evita iniciar el mismo worker dos veces.
workers_iniciados = set()

# Servidores que actualmente están procesando/reproduciendo
# un elemento de audio.
reproduciendo = set()


# ============================================================
# CONFIGURACIÓN DE SONIDOS
# ============================================================

SONIDOS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "sonidos"
)

# Marcadores permitidos actualmente.
#
# El usuario puede escribir:
# (dross1)
# (dross2)
# (dross3)
#
# Los archivos correspondientes deben existir en:
# sonidos\dross1.mp3
# sonidos\dross2.mp3
# sonidos\dross3.mp3

def obtener_sonidos_disponibles():
    """
    Busca automaticamente todos los .mp3
    dentro de la carpeta sonidos y devuelve

    El nombre del archivo sera el nombre del marcador.
    Ejemplo:
        sonidos\dross1.mp3 -> dross1
        sonidos\dross2.mp3 -> dross2
    """

    sonidos = {}

    if not os.path.isdir(SONIDOS_PATH):
        return sonidos

    for archivo in os.listdir(SONIDOS_PATH):
        if archivo.lower().endswith(".mp3"):
            nombre = os.path.splitext(archivo)[0].lower()
            ruta = os.path.join(SONIDOS_PATH, archivo)
            sonidos[nombre] = ruta

    return sonidos


def separar_segmentos_audio(texto):
    """Separa texto TTS y marcadores de sonidos conocidos."""

    sonidos = obtener_sonidos_disponibles()
    segmentos = []
    posicion = 0
    for coincidencia in re.finditer(
        r"\(([^()\r\n]+)\)",
        texto
    ):
        nombre = coincidencia.group(1).strip().lower()
        archivo = sonidos.get(nombre)

        if archivo is None:
            continue

        texto_anterior = texto[
            posicion:coincidencia.start()
        ].strip()

        if texto_anterior:
            segmentos.append(
                ("tts", texto_anterior)
            )

        segmentos.append(
            ("sound", archivo)
        )

        posicion = coincidencia.end()

    texto_restante = texto[posicion:].strip()

    if texto_restante:
        segmentos.append(
            ("tts", texto_restante)
        )

    if not segmentos:
        segmentos.append(
            ("tts", texto)
        )

    return segmentos


def separar_segmentos_fish(texto, modelo_inicial):
    """Separa hasta tres voces Fish Audio y sonidos MP3."""

    sonidos = obtener_sonidos_disponibles()
    segmentos = []
    posicion = 0
    modelo_actual = modelo_inicial
    voces_utilizadas = {modelo_inicial}

    patron_voces = "|".join(
        re.escape(nombre)
        for nombre in config.MODELOS_IA
    )

    for coincidencia in re.finditer(
        rf"!(?:{patron_voces})\b|\(([^()\r\n]+)\)",
        texto,
        flags=re.IGNORECASE
    ):
        marcador = coincidencia.group(0)
        es_voz = marcador.startswith("!")

        if es_voz:
            nombre_voz = marcador[1:].lower()
            nuevo_modelo = config.MODELOS_IA[nombre_voz]

            if nuevo_modelo != modelo_actual:
                voces_utilizadas.add(nuevo_modelo)

            if len(voces_utilizadas) > 3:
                raise ValueError(
                    "Un mensaje puede utilizar como máximo "
                    "3 voces Fish Audio."
                )
        else:
            nombre_sonido = coincidencia.group(1).strip().lower()
            archivo = sonidos.get(nombre_sonido)

            if archivo is None:
                continue

        texto_anterior = texto[
            posicion:coincidencia.start()
        ].strip()

        if texto_anterior:
            segmentos.append(
                ("tts", texto_anterior, "ia", modelo_actual)
            )

        if es_voz:
            modelo_actual = nuevo_modelo
        else:
            segmentos.append(
                ("sound", archivo)
            )

        posicion = coincidencia.end()

    texto_restante = texto[posicion:].strip()

    if texto_restante:
        segmentos.append(
            ("tts", texto_restante, "ia", modelo_actual)
        )

    if not segmentos:
        segmentos.append(
            ("tts", texto, "ia", modelo_inicial)
        )

    return segmentos

# ============================================================
# CARPETA TEMPORAL
# ============================================================

def asegurar_temp():
    """Se asegura de que exista la carpeta temporal."""

    os.makedirs(
        config.TEMP_PATH,
        exist_ok=True
    )


def asegurar_sonidos():
    """Se asegura de que exista la carpeta de sonidos."""

    os.makedirs(
        SONIDOS_PATH,
        exist_ok=True
    )


def limpiar_temp():
    """
    Elimina archivos temporales antiguos al iniciar el bot.

    Solo elimina archivos creados por este bot.
    Los sonidos permanentes de /sonidos no se tocan.
    """

    asegurar_temp()

    eliminados = 0

    try:
        for archivo in os.listdir(config.TEMP_PATH):

            if not (
                archivo.startswith("mensaje_")
                or archivo.startswith("audio_")
                or archivo.startswith("mezcla_")
            ):
                continue

            ruta = os.path.join(
                config.TEMP_PATH,
                archivo
            )

            if not os.path.isfile(ruta):
                continue

            try:
                os.remove(ruta)
                eliminados += 1

            except OSError as e:
                print(
                    f"⚠️ No se pudo eliminar "
                    f"{archivo}: {e}"
                )

    except OSError as e:
        print(
            f"⚠️ Error accediendo a temp: {e}"
        )
        return

    if eliminados:
        print(
            f"🧹 Limpieza temp: "
            f"{eliminados} archivo(s) eliminado(s)."
        )


# ============================================================
# UTILIDADES DE ARCHIVOS
# ============================================================

def eliminar_archivo(ruta):
    """Elimina un archivo si existe."""

    if not ruta:
        return

    try:
        if os.path.exists(ruta):
            os.remove(ruta)

    except OSError as e:
        print(
            f"⚠️ No se pudo eliminar "
            f"{ruta}: {e}"
        )


# ============================================================
# SONIDOS / MARCADORES
# ============================================================

# ============================================================
# FISH AUDIO
# ============================================================

def generar_audio_ia(
    texto,
    modelo,
    archivo_audio
):
    """
    Genera audio mediante Fish Audio.

    La función original es síncrona, por lo que
    se ejecuta mediante asyncio.to_thread().
    """

    asegurar_temp()

    try:
        fish_audio.generar_audio_fish(
            texto,
            modelo,
            archivo_audio
        )

        if not os.path.exists(
            archivo_audio
        ):
            raise RuntimeError(
                "Fish Audio terminó pero no generó "
                f"el archivo esperado: {archivo_audio}"
            )

        return archivo_audio

    except Exception:

        try:
            if os.path.exists(
                archivo_audio
            ):
                os.remove(
                    archivo_audio
                )
        except OSError:
            pass

        raise


# ============================================================
# GENERACIÓN DE SEGMENTOS TTS
# ============================================================

async def generar_segmento_tts(
    texto,
    motor,
    voz
):
    """
    Genera un segmento TTS y devuelve:

        archivo_audio
        archivo_texto

    archivo_texto será None para Fish Audio.
    """

    if motor == "ia":

        identificador = uuid.uuid4().hex[:8]

        archivo_audio = os.path.join(
            config.TEMP_PATH,
            f"audio_{identificador}.mp3"
        )

        await asyncio.to_thread(
            generar_audio_ia,
            texto,
            voz,
            archivo_audio
        )

        return archivo_audio, None

    raise RuntimeError(f"Motor de audio no compatible: {motor}")


# ============================================================
# COMPOSICIÓN DE AUDIO
# ============================================================

def obtener_ffmpeg():
    """
    Obtiene la ubicación de FFmpeg.

    FFmpeg ya forma parte del entorno actual del bot.
    """

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg no está disponible en PATH."
        )

    return ffmpeg


def componer_audios(
    archivos,
    archivo_salida,
    separacion_ms=0
):
    """
    Une varios archivos de audio en un único MP3.

    Se utiliza FFmpeg para hacer la composición.
    """

    if not archivos:
        raise RuntimeError(
            "No hay archivos de audio para componer."
        )

    if len(archivos) == 1:

        origen = archivos[0]

        if os.path.abspath(origen) != os.path.abspath(
            archivo_salida
        ):
            shutil.copyfile(
                origen,
                archivo_salida
            )

        return archivo_salida

    ffmpeg = obtener_ffmpeg()

    comando = [
        ffmpeg,
        "-y"
    ]

    # Entradas.
    for archivo in archivos:

        comando.extend(
            [
                "-i",
                archivo
            ]
        )

    # Cada entrada se convierte en un segmento
    # concatenable. El resultado final conserva
    # exactamente el orden recibido.
    filtros = []

    for indice in range(len(archivos)):

        filtros.append(
            f"[{indice}:a]"
            f"aresample=48000,"
            f"aformat=sample_fmts=fltp:"
            f"sample_rates=48000:"
            f"channel_layouts=stereo"
            f"[a{indice}]"
        )

    entradas_concat = []

    for indice in range(len(archivos)):

        entradas_concat.append(
            f"[a{indice}]"
        )

        if (
            separacion_ms > 0
            and indice < len(archivos) - 1
        ):
            duracion = separacion_ms / 1000
            etiqueta = f"silencio{indice}"

            filtros.append(
                f"anullsrc=r=48000:cl=stereo:d={duracion:.3f}"
                f"[{etiqueta}]"
            )

            entradas_concat.append(
                f"[{etiqueta}]"
            )

    filtros.append(
        f"{''.join(entradas_concat)}"
        f"concat=n={len(entradas_concat)}:"
        f"v=0:a=1"
        f"[out]"
    )

    filter_complex = ";".join(
        filtros
    )

    comando.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            archivo_salida
        ]
    )

    resultado = subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    if resultado.returncode != 0:

        error = resultado.stderr.strip()

        raise RuntimeError(
            "FFmpeg no pudo componer los audios"
            + (
                f": {error}"
                if error
                else ""
            )
        )

    if not os.path.exists(
        archivo_salida
    ):
        raise RuntimeError(
            "FFmpeg terminó pero no generó "
            f"el archivo final: {archivo_salida}"
        )

    return archivo_salida


async def generar_audio_compuesto(
    texto,
    motor,
    voz
):
    """
    Analiza un mensaje, genera sus segmentos TTS
    y mezcla TTS + sonidos en un único archivo.

    Devuelve:

        archivo_final
        archivos_temporales
    """

    if motor != "ia":
        raise RuntimeError(f"Motor de audio no compatible: {motor}")

    segmentos = separar_segmentos_fish(
        texto,
        voz
    )

    archivos_audio = []
    archivos_temporales = []

    try:

        for segmento in segmentos:

            tipo = segmento[0]

            if tipo == "sound":

                archivos_audio.append(
                    segmento[1]
                )

                continue

            if tipo == "tts":

                contenido = segmento[1]
                segmento_motor = (
                    segmento[2]
                    if len(segmento) > 2
                    else motor
                )
                segmento_voz = (
                    segmento[3]
                    if len(segmento) > 3
                    else voz
                )

                audio, archivo_texto = (
                    await generar_segmento_tts(
                        contenido,
                        segmento_motor,
                        segmento_voz
                    )
                )

                archivos_audio.append(
                    audio
                )

                archivos_temporales.append(
                    audio
                )

                if archivo_texto:
                    archivos_temporales.append(
                        archivo_texto
                    )

                continue

            raise RuntimeError(
                f"Tipo de segmento desconocido: {tipo}"
            )

        identificador = uuid.uuid4().hex[:8]

        archivo_final = os.path.join(
            config.TEMP_PATH,
            f"mezcla_{identificador}.mp3"
        )

        # Si hay solamente un segmento TTS
        # y no hay sonidos, podemos utilizarlo
        # directamente sin recodificar.
        if (
            len(archivos_audio) == 1
            and segmentos[0][0] == "tts"
        ):

            archivo_final = archivos_audio[0]

        else:

            await asyncio.to_thread(
                componer_audios,
                archivos_audio,
                archivo_final,
                (
                    config.FISH_AUDIO_SEGMENT_DELAY_MS
                    if motor == "ia"
                    else 0
                )
            )

            # El archivo final pasa a ser temporal.
            archivos_temporales.append(
                archivo_final
            )

        return (
            archivo_final,
            archivos_temporales
        )

    except Exception:

        for archivo in archivos_temporales:
            eliminar_archivo(
                archivo
            )

        raise


# ============================================================
# COLAS POR SERVIDOR
# ============================================================

def obtener_cola(guild_id):
    """
    Obtiene la cola del servidor.

    Si todavía no existe, la crea.
    """

    if guild_id not in colas_audio:

        colas_audio[guild_id] = (
            asyncio.Queue()
        )

    return colas_audio[guild_id]


def iniciar_worker(guild_id):
    """
    Inicia un worker para un servidor
    si todavía no existe.
    """

    if guild_id in workers_iniciados:
        return

    cola = obtener_cola(
        guild_id
    )

    workers[guild_id] = (
        bot.loop.create_task(
            procesador_cola(
                guild_id,
                cola
            )
        )
    )

    workers_iniciados.add(
        guild_id
    )

    print(
        f"⚙️ Worker iniciado para servidor "
        f"{guild_id}"
    )


# ============================================================
# PROCESADOR DE COLA
# ============================================================

async def procesador_cola(
    guild_id,
    cola
):
    """
    Procesa exclusivamente la cola de un servidor.

    Cada elemento puede contener:
        - Fish Audio
        - TTS + sonidos intercalados

    Un error en un audio NO mata el worker.
    """

    while not bot.is_closed():

        ctx, texto, motor, voz = (
            await cola.get()
        )

        archivos_temporales = []

        reproduciendo.add(
            guild_id
        )

        try:

            # ------------------------------------------------
            # COMPROBAR CONEXIÓN
            # ------------------------------------------------

            voice_client = (
                ctx.guild.voice_client
            )

            if not voice_client:

                await ctx.send(
                    "No estoy conectado a un canal de voz."
                )

                continue

            # ------------------------------------------------
            # GENERAR AUDIO
            # ------------------------------------------------

            (
                archivo_audio,
                archivos_temporales
            ) = await generar_audio_compuesto(
                texto,
                motor,
                voz
            )

            # ------------------------------------------------
            # VOLVER A COMPROBAR CONEXIÓN
            # ------------------------------------------------

            voice_client = (
                ctx.guild.voice_client
            )

            if not voice_client:

                raise RuntimeError(
                    "El bot se desconectó mientras "
                    "se generaba el audio."
                )

            # ------------------------------------------------
            # MENSAJE DE REPRODUCCIÓN
            # ------------------------------------------------

            await ctx.send(
                f"🔊 Reproduciendo: `{texto}`"
            )

            # ------------------------------------------------
            # REPRODUCIR
            # ------------------------------------------------

            fuente = discord.FFmpegPCMAudio(
                archivo_audio
            )

            voice_client.play(
                fuente
            )

            while voice_client.is_playing():

                await asyncio.sleep(
                    0.25
                )

            # Pequeña separación entre elementos.
            await asyncio.sleep(
                1.5
            )

        except Exception as e:

            print(
                f"❌ Error procesando audio "
                f"[{motor}]: {e}"
            )

            try:

                await ctx.send(
                    f"❌ No pude generar/reproducir "
                    f"el audio: `{e}`"
                )

            except Exception:
                pass

        finally:

            # ------------------------------------------------
            # LIMPIEZA SEGURA
            # ------------------------------------------------

            for archivo in archivos_temporales:

                eliminar_archivo(
                    archivo
                )

            reproduciendo.discard(
                guild_id
            )

            # Importante:
            # task_done SIEMPRE debe ejecutarse.
            cola.task_done()


# ============================================================
# COLA / COMANDOS DE AUDIO
# ============================================================

async def agregar_a_cola(
    ctx,
    texto,
    motor,
    voz
):
    """
    Añade un audio a la cola del servidor.

    Solo muestra el mensaje de posición cuando
    realmente hay otro audio reproduciéndose
    o esperando en la cola.
    """

    cola = obtener_cola(
        ctx.guild.id
    )

    estaba_ocupado = (
        ctx.guild.id in reproduciendo
        or not cola.empty()
    )

    await cola.put(
        (
            ctx,
            texto,
            motor,
            voz
        )
    )

    if estaba_ocupado:

        posicion = cola.qsize()

        await ctx.send(
            f"📝 Añadido a la cola. "
            f"Posición: {posicion}"
        )


# ============================================================
# EVENTO READY
# ============================================================

@bot.event
async def on_ready():

    limpiar_temp()

    asegurar_sonidos()

    print(
        f"✅ Conectado como {bot.user}"
    )

    print(
        f"🤖 Voces IA disponibles: "
        f"{len(config.MODELOS_IA)}"
    )

    print(
        "🎤 " +
        ", ".join(
            config.MODELOS_IA.keys()
        )
    )

    print(
        f"🔊 Sonidos disponibles: "
        f"{', '.join(obtener_sonidos_disponibles())}"
    )

    # Crear workers para servidores donde
    # el bot ya esté conectado.
    for guild in bot.guilds:

        if guild.voice_client:

            iniciar_worker(
                guild.id
            )


# ============================================================
# !PING
# ============================================================

@bot.command()
async def ping(ctx):

    await ctx.send(
        "Soy el coco!"
    )


# ============================================================
# !COMANDOS
# ============================================================

@bot.command()
async def comandos(ctx):

    voces = "\n".join(
        f"!{nombre}"
        for nombre in config.MODELOS_IA
    )

    sonidos = ", ".join(
        f"({nombre})"
        for nombre in obtener_sonidos_disponibles()
    )

    await ctx.send(
        "**Comandos disponibles**\n"
        "`!join` - Entrar a tu canal de voz\n"
        "`!leave` - Salir del canal de voz\n"
        "`!skip` - Saltar el audio actual\n"
        "`!ping` - Comprobar que estoy activo\n"
        "`!shutdown` - Apagar el bot (administradores)\n\n"
        "**Voces Fish Audio**\n"
        f"{voces}\n\n"
        "Escribe el texto después del comando de voz. "
        "Puedes intercalar sonidos usando paréntesis:\n"
        f"`!dross Texto de prueba (dross1)`\n\n"
        f"**Sonidos:** {sonidos}"
    )

# ============================================================
# !SCREAMER
# ============================================================

@bot.command()
async def screamer(ctx):
    ruta_imagen = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "screamer",
        "screamer.jpg"
    )

    if not os.path.exists(ruta_imagen):
        await ctx.send("❌ No encontré la foto del screamer en la ruta especificada.")
        return

    # Envía la imagen al canal actual donde se invocó el comando
    await ctx.send(file=discord.File(ruta_imagen))

    probabilidad_susto = 30

    if random.randint(1, 100) <= probabilidad_susto:

        ruta_sonido = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "screamer",
            "grito.mp3"
        )

        if not os.path.exists(ruta_sonido):
            return

        if ctx.author.voice: 
            canal = ctx.author.voice.channel
            voice_client = ctx.guild.voice_client

            try:
                if not voice_client:
                    voice_client = await canal.connect(self_deaf=True)
                    iniciar_worker(ctx.guild.id)

                if not voice_client.is_playing():
                    fuente_original = discord.FFmpegPCMAudio(
                        ruta_sonido,
                        options='-af "volume=0.3"'
                    )

                    fuente_volumen = discord.PCMVolumeTransformer(
                        fuente_original,
                        volume=0.3
                    )

                    voice_client.play(fuente_volumen)

            except Exception as e:
                print(f"❌ Error al reproducir el sonido del screamer: {e}")

# ============================================================
# !JOIN
# ============================================================

@bot.command()
async def join(ctx):

    if not ctx.author.voice:

        await ctx.send(
            "Debes estar en un canal de voz."
        )

        return

    canal = ctx.author.voice.channel

    try:

        if ctx.voice_client:

            await ctx.voice_client.move_to(
                canal
            )

        else:

            await canal.connect(
                self_deaf=True
            )

        # Garantizar que existe worker.
        iniciar_worker(
            ctx.guild.id
        )

        await ctx.send(
            "Conectado al canal de voz."
        )

    except Exception as e:

        print(
            f"❌ Error conectando al canal: {e}"
        )

        await ctx.send(
            f"❌ No pude conectarme: `{e}`"
        )


# ============================================================
# !LEAVE
# ============================================================

@bot.command()
async def leave(ctx):

    if not ctx.voice_client:

        await ctx.send(
            "No estoy conectado a un canal de voz."
        )

        return

    try:

        await ctx.voice_client.disconnect()

        await ctx.send(
            "Me mataron."
        )

    except Exception as e:

        print(
            f"❌ Error desconectando: {e}"
        )


# ============================================================
# !SKIP
# ============================================================

@bot.command(name="skip")
async def skip(ctx):
    """
    Salta el audio que se está reproduciendo actualmente.

    La cola no se modifica.
    """

    voice_client = (
        ctx.guild.voice_client
    )

    if (
        voice_client is None
        or not voice_client.is_connected()
    ):

        await ctx.send(
            "❌ No estoy conectado a un canal de voz."
        )

        return

    if not voice_client.is_playing():

        await ctx.send(
            "❌ No hay ningún audio reproduciéndose."
        )

        return

    voice_client.stop()

    await ctx.send(
        "⏭️ Audio saltado."
    )


# ============================================================
# !SHUTDOWN
# ============================================================

@bot.command()
@commands.has_permissions(
    administrator=True
)
async def shutdown(ctx):

    await ctx.send(
        "Apagando Sotelo..."
    )

    try:

        if ctx.voice_client:

            await ctx.voice_client.disconnect()

    except Exception as e:

        print(
            f"⚠️ Error desconectando durante "
            f"shutdown: {e}"
        )

    await bot.close()


# ============================================================
# GENERADOR DE COMANDOS IA
# ============================================================

def crear_comando_ia(
    nombre,
    modelo
):
    """
    Crea automáticamente un comando de Discord
    asociado a una voz/modelo de Fish Audio.

    Ejemplos:

        !freezer Hola
        !gohan Hola
        !dross Hola (dross1)

    El comando se genera desde config.MODELOS_IA.
    """

    async def comando(
        ctx,
        *,
        texto
    ):

        if not ctx.voice_client:

            await ctx.send(
                "Primero usa !join."
            )

            return

        if not texto.strip():

            await ctx.send(
                "Debes escribir algo para decir."
            )

            return

        iniciar_worker(
            ctx.guild.id
        )

        await agregar_a_cola(
            ctx,
            texto,
            "ia",
            modelo
        )

    comando.__name__ = nombre

    return commands.Command(
        comando,
        name=nombre,
        help=f"Habla con la voz IA de {nombre}."
    )


# ============================================================
# REGISTRAR TODAS LAS VOCES IA
# ============================================================

for nombre, modelo in config.MODELOS_IA.items():

    if nombre in bot.all_commands:

        print(
            f"⚠️ Comando duplicado ignorado: "
            f"!{nombre}"
        )

        continue

    bot.add_command(
        crear_comando_ia(
            nombre,
            modelo
        )
    )


# ============================================================
# AUTO-LEAVE
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    # Ignorar al propio bot y cualquier otro bot.
    if member.bot:
        return

    # Si no estaba en un canal antes,
    # no abandonó ningún canal.
    if before.channel is None:
        return

    canal = before.channel

    # Buscar si nuestro bot está en ese canal.
    for vc in bot.voice_clients:

        if vc.channel != canal:
            continue

        # Comprobar usuarios reales.
        usuarios = [
            m
            for m in canal.members
            if not m.bot
        ]

        if len(usuarios) != 0:
            break

        print(
            f"⏳ Canal vacío. "
            f"Esperando {config.AUTO_LEAVE_TIME}s..."
        )

        await asyncio.sleep(
            config.AUTO_LEAVE_TIME
        )

        # Comprobar nuevamente.
        if not vc.is_connected():
            break

        usuarios = [
            m
            for m in canal.members
            if not m.bot
        ]

        if len(usuarios) == 0:

            try:

                await vc.disconnect()

                print(
                    "👋 Desconectado por canal vacío."
                )

            except Exception as e:

                print(
                    f"⚠️ Error en auto-leave: {e}"
                )

        break


# ============================================================
# ERRORES DE COMANDOS
# ============================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    # Comando inexistente:
    # no hacemos nada para evitar spam.
    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ Falta el texto que debo decir."
        )

        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ No tienes permisos para usar "
            "este comando."
        )

        return

    print(
        f"⚠️ Error en comando "
        f"{ctx.command}: {error}"
    )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":
    bot.run(
        config.TOKEN
    )