import subprocess
import os
import config


def generar_audio(texto, voz):
    archivo_texto = os.path.join(config.TEMP_PATH, "mensaje.txt")
    salida = os.path.join(config.TEMP_PATH, "audio")

    # Crear archivo de texto
    with open(archivo_texto, "w", encoding="utf-8") as f:
        f.write(texto)

    # Ejecutar Loquendo
    comando = [
        config.LOQUENDO_PATH,
        "-v",
        voz,
        "-o",
        salida,
        archivo_texto
    ]

    subprocess.run(comando)

    print("Audio generado.")


generar_audio(
    "Hola amigos, soy Jorge funcionando desde Python.",
    "Jorge"
)