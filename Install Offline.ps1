$ErrorActionPreference = 'Stop'
try {
    $metadata = Get-Content (Join-Path $PSScriptRoot 'Offline Package.json') -Raw | ConvertFrom-Json
    $locations = @($PSScriptRoot, (Split-Path $PSScriptRoot -Parent))
    $partsFolder = $locations | Where-Object { Test-Path (Join-Path $_ $metadata.parts[0].name) } | Select-Object -First 1
    if (!$partsFolder) { throw 'Download ALL Offline.7z parts to the setup folder or its parent folder first.' }
    Write-Host 'Checking all downloaded parts. This may take a few minutes...'
    foreach ($part in $metadata.parts) {
        $path = Join-Path $partsFolder $part.name
        if (!(Test-Path $path)) { throw ('Missing part: ' + $part.name) }
        if ((Get-Item $path).Length -ne $part.size -or (Get-FileHash $path -Algorithm SHA256).Hash -ne $part.sha256) {
            throw ('Incomplete or damaged download: ' + $part.name)
        }
    }
    $destination = Join-Path $partsFolder ('Live Answer Assistant v' + $metadata.version)
    if (Test-Path $destination) { throw ('Destination already exists. Keep your existing app and extract in a new folder: ' + $destination) }
    $drive = (Get-Item $partsFolder).PSDrive
    if ($null -ne $drive.Free -and $drive.Free -lt ($metadata.unpacked_bytes + 1GB)) { throw 'Not enough free disk space for extraction.' }
    & (Join-Path $PSScriptRoot '7z.exe') x (Join-Path $partsFolder $metadata.parts[0].name) ('-o' + $destination) -y
    if ($LASTEXITCODE -ne 0) { throw 'Extraction failed. Keep the downloaded parts and retry in a new folder.' }
    Write-Host ('Installed: ' + $destination)
    Write-Host 'Both models are included. Start the app, select 2B or 4B, then test / warm up.'
    if ($env:LIVE_ASSISTANT_SETUP_TEST -ne '1') { Start-Process (Join-Path $destination 'Live Answer Assistant.exe') }
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
