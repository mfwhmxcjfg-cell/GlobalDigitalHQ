$uri = 'http://127.0.0.1:8824/'
for ($i = 0; $i -lt 25; $i++) {
    try {
        $null = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        Start-Process $uri
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
}
Write-Host 'Le serveur local ne repond pas encore. Ouvrir http://127.0.0.1:8824/ manuellement.'
exit 1
