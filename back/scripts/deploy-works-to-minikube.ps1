$ErrorActionPreference = 'Stop'

$backendRoot = Split-Path -Parent $PSScriptRoot

function Resolve-Executable {
    param(
        [string]$Name,
        [string[]]$FallbackPaths
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    foreach ($path in $FallbackPaths) {
        if (Test-Path -LiteralPath $path) {
            return $path
        }
    }

    throw "$Name no está instalado o no está disponible en PATH."
}

$docker = Resolve-Executable 'docker' @(
    'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
)
$kubectl = Resolve-Executable 'kubectl' @(
    'C:\Program Files\Docker\Docker\resources\bin\kubectl.exe'
)
$minikube = Resolve-Executable 'minikube' @(
    'C:\Program Files\Kubernetes\Minikube\minikube.exe'
)

$status = & $minikube status --output=json 2>$null
$minikubeRunning = $LASTEXITCODE -eq 0 -and
    ($status | ConvertFrom-Json).Host -eq 'Running'
if (-not $minikubeRunning) {
    & $minikube start --driver=docker --cpus=2 --memory=2048
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo iniciar Minikube.'
    }
}

& $kubectl wait --for=condition=Ready node/minikube --timeout=180s
if ($LASTEXITCODE -ne 0) {
    throw 'El nodo de Minikube no quedó listo.'
}

Push-Location $backendRoot
try {
    & $docker build -f services/works-service/Dockerfile -t gart-gallery-works:local .
    if ($LASTEXITCODE -ne 0) {
        throw 'Falló la construcción de la imagen del servicio Works.'
    }
} finally {
    Pop-Location
}

& $minikube image load gart-gallery-works:local
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo cargar la imagen de Works en Minikube.'
}

& $kubectl create namespace gart-gallery --dry-run=client -o yaml |
    & $kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo crear o verificar el namespace gart-gallery.'
}

$secretExists = & $kubectl get secret works-postgres-env -n gart-gallery 2>$null
if ($LASTEXITCODE -ne 0) {
    $randomBytes = New-Object byte[] 24
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($randomBytes)
    } finally {
        $random.Dispose()
    }

    $password = [Convert]::ToBase64String($randomBytes).
        TrimEnd('=').
        Replace('+', 'a').
        Replace('/', 'b')
    $secretArguments = @(
        'create', 'secret', 'generic', 'works-postgres-env',
        '-n', 'gart-gallery',
        '--from-literal=POSTGRES_DB=gart_gallery',
        '--from-literal=POSTGRES_USER=works',
        "--from-literal=POSTGRES_PASSWORD=$password",
        "--from-literal=DATABASE_URL=postgresql://works:$password@works-postgres:5432/gart_gallery",
        '--dry-run=client', '-o', 'yaml'
    )
    & $kubectl @secretArguments | & $kubectl apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo crear el Secret local para PostgreSQL.'
    }
}

& $kubectl apply -f (Join-Path $backendRoot 'deploy\kubernetes\works-service.yaml')
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron aplicar los recursos de Works y PostgreSQL.'
}

& $kubectl rollout status statefulset/works-postgres -n gart-gallery --timeout=180s
if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL no quedó listo.'
}

& $kubectl rollout status deployment/works-service -n gart-gallery --timeout=180s
if ($LASTEXITCODE -ne 0) {
    throw 'El servicio Works no quedó listo.'
}

& $kubectl get pods,services,persistentvolumeclaims -n gart-gallery -o wide
