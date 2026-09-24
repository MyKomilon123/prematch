@echo off
setlocal
cd /d "%~dp0"
color 07
title Prematch Stats Desk
cls
echo ================================================
echo             PREMATCH STATS DESK
echo ================================================
echo.
echo Carpeta: %CD%
echo.

REM Primero intenta el lanzador oficial de Python para Windows.
where py >nul 2>&1
if not errorlevel 1 goto USE_PY

REM Si no existe py.exe, intenta python.exe.
where python >nul 2>&1
if not errorlevel 1 goto USE_PYTHON

echo [ERROR] No se encontro Python en este equipo.
echo.
echo Instala Python 3 y marca "Add Python to PATH".
echo Luego vuelve a ejecutar este archivo.
echo.
pause
exit /b 1

:USE_PY
echo Python detectado mediante py.exe
echo Version:
py -3 --version
echo.
echo Iniciando servidor...
echo NO CIERRES ESTA VENTANA mientras uses la aplicacion.
echo El navegador deberia abrirse automaticamente.
echo.
py -3 -u app.py
goto END

:USE_PYTHON
echo Python detectado mediante python.exe
echo Version:
python --version
echo.
echo Iniciando servidor...
echo NO CIERRES ESTA VENTANA mientras uses la aplicacion.
echo El navegador deberia abrirse automaticamente.
echo.
python -u app.py

goto END

:END
echo.
echo ================================================
echo El servidor se ha detenido.
echo Codigo de salida: %errorlevel%
echo ================================================
echo.
pause
endlocal
