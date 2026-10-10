# Sets up the 5-minute clock for Nabd: an Upstash QStash schedule that starts the radar workflow on GitHub.
# The owner runs this himself and pastes the keys when asked; they are sent only to GitHub and Upstash
# and are never written to disk or shown on screen.
$ErrorActionPreference = 'Stop'
$repo = 'aram313/nyhedsradar'
$dispatch = "https://api.github.com/repos/$repo/actions/workflows/radar.yml/dispatches"

Write-Host ''
Write-Host 'Nabd – opsætning af vækkeur' -ForegroundColor Red
Write-Host ''

$gh = Read-Host -AsSecureString '1/3  Indsæt din GitHub-nøgle (den du lige har lavet)'
$ghToken = (ConvertFrom-SecureString $gh -AsPlainText).Trim()

Write-Host '     Tester GitHub-nøglen ...'
try {
    Invoke-RestMethod -Method Post -Uri $dispatch -ContentType 'application/json' -Body '{"ref":"main"}' -Headers @{
        Authorization = "Bearer $ghToken"; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28'
    } | Out-Null
    Write-Host '     OK – nøglen virker, og radaren er lige blevet startet.' -ForegroundColor Green
} catch {
    Write-Host '     GitHub sagde nej. Tjek at nøglen har adgang til "nyhedsradar" og "Actions: Read and write".' -ForegroundColor Yellow
    Write-Host "     ($($_.Exception.Message))"
    exit 1
}

$url = (Read-Host '2/3  Indsæt QSTASH_URL fra Upstash (fx https://qstash-eu-central-1.upstash.io)').Trim().TrimEnd('/')
if (-not $url) { $url = 'https://qstash-eu-central-1.upstash.io' }
$qs = Read-Host -AsSecureString '3/3  Indsæt QSTASH_TOKEN fra Upstash'
$qsToken = (ConvertFrom-SecureString $qs -AsPlainText).Trim()

Write-Host '     Opretter vækkeuret (hvert 5. minut) ...'
try {
    $res = Invoke-RestMethod -Method Post -Uri "$url/v2/schedules/$dispatch" -ContentType 'application/json' -Body '{"ref":"main"}' -Headers @{
        Authorization                          = "Bearer $qsToken"
        'Upstash-Cron'                         = '*/5 * * * *'
        'Upstash-Method'                       = 'POST'
        'Upstash-Retries'                      = '0'
        'Upstash-Schedule-Id'                  = 'nabd-radar'
        'Upstash-Forward-Authorization'        = "Bearer $ghToken"
        'Upstash-Forward-Accept'               = 'application/vnd.github+json'
        'Upstash-Forward-X-GitHub-Api-Version' = '2022-11-28'
    }
    Write-Host "     Færdig! Vækkeuret kører nu hvert 5. minut (id: $($res.scheduleId))." -ForegroundColor Green
    Write-Host '     Du kan lukke dette vindue og sige til Claude, at det er gjort.'
} catch {
    Write-Host '     Upstash sagde nej. Tjek at QSTASH_URL og QSTASH_TOKEN er kopieret rigtigt.' -ForegroundColor Yellow
    Write-Host "     ($($_.Exception.Message))"
    exit 1
}
