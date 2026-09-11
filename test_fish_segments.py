import unittest

import bot
import config


class FishSegmentsTests(unittest.TestCase):

    def test_fish_combina_tres_voces_y_sonidos(self):
        original = bot.obtener_sonidos_disponibles
        bot.obtener_sonidos_disponibles = lambda: {
            "dross1": "sonidos/dross1.mp3",
            "pistol": "sonidos/pistol.mp3",
        }

        try:
            segmentos = bot.separar_segmentos_fish(
                "!dross Hola, soy Dross. (dross1) "
                "!freezer Ah, si? (pistol) !rubius Jajaja.",
                config.MODELOS_IA["dross"]
            )
        finally:
            bot.obtener_sonidos_disponibles = original

        self.assertEqual(
            segmentos,
            [
                ("tts", "Hola, soy Dross.", "ia", config.MODELOS_IA["dross"]),
                ("sound", "sonidos/dross1.mp3"),
                ("tts", "Ah, si?", "ia", config.MODELOS_IA["freezer"]),
                ("sound", "sonidos/pistol.mp3"),
                ("tts", "Jajaja.", "ia", config.MODELOS_IA["rubius"]),
            ]
        )

    def test_fish_rechaza_mas_de_tres_voces(self):
        with self.assertRaisesRegex(ValueError, "3 voces"):
            bot.separar_segmentos_fish(
                "!dross Uno. !freezer Dos. !rubius Tres. !auron Cuatro.",
                config.MODELOS_IA["dross"]
            )
