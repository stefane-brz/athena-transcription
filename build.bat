@echo off
chcp 65001 >nul
echo ============================================
echo  Build AthenaT .exe pour Windows
echo ============================================
echo.

echo 1. Installation des dépendances...
echo   1a. PyQt5 via wheel...
python -m pip install PyQt5==5.15.11 PyQt5-Qt5==5.15.19 PyQt5_sip==12.18.0 --only-binary :all:
if %errorlevel% neq 0 exit /b %errorlevel%

echo   1b. Autres dépendances...
pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

pip install pyinstaller
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo 2. Vérification PyQt5...
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo 3. Téléchargement du modèle Whisper...
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', cache_dir='hf_home')"
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo 4. Build avec PyInstaller...
pyinstaller --onefile --windowed --name "AthenaT" ^
    --add-data "hf_home;hf_home" ^
    --collect-all PyQt5 ^
    --collect-all PyQt5-Qt5 ^
    --hidden-import ctranslate2 ^
    --hidden-import faster_whisper ^
    --hidden-import tokenizers ^
    --collect-submodules faster_whisper ^
    app/app.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo ============================================
echo  ✅ Build terminé !
echo  📁 Fichier : dist\AthenaT.exe
echo ============================================
pause
