Write-Host "Exporting production dependencies" -ForegroundColor Green
python -m poetry export --without dev -f requirements.txt --output requirements-prod.txt --without-hashes

Write-Host "Exporting dev dependencies..." -ForegroundColor Blue
python -m poetry export --with dev -f requirements.txt --output requirements-dev.txt --without-hashes

Write-Host "Files created:" -ForegroundColor Green
Get-ChildItem requirements-*.txt

Write-Host "Production dependencies count:" -ForegroundColor Yellow
if (Test-Path requirements-prod.txt) {
    (Get-Content requirements-prod.txt).Count
}

Write-Host "Dev dependencies count:" -ForegroundColor Yellow
if (Test-Path requirements-dev.txt) {
    (Get-Content requirements-dev.txt).Count
}

Write-Host "First 5 lines of production requirements:" -ForegroundColor Cyan
if (Test-Path requirements-prod.txt) {
    Get-Content requirements-prod.txt | Select-Object -First 5
}

Write-Host "Looking for pytest in dev file:" -ForegroundColor Cyan
if (Test-Path requirements-dev.txt) {
    Select-String -Path requirements-dev.txt -Pattern "pytest"
}
