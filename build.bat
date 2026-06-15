@echo off
chcp 65001 >nul
echo ============================================
echo  Build AthenaT .exe pour Windows
echo ============================================
echo.

echo 1. Installation des dépendances...
pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

pip install pyinstaller
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo 2. Téléchargement du modèle Whisper...
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', cache_dir='hf_home')"
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo 3. Build avec PyInstaller...
pyinstaller --onefile --windowed --name "AthenaT" ^
    --add-data "hf_home;hf_home" ^
    --collect-all PyQt5 ^
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
