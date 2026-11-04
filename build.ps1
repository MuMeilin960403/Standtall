<#
.SYNOPSIS
    Run the StandTall tests, build a Windows executable, and smoke-test it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build.ps1 -SkipTests -SkipSmoke
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipSmoke
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    throw "Missing .venv. Run: py -3.11 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt"
}

Write-Host '== Check dependencies ==' -ForegroundColor Cyan
& $Python -c "import PySide6, pytest, PyInstaller, PIL; print('runtime and build dependencies: ok')"
if ($LASTEXITCODE -ne 0) { throw 'Dependencies are incomplete.' }

$Icon = Join-Path $Root 'assets\standtall.ico'
if (-not (Test-Path $Icon)) {
    Write-Host '== Generate application icon ==' -ForegroundColor Cyan
    & $Python (Join-Path $Root 'scripts\make_standtall_icon.py')
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
}

if (-not $SkipTests) {
    Write-Host '== Run tests ==' -ForegroundColor Cyan
    $oldPlatform = $env:QT_QPA_PLATFORM
    $env:QT_QPA_PLATFORM = 'offscreen'
    try {
        & $Python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
    }
    finally {
        $env:QT_QPA_PLATFORM = $oldPlatform
    }
}

Write-Host '== PyInstaller build (versioned portable folder) ==' -ForegroundColor Cyan
$dist = Join-Path $Root 'dist'
$work = Join-Path $Root 'build'
$versionMatch = Select-String -Path (Join-Path $Root 'standtall\__init__.py') -Pattern '__version__\s*=\s*"([^"]+)"'
if (-not $versionMatch) { throw 'Could not read the application version.' }
$Version = $versionMatch.Matches[0].Groups[1].Value
$Name = "StandTallPortable-$Version"
$PortableDir = Join-Path $dist $Name
$Exe = Join-Path $PortableDir "$Name.exe"
$Zip = Join-Path $dist 'StandTall-Portable.zip'

# The stable dist\StandTallPortable folder may be the currently running old
# instance. Build a fresh versioned folder instead of deleting it.
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Remove-Item -Recurse -Force $PortableDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work | Out-Null

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name $Name `
    --icon $Icon `
    --distpath $dist `
    --workpath $work `
    --specpath $work `
    --exclude-module tkinter `
    (Join-Path $Root 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

if (-not (Test-Path $Exe)) { throw "$Name.exe was not produced." }

if (-not $SkipSmoke) {
    Write-Host '== Smoke-test portable executable ==' -ForegroundColor Cyan
    $smokeDir = Join-Path $Root ('.build-smoke-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null
    $oldDataDir = $env:STANDTALL_DATA_DIR
    $oldQtPlatform = $env:QT_QPA_PLATFORM
    $env:STANDTALL_DATA_DIR = $smokeDir
    $env:QT_QPA_PLATFORM = 'windows'
    try {
        $process = Start-Process -FilePath $Exe -ArgumentList '--smoke-test' -WorkingDirectory $PortableDir -PassThru
        if (-not $process.WaitForExit(40000)) {
            $process.Kill()
            throw 'Portable smoke test timed out.'
        }
        $process.Refresh()
        $marker = Join-Path $smokeDir 'smoke-ok.txt'
        $exitCode = $process.ExitCode
        if ((-not (Test-Path $marker)) -or ($null -ne $exitCode -and $exitCode -ne 0)) {
            $log = Join-Path $smokeDir 'logs\standtall.log'
            if (Test-Path $log) { Get-Content $log -Tail 50 }
            throw "Portable smoke test failed (exit code: $exitCode)."
        }
        Write-Host 'Smoke test passed.' -ForegroundColor Green
        Remove-Item -Recurse -Force $smokeDir -ErrorAction SilentlyContinue
    }
    finally {
        $env:STANDTALL_DATA_DIR = $oldDataDir
        $env:QT_QPA_PLATFORM = $oldQtPlatform
    }
}

Write-Host '== Package portable zip ==' -ForegroundColor Cyan
Remove-Item -Force $Zip -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $PortableDir '*') -DestinationPath $Zip -CompressionLevel Optimal

$SizeMb = [math]::Round((Get-Item $Zip).Length / 1MB, 1)
Write-Host ''
Write-Host "Portable build: $Exe" -ForegroundColor Green
Write-Host "Distribution zip: $Zip ($SizeMb MB)" -ForegroundColor Green
Write-Host 'Keep the whole folder together; do not copy only the exe.' -ForegroundColor Yellow
