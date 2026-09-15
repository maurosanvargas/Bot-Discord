@echo off
setlocal

title Discord TTS Bot

REM Se ejecuta desde la carpeta del proyecto.
cd /d "%~dp0"

echo Iniciando Discord TTS Bot...

echo.

echo Si no tienes un entorno virtual activo, se recomienda usar:
	echo   python -m venv .venv
	echo   .venv\Scripts\activate

echo.

python bot.py

echo.
echo El bot se ha detenido.
pause

endlocal