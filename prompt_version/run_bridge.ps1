$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BridgeExe = Join-Path $RootDir 'tools\o6_bridge.exe'
$BridgePy = Join-Path $RootDir 'tools\o6_bridge.py'
$PythonExe = if ($env:O6_BRIDGE_PYTHON) { $env:O6_BRIDGE_PYTHON } else { 'python' }

if (Test-Path $BridgeExe) {
    & $BridgeExe @args
    exit $LASTEXITCODE
}

& $PythonExe $BridgePy @args
exit $LASTEXITCODE
