' Temporary 5-minute clock for Nabd while QStash is not set up yet.
' Windows Task Scheduler ("Nabd vaekkeur") runs this every 5 minutes; it starts the radar workflow on
' GitHub with the PC's existing GitHub login, in a hidden window, and logs the result.
Set sh = CreateObject("WScript.Shell")
logFile = "E:\Alpha\projects\nyhedsradar\.cache\pc-clock.log"
cmd = "cmd /c echo %date% %time% >> """ & logFile & """ && ""C:\Program Files\GitHub CLI\gh.exe"" workflow run radar.yml -R aram313/nyhedsradar >> """ & logFile & """ 2>&1"
sh.Run cmd, 0, True
