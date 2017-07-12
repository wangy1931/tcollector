# delete service if it already exists
if (Get-Service winlogbeatd -ErrorAction SilentlyContinue) {
  $service = Get-WmiObject -Class Win32_Service -Filter "name='winlogbeatd'"
  $service.StopService()
  Start-Sleep -s 1
  $service.delete()
}

$workdir = Split-Path $MyInvocation.MyCommand.Path

# create new service
New-Service -name winlogbeatd `
  -displayName winlogbeatd `
  -binaryPathName "`"$workdir\\winlogbeat.exe`" -c `"$workdir\\winlogbeat.yml`" -path.home `"$workdir`" -path.data `"C:\\ProgramData\\winlogbeat`""

 if (Get-Service winlogbeatd -ErrorAction SilentlyContinue) {
    net start  winlogbeatd
}