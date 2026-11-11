$apiBase = 'http://localhost:8000'
$demoProject = Invoke-RestMethod -Method Post -Uri "$apiBase/projects" -ContentType 'application/json' -Body '{"name":"API demo"}'
$demoAuth = @{ Authorization = "Bearer $($demoProject.api_key)" }
$demoRun = Invoke-RestMethod -Method Post -Uri "$apiBase/runs" -Headers $demoAuth -ContentType 'application/json' -Body '{"name":"Example run"}'
$demoBatch = @{
    batch_id = [guid]::NewGuid().ToString()
    events = @(@{
        event_id = [guid]::NewGuid().ToString()
        metric = 'loss'; step = 1; value = 0.5
        occurred_at = '2026-01-01T00:00:00Z'
    })
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri "$apiBase/runs/$($demoRun.id)/metrics" -Headers $demoAuth -ContentType 'application/json' -Body $demoBatch
# Identical retry: same receipt, no extra events.
Invoke-RestMethod -Method Post -Uri "$apiBase/runs/$($demoRun.id)/metrics" -Headers $demoAuth -ContentType 'application/json' -Body $demoBatch
Invoke-RestMethod -Uri "$apiBase/runs/$($demoRun.id)" -Headers $demoAuth
Remove-Variable demoProject,demoAuth
