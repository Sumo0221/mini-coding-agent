$ErrorActionPreference = 'Continue'
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8888/search?q=test&format=json" -TimeoutSec 5
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content (first 300 chars): $($response.Content.Substring(0, [Math]::Min(300, $response.Content.Length)))"
} catch {
    Write-Host "Error: $_"
}
