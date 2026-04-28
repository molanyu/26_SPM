param(
    [switch]$StartDockerDb,
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

    if (-not $env:POSTGRES_REGRESSION_URL) {
        Set-Item -Path "Env:POSTGRES_REGRESSION_URL" -Value $env:DATABASE_URL
    }

    Set-Item -Path "Env:DATABASE_AUTO_CREATE" -Value "false"

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

    Invoke-CheckedCommand -Description "Running Alembic migrations against PostgreSQL" -Command {
        python -m alembic upgrade head
    }

    Invoke-CheckedCommand -Description "Running PostgreSQL smoke suite" -Command {
        python run_tests.py --suite postgres
    }

    Write-Host ""
    Write-Host "PostgreSQL acceptance checks completed successfully." -ForegroundColor Green
    Write-Host "DATABASE_URL=$($env:DATABASE_URL)"
    Write-Host "POSTGRES_REGRESSION_URL=$($env:POSTGRES_REGRESSION_URL)"
}
finally {
    Pop-Location
}
