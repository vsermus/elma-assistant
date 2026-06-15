@echo off
chcp 1251 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   Демо — График витражей ELMA
echo ============================================
echo.

rem Проверяем Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
  echo   Запуск на Python...
  python -m http.server 8000 --bind 127.0.0.1
  pause
  exit /b
)

echo   Python не найден, запускаем встроенный сервер...
echo.
echo   Откройте: http://127.0.0.1:8000
echo   Закройте окно для остановки
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$port=8000; ^
$root=Resolve-Path '.'; ^
$mime=@{'.html'='text/html;charset=utf-8';'.js'='application/javascript';'.json'='application/json';'.css'='text/css';'.png'='image/png';'.ico'='image/x-icon'}; ^
$l=New-Object System.Net.HttpListener; ^
$l.Prefixes.Add('http://127.0.0.1:'+$port+'/'); ^
try{$l.Start()}catch{Write-Host 'Ошибка:' $_;pause;exit}; ^
Write-Host ('  Сервер запущен на http://127.0.0.1:'+$port); ^
try{Start-Process 'http://127.0.0.1:'+$port}catch{}; ^
while($l.IsListening){ ^
  $c=$l.GetContext(); ^
  $p=$c.Request.Url.LocalPath.TrimStart('/'); ^
  if(!$p){$p='index.html'}; ^
  $f=Join-Path $root $p; ^
  if(Test-Path $f -PathType Leaf){ ^
    $e=[IO.Path]::GetExtension($f); ^
    $t=[string]$mime[$e]; ^
    if(!$t){$t='application/octet-stream'}; ^
    $c.Response.ContentType=$t; ^
    $b=[IO.File]::ReadAllBytes($f); ^
    $c.Response.ContentLength64=$b.Length; ^
    $c.Response.OutputStream.Write($b,0,$b.Length); ^
    $c.Response.OutputStream.Close() ^
  }else{ ^
    $c.Response.StatusCode=404; ^
    $c.Response.Close() ^
  } ^
}
