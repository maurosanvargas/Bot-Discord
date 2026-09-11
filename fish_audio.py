import requests
import config


def generar_audio_fish(texto, reference_id, archivo_salida):

    response = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {config.FISH_AUDIO_API_KEY}",
            "Content-Type": "application/json",
            "model": "s2.1-pro-free",
        },
        json={
            "text": texto,
            "reference_id": reference_id,
            "format": "mp3",
        },
    )

    if response.status_code != 200:
        raise Exception(
            f"Fish Audio devolvió {response.status_code}: {response.text}"
        )

    with open(archivo_salida, "wb") as f:
        f.write(response.content)

    return archivo_salida