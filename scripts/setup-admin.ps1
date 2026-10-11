# Makes the owner's admin code for Khabar and stores it as the ADMIN_KEY secret on GitHub.
# The code is shown only here, in this window: type it into the app on your phone (hold the Khabar logo for two
# seconds). Run the script again to make a new code; the old one stops working at once.
$ErrorActionPreference = 'Stop'
$alphabet = 'abcdefghjkmnpqrstuvwxyz23456789'   # no 0/o, 1/l/i: easy to type on a phone
$bytes = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)   # works in Windows PowerShell 5 too
$chars = $bytes | ForEach-Object { $alphabet[$_ % $alphabet.Length] }
$code = (0..3 | ForEach-Object { -join $chars[($_ * 4)..($_ * 4 + 3)] }) -join '-'

$code | gh secret set ADMIN_KEY --repo aram313/nyhedsradar
if ($LASTEXITCODE -ne 0) { throw 'Could not save the code on GitHub (is gh logged in?)' }

Write-Host ''
Write-Host 'Din admin-kode til Khabar:' -ForegroundColor Green
Write-Host ''
Write-Host "    $code" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Paa telefonen: aabn Khabar, hold logoet nede i 1,5 sekund og skriv koden.'
Write-Host 'Derefter: hold en nyhed nede for at fjerne eller flytte den.'
Write-Host 'Luk dette vindue bagefter, og del ikke koden med nogen.'
