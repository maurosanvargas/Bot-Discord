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

    def test_fish_permite_mas_de_tres_voces(self):
        segmentos = bot.separar_segmentos_fish(
            "!dross Uno. !freezer Dos. !rubius Tres. !auron Cuatro.",
            config.MODELOS_IA["dross"]
        )
        self.assertEqual(len(segmentos), 4)
        self.assertEqual(segmentos[0], ("tts", "Uno.", "ia", config.MODELOS_IA["dross"]))
        self.assertEqual(segmentos[1], ("tts", "Dos.", "ia", config.MODELOS_IA["freezer"]))
        self.assertEqual(segmentos[2], ("tts", "Tres.", "ia", config.MODELOS_IA["rubius"]))
        self.assertEqual(segmentos[3], ("tts", "Cuatro.", "ia", config.MODELOS_IA["auron"]))
