@echo off
title PCF-SPR Sensor Generator
echo [Step 1] Activating Virtual Environment...
IF EXIST venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment not found at venv\Scripts\activate.bat
    pause
    exit /b
)

echo [Step 2] Running Generator...
python run_generator.py

echo.
echo Process finished.
pause
