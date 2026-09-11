import fish_audio
import config
import os


archivo = os.path.join(
    config.TEMP_PATH,
    "prueba_modulo.mp3"
)


try:
    fish_audio.generar_audio_fish(
        "Hola. Soy Freezer probando el nuevo módulo de audio.",
        config.MODELOS_IA["freezer"],
        archivo
    )

    print("Audio generado correctamente:")
    print(archivo)

except Exception as e:
    print("Error:")
    print(e)