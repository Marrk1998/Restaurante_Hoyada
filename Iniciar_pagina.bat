@echo off
setlocal
cd /d "%~dp0"

start "" /b powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "$root='%~dp0'; $url='http://127.0.0.1:5000/'; $ready=$false; try { $response=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; $ready=($response.StatusCode -eq 200) } catch {}; if (-not $ready) { $python=Join-Path $root '.venv\Scripts\pythonw.exe'; if (-not (Test-Path $python)) { Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('No se encontro el entorno virtual. Ejecuta la instalacion del proyecto primero.','Restaurante La Hoyada') | Out-Null; exit 1 }; Start-Process -FilePath $python -ArgumentList 'app.py' -WorkingDirectory $root; for ($i=0; $i -lt 30 -and -not $ready; $i++) { Start-Sleep -Seconds 1; try { $response=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; $ready=($response.StatusCode -eq 200) } catch {} } }; if ($ready) { Start-Process $url } else { Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('No se pudo iniciar la pagina. Comprueba que el puerto 5000 este disponible.','Restaurante La Hoyada') | Out-Null }"

exit /b
