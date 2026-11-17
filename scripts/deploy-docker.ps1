$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$dockerFallback = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$docker = if ($dockerCommand) { $dockerCommand.Source } else { $dockerFallback }

if (-not (Test-Path -LiteralPath $docker)) {
    throw 'Docker CLI is not installed. Install and start Docker Desktop first.'
}

Push-Location $repositoryRoot
try {
    & $docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Engine is unavailable. Start Docker Desktop and run this script again.'
    }

    $envFile = Join-Path $repositoryRoot '.env.docker'
    if (-not (Test-Path -LiteralPath $envFile)) {
        $bytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $generator.GetBytes($bytes)
        } finally {
            $generator.Dispose()
        }

        $password = [Convert]::ToHexString($bytes)
        Set-Content -LiteralPath $envFile -Value "POSTGRES_PASSWORD=$password" -Encoding ascii
    }

    $compose = Join-Path $repositoryRoot 'compose.yaml'
    & $docker compose --env-file $envFile -f $compose up --detach --build
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose failed to build or start the application.'
    }

    $deadline = (Get-Date).AddMinutes(3)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        & $docker compose --env-file $envFile -f $compose ps --status running 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            try {
                $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 5
                $api = Invoke-WebRequest -Uri 'http://127.0.0.1:3002/health' -TimeoutSec 5
                if ($page.StatusCode -eq 200 -and
                    $page.Content -match 'GART Gallery' -and
                    $api.StatusCode -eq 200) {
                    $ready = $true
                    break
                }
            } catch {
                Start-Sleep -Seconds 3
            }
        } else {
            Start-Sleep -Seconds 3
        }
    }

    if (-not $ready) {
        & $docker compose --env-file $envFile -f $compose ps
        throw 'The frontend or Works API did not become healthy within three minutes.'
    }

    $composeArguments = @('--env-file', $envFile, '-f', $compose)
    & $docker compose @composeArguments stop frontend-primary
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not stop the primary frontend for the failover check.'
    }

    try {
        Start-Sleep -Seconds 2
        $fallbackPage = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 15
        if ($fallbackPage.StatusCode -ne 200 -or $fallbackPage.Content -notmatch 'GART Gallery') {
            throw 'The public frontend did not fail over to its backup.'
        }
        Write-Output 'Automatic failover verified: the main URL served the backup after stopping the primary.'
    } finally {
        & $docker compose @composeArguments start frontend-primary
        if ($LASTEXITCODE -ne 0) {
            throw 'The backup passed failover, but the primary frontend could not be restarted.'
        }
    }

    $deadline = (Get-Date).AddSeconds(60)
    do {
        try {
            $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 5
            if ($page.StatusCode -eq 200 -and $page.Content -match 'GART Gallery') {
                break
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'GART Gallery') {
        throw 'The main frontend did not recover after the failover check.'
    }

    & $docker compose @composeArguments ps
    Write-Output ''
    Write-Output 'Main site:  http://127.0.0.1:8080/'
    Write-Output 'Backup:     http://127.0.0.1:8081/'
    Write-Output 'Works API:  http://127.0.0.1:3002/docs'
} finally {
    Pop-Location
}
