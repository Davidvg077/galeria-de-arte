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

    & $docker compose --env-file $envFile -f $compose up --detach --force-recreate frontend-proxy
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose failed to reload the API proxy configuration.'
    }

    $deadline = (Get-Date).AddMinutes(3)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        & $docker compose --env-file $envFile -f $compose ps --status running 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            try {
                $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 5
                $api = Invoke-WebRequest -Uri 'http://127.0.0.1:3002/health' -TimeoutSec 5
                $works = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/works?limit=4' -TimeoutSec 5
                $galleries = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/galleries' -TimeoutSec 5
                if ($page.StatusCode -eq 200 -and
                    $page.Content -match 'GART Gallery' -and
                    $api.StatusCode -eq 200 -and
                    $works.items.Count -gt 0 -and
                    $galleries.items.Count -gt 0) {
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
        throw 'The frontend, Works API, or Gallery API did not become healthy within three minutes.'
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
        $fallbackWorks = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/works?limit=4' -TimeoutSec 10
        $fallbackGalleries = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/galleries' -TimeoutSec 10
        if ($fallbackWorks.items.Count -eq 0 -or $fallbackGalleries.items.Count -eq 0) {
            throw 'The APIs did not remain available during the frontend failover.'
        }
        Write-Output 'Automatic failover verified: the main URL served the backup after stopping the primary.'
    } finally {
        & $docker compose @composeArguments start frontend-primary
        if ($LASTEXITCODE -ne 0) {
            throw 'The backup passed failover, but the primary frontend could not be restarted.'
        }
    }

    $deadline = (Get-Date).AddSeconds(60)
    $recovered = $false
    $recoveryError = $null
    do {
        try {
            $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 5
            $primaryContainer = & $docker compose @composeArguments ps -q frontend-primary
            if ($LASTEXITCODE -ne 0 -or -not $primaryContainer) {
                throw 'Could not identify the primary frontend container.'
            }
            $primaryHealth = & $docker inspect --format '{{.State.Health.Status}}' $primaryContainer
            if ($LASTEXITCODE -ne 0) {
                throw 'Could not read the primary frontend health status.'
            }
            if ($page.StatusCode -eq 200 -and
                $page.Content -match 'GART Gallery' -and
                $primaryHealth -eq 'healthy') {
                $recovered = $true
                break
            }
        } catch {
            $recoveryError = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    if (-not $recovered) {
        if ($recoveryError) {
            throw "The primary frontend did not become healthy after the failover check: $recoveryError"
        }
        throw "The primary frontend did not become healthy after the failover check (health: $primaryHealth)."
    }

    $composeStatus = & $docker compose @composeArguments ps
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not collect the final Docker Compose status.'
    }

    $evidenceDirectory = Join-Path $repositoryRoot 'evidence\docker'
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $evidenceFile = Join-Path $evidenceDirectory "docker-api-check-$timestamp.txt"
    @(
        "Local time: $(Get-Date -Format o)"
        'Stack: gart-gallery'
        ''
        '=== Docker Compose ==='
        $composeStatus
        ''
        '=== Website API responses through the primary URL ==='
        "GET /: HTTP $($page.StatusCode) - GART Gallery present"
        "GET /api/works?limit=4: HTTP 200 - $($works.items.Count) works"
        "GET /api/galleries: HTTP 200 - $($galleries.items.Count) galleries"
        ''
        '=== Failover ==='
        'The primary frontend was stopped temporarily; the main URL and both APIs continued to respond via the backup.'
        "GET /api/works?limit=4 during failover: HTTP 200 - $($fallbackWorks.items.Count) works"
        "GET /api/galleries during failover: HTTP 200 - $($fallbackGalleries.items.Count) galleries"
        "Primary recovered: Docker health=$primaryHealth; main URL returned HTTP $($page.StatusCode)"
        ''
        'Local database credentials are excluded from this evidence.'
    ) | Set-Content -Path $evidenceFile -Encoding utf8

    Write-Output "Evidence: $evidenceFile"
    Write-Output ''
    Write-Output 'Main site:  http://127.0.0.1:8080/'
    Write-Output 'Backup:     http://127.0.0.1:8081/'
    Write-Output 'Works API:  http://127.0.0.1:3002/docs'
    Write-Output 'Works and galleries APIs are proxied under /api/ on the main site.'
} finally {
    Pop-Location
}
