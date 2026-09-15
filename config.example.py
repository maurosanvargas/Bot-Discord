import os

TOKEN = os.getenv("DISCORD_TOKEN", "")

TEMP_PATH = os.getenv(
    "TEMP_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
)

AUTO_LEAVE_TIME = 15

FISH_AUDIO_SEGMENT_DELAY_MS = 400

FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")

MODELOS_IA = {
    "freezer": "e921c8e95a3b4c4d8310db3ea11b3c84",
    "gohan": "fef12f2bb6d54d7bb3438273c33a0a62",
    "babidick": "525a0abb973945528a595215d8a2893c",
    "illojuan": "97582f301e1c4f93a514ceda15e23e26",
    "arthur": "40af8e6319ef4d81aa4cf22a619553bb",
    "dross": "d9f0d3d3fe734af6acb5ecc9129bc49a",
    "xokas": "d975c8843339446794fbd916532a95c3",
    "fernanfloo": "eff6261cf86f4bef839b65c6fed60a6d",
    "rubius": "937996ea4d3b4edaa28d1e3418242e8b",
    "auron": "0740a1f4e529461fb39e07f5606f7296",
    "robot": "dbf9230866e84109a902f4e5eb1796ae",
    "caca": "ae3fd7b5fd1747599113892358eb0ce1",
    "gaspi": "4911ceb45fd34a4ca3c4ef5ffa2a9a52",
    "walter": "52fc1dcd125d4ecabef0baf91807cb12",
    "john": "ea69ae4274f141cdbcabe0e56f4011d3"
}
