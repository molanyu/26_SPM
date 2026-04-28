param(
    [switch]$StartDockerDb,
    [switch]$SkipMigrations,
    [switch]$NoReload,
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 0,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
$envExampleFile = Join-Path $projectRoot ".env.example"

function Write-Step {
    param([string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Import-DotEnv {
    param([string]$Path)

    foreach ($rawLine in Get-Content -Path $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

function Ensure-EnvFile {
    if ((Test-Path -LiteralPath $envFile) -or -not (Test-Path -LiteralPath $envExampleFile)) {
        return
    }

    if ($DryRun) {
        Write-Host "Dry run enabled, would create .env from .env.example" -ForegroundColor Yellow
        return
    }

    Copy-Item -LiteralPath $envExampleFile -Destination $envFile -Force
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

function Invoke-CheckedCommand {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    Write-Step $Description

    if ($DryRun) {
        Write-Host "Dry run enabled, skipping command execution." -ForegroundColor Yellow
        return
    }

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Description"
    }
}

function Wait-ForDockerPostgres {
    param(
        [string]$UserName,
        [string]$DatabaseName
    )

    Write-Step "Waiting for dockerized PostgreSQL to become healthy"

    if ($DryRun) {
        Write-Host "Dry run enabled, skipping readiness check." -ForegroundColor Yellow
        return
    }

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & docker compose exec -T db pg_isready -U $UserName -d $DatabaseName *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready." -ForegroundColor Green
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "Dockerized PostgreSQL did not become ready within the expected time."
}

Push-Location $projectRoot

try {
    Ensure-EnvFile

    if (Test-Path -LiteralPath $envFile) {
        Import-DotEnv -Path $envFile
    }

    if (-not $env:DATABASE_URL) {
        throw "DATABASE_URL is required. Set it in .env or the current environment."
    }

    $resolvedPort = if ($PSBoundParameters.ContainsKey("Port") -and $Port -gt 0) {
        $Port
    }
    elseif ($env:APP_PORT) {
        [int]$env:APP_PORT
    }
    else {
        8000
    }

    if ($StartDockerDb) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "docker command is not available. Start Docker Desktop or provide an existing PostgreSQL instance instead."
        }

        $postgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "spm" }
        $postgresDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "spm" }

        Invoke-CheckedCommand -Description "Starting docker compose PostgreSQL service" -Command {
            docker compose up -d db
        }
        Wait-ForDockerPostgres -UserName $postgresUser -DatabaseName $postgresDb
    }

    if (-not $SkipMigrations) {
        Invoke-CheckedCommand -Description "Running Alembic migrations" -Command {
            python -m alembic upgrade head
        }
    }

    Write-Step "Launching backend"
    Write-Host "Host: $ListenHost"
    Write-Host "Port: $resolvedPort"
    Write-Host "Reload: $(-not $NoReload)"
    Write-Host "DATABASE_URL=$($env:DATABASE_URL)"
    Write-Host "NOTIFICATION_DEFAULT_CHANNEL=$($env:NOTIFICATION_DEFAULT_CHANNEL)"

    if ($DryRun) {
        Write-Host "Dry run enabled, skipping backend launch." -ForegroundColor Yellow
        return
    }

    $arguments = @("-m", "uvicorn", "app.main:app", "--host", $ListenHost, "--port", "$resolvedPort")
    if (-not $NoReload) {
        $arguments += "--reload"
    }

    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Backend exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
