import requests
import config

response = requests.post(
    "https://api.fish.audio/v1/tts",
    headers={
        "Authorization": f"Bearer {config.FISH_AUDIO_API_KEY}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free",
    },
    json={
        "text": "Hola. Soy Freezer. Esta es una prueba desde Python.",
        "reference_id": "e921c8e95a3b4c4d8310db3ea11b3c84",
        "format": "mp3",
    },
)

print("Status:", response.status_code)

if response.status_code == 200:
    with open("prueba.mp3", "wb") as f:
        f.write(response.content)

    print("Audio generado correctamente.")
else:
    print(response.text)