<#
.SYNOPSIS
  Единая точка входа для задач проекта ELMA_Connector.
.DESCRIPTION
  Использование:
    .\scripts\run.ps1 help          — справка
    .\scripts\run.ps1 load          — загрузить все данные из ELMA
    .\scripts\run.ps1 load users    — загрузить только users
    .\scripts\run.ps1 build         — пересобрать обработанные данные
    .\scripts\run.ps1 check         — запустить все проверки
    .\scripts\run.ps1 check users   — проверить только users
#>

param(
  [string]$Command = "help",
  [string]$Target = ""
)

$root = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $root "scripts"
$python = "python"

function Run {
  param([string]$Path, [string]$ArgList = "")
  $full = Join-Path $scripts $Path
  if ($ArgList) {
    & $python $full $ArgList
  } else {
    & $python $full
  }
}

switch ($Command.ToLower()) {
  "help" {
    Write-Host @"

  .\scripts\run.ps1 load              — загрузить все данные
  .\scripts\run.ps1 load <entity>     — загрузить конкретную сущность
  .\scripts\run.ps1 build             — пересобрать данные
  .\scripts\run.ps1 analyze           — анализ данных
  .\scripts\run.ps1 check             — все проверки
  .\scripts\run.ps1 check <name>      — конкретная проверка (users, data, coverage, fields, utf8)
  .\scripts\run.ps1 watch             — проверить изменения: новые поля и записи
  .\scripts\run.ps1 gantt             — інтерактивный выбор объекта и формирование графика
  .\scripts\run.ps1 gantt --object XXX  — сразу сформировать график для объекта
  .\scripts\run.ps1 html              — проверить HTML дашборда
  .\scripts\run.ps1 list              — список доступных сущностей для загрузки

"@
  }

  "load" {
    if ($Target) {
      Run "load\load_data.py" $Target
    } else {
      Run "load\load_data.py"
    }
    Write-Host "`nПроверка изменений..."
    Run "check\check_changes.py"
  }

  "build" {
    Run "process\build_data.py"
  }

  "analyze" {
    Run "process\analyze_data.py"
  }

  "check" {
    switch ($Target.ToLower()) {
      "users"    { Run "check\check_users.py" }
      "data"     { Run "check\check_data.py" }
      "coverage" { Run "check\check_coverage.py" }
      "fields"   { Run "check\check_fields.py"; Run "check\check_fields2.py" }
      "utf8"     { Run "check\check_utf8.py" }
      default    {
        Run "check\check_users.py"
        Run "check\check_data.py"
        Run "check\check_coverage.py"
        Run "check\check_utf8.py"
      }
    }
  }

  "watch" {
    Run "check\check_changes.py"
  }

  "html" {
    Run "check\check_html.py"
  }

  "gantt" {
    $argsList = if ($Target) { $Target } else { "" }
    Run "process\vitrage_gantt.py" $argsList
  }

  "list" {
    Run "load\_list_entities.py"
  }

  default {
    Write-Host "Неизвестная команда: $Command"
    Write-Host "  Используйте: .\scripts\run.ps1 help"
  }
}
