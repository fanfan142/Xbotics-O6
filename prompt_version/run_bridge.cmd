@echo off
setlocal
set "ROOT=%~dp0"
set "BRIDGE_EXE=%ROOT%tools\o6_bridge.exe"
set "BRIDGE_PY=%ROOT%tools\o6_bridge.py"
set "PYTHON_EXE=python"
if not "%O6_BRIDGE_PYTHON%"=="" set "PYTHON_EXE=%O6_BRIDGE_PYTHON%"
if exist "%BRIDGE_EXE%" (
  "%BRIDGE_EXE%" %*
  exit /b %ERRORLEVEL%
)
"%PYTHON_EXE%" "%BRIDGE_PY%" %*
exit /b %ERRORLEVEL%
