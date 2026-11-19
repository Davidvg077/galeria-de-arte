$ErrorActionPreference = 'Stop'

$backendRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $backendRoot
$dockerFallback = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$docker = if ($dockerCommand) { $dockerCommand.Source } else { $dockerFallback }

function Test-HttpStatus {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][int]$ExpectedStatus
    )

    $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5 -SkipHttpErrorCheck
    return $response.StatusCode -eq $ExpectedStatus
}

if (-not (Test-Path -LiteralPath $docker)) {
    throw 'Docker CLI is not installed. Install and start Docker Desktop first.'
}

Push-Location $repositoryRoot
try {
    & $docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Engine is unavailable. Start Docker Desktop and run this script again.'
    }

    $envFile = Join-Path $backendRoot '.env.docker'
    $environmentLines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $envFile) {
        $existingEnvironment = [System.IO.File]::ReadAllText($envFile)
        $entries = [regex]::Matches(
            $existingEnvironment,
            '(POSTGRES_PASSWORD|TOKEN_PEPPER)=([^\r\n]*?)(?=(?:POSTGRES_PASSWORD|TOKEN_PEPPER)=|\r?\n|$)'
        )
        foreach ($entry in $entries) {
            $secretName = $entry.Groups[1].Value
            $alreadyLoaded = $false
            foreach ($line in $environmentLines) {
                if ($line.StartsWith("$secretName=", [System.StringComparison]::Ordinal)) {
                    $alreadyLoaded = $true
                    break
                }
            }
            if (-not $alreadyLoaded) {
                $environmentLines.Add("$secretName=$($entry.Groups[2].Value)")
            }
        }
    }

    foreach ($secretName in @('POSTGRES_PASSWORD', 'TOKEN_PEPPER')) {
        $existingIndex = -1
        for ($index = 0; $index -lt $environmentLines.Count; $index++) {
            if ($environmentLines[$index] -match "^$secretName=") {
                $existingIndex = $index
                break
            }
        }
        if ($existingIndex -ge 0 -and $environmentLines[$existingIndex] -notmatch "^$secretName=$") {
            continue
        }

        $bytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $generator.GetBytes($bytes)
        } finally {
            $generator.Dispose()
        }

        $secretValue = [Convert]::ToHexString($bytes)
        if ($existingIndex -ge 0) {
            $environmentLines[$existingIndex] = "$secretName=$secretValue"
        } else {
            $environmentLines.Add("$secretName=$secretValue")
        }
    }
    [System.IO.File]::WriteAllLines($envFile, $environmentLines.ToArray(), [System.Text.Encoding]::ASCII)

    $compose = Join-Path $backendRoot 'compose.yaml'
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
                $content = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/content/landing' -TimeoutSec 5
                $authProtected = Test-HttpStatus -Uri 'http://127.0.0.1:8080/api/auth/me' -ExpectedStatus 401
                $purchasesProtected = Test-HttpStatus -Uri 'http://127.0.0.1:8080/api/purchases' -ExpectedStatus 401
                if ($page.StatusCode -eq 200 -and
                    $page.Content -match 'GART Gallery' -and
                    $api.StatusCode -eq 200 -and
                    $works.items.Count -gt 0 -and
                    $galleries.items.Count -gt 0 -and
                    $content.title -and
                    $authProtected -and
                    $purchasesProtected) {
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
        $fallbackContent = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/content/landing' -TimeoutSec 10
        $fallbackAuthProtected = Test-HttpStatus -Uri 'http://127.0.0.1:8080/api/auth/me' -ExpectedStatus 401
        $fallbackPurchasesProtected = Test-HttpStatus -Uri 'http://127.0.0.1:8080/api/purchases' -ExpectedStatus 401
        if ($fallbackWorks.items.Count -eq 0 -or
            $fallbackGalleries.items.Count -eq 0 -or
            -not $fallbackContent.title -or
            -not $fallbackAuthProtected -or
            -not $fallbackPurchasesProtected) {
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

    $evidenceDirectory = Join-Path $backendRoot 'evidence\docker'
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
        'GET /api/content/landing: HTTP 200'
        'GET /api/auth/me unauthenticated: HTTP 401'
        'GET /api/purchases unauthenticated: HTTP 401'
        ''
        '=== Failover ==='
        'The primary frontend was stopped temporarily; the main URL and both APIs continued to respond via the backup.'
        "GET /api/works?limit=4 during failover: HTTP 200 - $($fallbackWorks.items.Count) works"
        "GET /api/galleries during failover: HTTP 200 - $($fallbackGalleries.items.Count) galleries"
        'Content, Auth and Purchase routes remained reachable during failover.'
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
