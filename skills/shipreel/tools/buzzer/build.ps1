# Builds buzzer.exe with the C# compiler that ships with Windows (.NET Framework 4.x). No SDK download.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
& $csc /nologo /optimize+ /target:winexe "/out:$here\buzzer.exe" /r:System.Windows.Forms.dll /r:System.Drawing.dll "$here\Buzzer.cs"
if ($LASTEXITCODE -ne 0) { throw "csc failed" }
Write-Output "built $here\buzzer.exe"
