@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo No hay Python para compilar en esta computadora.
  echo Usa el compilador gratuito en GitHub Actions incluido con el proyecto.
  pause
  exit /b 1
)
py -3.12 -m pip install -r requirements.txt "pyinstaller>=6.11,<7"
if errorlevel 1 (
  echo Fallo la instalacion de dependencias para compilar.
  pause
  exit /b 1
)
py -3.12 -m PyInstaller --noconfirm --clean --onefile --console --name GO_Arequipa_Noticias --add-data "templates;templates" --add-data "static;static" --add-data "config.json;." --collect-all tzdata portable_launcher.py
if errorlevel 1 (
  echo Fallo la compilacion.
  pause
  exit /b 1
)
echo Ejecutable creado: dist\GO_Arequipa_Noticias.exe
pause
