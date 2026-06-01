param(
    [switch]$StartDockerDb,
    [switch]$GitAdd,
    [switch]$SkipRowCounts,
    [string]$DumpPath = "dataset\spm_postgres_dump.sql",
    [string]$DatabaseName = "",
    [string]$UserName = "",
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
        [string]$ResolvedUserName,
        [string]$ResolvedDatabaseName
    )

    Write-Step "Waiting for dockerized PostgreSQL to become healthy"

    if ($DryRun) {
        Write-Host "Dry run enabled, skipping readiness check." -ForegroundColor Yellow
        return
    }

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & docker compose exec -T db pg_isready -U $ResolvedUserName -d $ResolvedDatabaseName *> $null
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

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker command is not available. Start Docker Desktop first."
    }

    if (-not $UserName) {
        $UserName = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "spm" }
    }

    if (-not $DatabaseName) {
        $DatabaseName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "spm" }
    }

    if ($StartDockerDb) {
        Invoke-CheckedCommand -Description "Starting docker compose PostgreSQL service" -Command {
            docker compose up -d db
        }
    }

    Wait-ForDockerPostgres -ResolvedUserName $UserName -ResolvedDatabaseName $DatabaseName

    if (-not $SkipRowCounts) {
        Invoke-CheckedCommand -Description "Showing key table row counts before export" -Command {
            docker compose exec -T db psql -U $UserName -d $DatabaseName -c "SELECT 'users' AS table_name, count(*) FROM users UNION ALL SELECT 'reservations', count(*) FROM reservations UNION ALL SELECT 'notification_logs', count(*) FROM notification_logs UNION ALL SELECT 'study_rooms', count(*) FROM study_rooms UNION ALL SELECT 'seats', count(*) FROM seats;"
        }
    }

    $resolvedDumpPath = if ([System.IO.Path]::IsPathRooted($DumpPath)) {
        $DumpPath
    }
    else {
        Join-Path $projectRoot $DumpPath
    }

    $dumpDir = Split-Path -Parent $resolvedDumpPath
    $tmpDumpPath = "$resolvedDumpPath.tmp"

    if (-not (Test-Path -LiteralPath $dumpDir)) {
        New-Item -ItemType Directory -Path $dumpDir -Force | Out-Null
    }

    if (Test-Path -LiteralPath $tmpDumpPath) {
        Remove-Item -LiteralPath $tmpDumpPath -Force
    }

    Invoke-CheckedCommand -Description "Exporting PostgreSQL dump to temporary file" -Command {
        $cmd = 'docker compose exec -T db pg_dump -U "{0}" -d "{1}" --clean --if-exists > "{2}"' -f $UserName, $DatabaseName, $tmpDumpPath
        cmd.exe /d /c $cmd
    }

    if ($DryRun) {
        Write-Host ""
        Write-Host "Dry run completed. No dump file was changed." -ForegroundColor Yellow
        return
    }

    if ((Get-Item -LiteralPath $tmpDumpPath).Length -le 0) {
        Remove-Item -LiteralPath $tmpDumpPath -Force
        throw "pg_dump produced an empty file; keeping the previous dump unchanged."
    }

    Move-Item -LiteralPath $tmpDumpPath -Destination $resolvedDumpPath -Force

    $dumpItem = Get-Item -LiteralPath $resolvedDumpPath
    Write-Host ""
    Write-Host "PostgreSQL dump exported successfully." -ForegroundColor Green
    Write-Host "Path: $($dumpItem.FullName)"
    Write-Host "Size: $($dumpItem.Length) bytes"
    Write-Host "Updated: $($dumpItem.LastWriteTime)"

    if ($GitAdd) {
        Invoke-CheckedCommand -Description "Staging dump file" -Command {
            git add -- $resolvedDumpPath
        }
    }

    Write-Step "Git status for dump file"
    git status --short -- $resolvedDumpPath

    Write-Host ""
    Write-Host "Next local update commands:" -ForegroundColor Yellow
    Write-Host "  git add dataset\spm_postgres_dump.sql"
    Write-Host "  git commit -m `"Update PostgreSQL dataset dump`""
    Write-Host "  git push"
}
finally {
    if ((Test-Path -LiteralPath "variable:tmpDumpPath") -and $tmpDumpPath -and (Test-Path -LiteralPath $tmpDumpPath)) {
        Remove-Item -LiteralPath $tmpDumpPath -Force
    }
    Pop-Location
}
