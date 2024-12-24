# packaging.ps1
# Transforming the packaging script to a PowerShell script

Write-Host "Checking if PyInstaller is installed..."
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller is not installed. Installing it..."
    python -m pip install pyinstaller
}

# Get the directory where the script is located
$scriptDir = $PSScriptRoot

# Set the path to your Python3 script
$scriptPath = Join-Path $scriptDir "client.py"

# Ensure the script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "The script $scriptPath does not exist."
    exit 1
}

# Set the output directory
$outputDir = Join-Path $scriptDir "dist"

# Debugging: Print paths
Write-Host "Script Directory: $scriptDir"
Write-Host "Script Path:      $scriptPath"
Write-Host "Output Directory: $outputDir"

# Create the standalone executable and check
if (Test-Path $outputDir) {
    Write-Host "Deleting existing dist directory..."
    Remove-Item -Recurse -Force $outputDir
}
Write-Host "Converting $scriptPath into a standalone executable..."
pyinstaller --onefile --distpath $outputDir $scriptPath

$executablePath = Join-Path $outputDir "client.exe"

# Debugging: Print executable path
Write-Host "Executable Path: $executablePath"

if (Test-Path $executablePath) {
    Write-Host "The executable is successfully created at $executablePath"
    Write-Host "Deleting the automatically generated data..."
    Remove-Item -Recurse -Force (Join-Path $scriptDir "build")
    Remove-Item -Force (Join-Path $scriptDir "client.spec")
} else {
    Write-Host "Failed to create the executable."
    exit 1
}

# Make a copy, and encrypt with AES algorithm.
# Previous phase program will use this, and decrypt then run.
Write-Host "Encrypting a copy of executable..."

# Function to convert hex string to byte array
function Convert-HexStringToByteArray($hex) {
    $bytes = @()
    for ($i = 0; $i -lt $hex.Length; $i += 2) {
        $bytes += [Convert]::ToByte($hex.Substring($i, 2), 16)
    }
    return ,$bytes  # Ensure it's returned as a byte array
}

$encryptionKeyHex  = "6B6E69676874636861736572CAFECAFE"
$encryptionKey     = Convert-HexStringToByteArray $encryptionKeyHex

$aes               = [System.Security.Cryptography.Aes]::Create()
$aes.Key           = $encryptionKey
$aes.GenerateIV()   # Generate a randomly created IV (Initialization Vector)
$iv                = $aes.IV

# Define paths relative to the script's directory
$encryptedFilePath = Join-Path $outputDir "client_encrypted.exe"

Write-Host "Encrypted File Path: $encryptedFilePath"

Write-Host "Key: $($encryptionKey | ForEach-Object { $_.ToString("X2") })"
Write-Host "IV: $($iv | ForEach-Object { $_.ToString("X2") })"
Write-Host "Encrypting the executable..."

$encryptor         = $aes.CreateEncryptor()
try {
    $inputFileStream   = [System.IO.File]::OpenRead($executablePath)
    $outputFileStream  = [System.IO.File]::Create($encryptedFilePath)
    $cryptoStream      = New-Object System.Security.Cryptography.CryptoStream($outputFileStream, $encryptor, [System.Security.Cryptography.CryptoStreamMode]::Write)

    # Write the IV to the output file first, which is needed for decryption
    $outputFileStream.Write($iv, 0, $iv.Length)

    # Define a buffer size (e.g., 4KB)
    $bufferSize = 4096
    $buffer = New-Object byte[] $bufferSize
    while (($bytesRead = $inputFileStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $cryptoStream.Write($buffer, 0, $bytesRead)
    }

    $cryptoStream.Close()
    $inputFileStream.Close()
    $outputFileStream.Close()
    Write-Host "The encrypted executable is successfully created at $encryptedFilePath"
} catch {
    Write-Host "An error occurred during encryption: $_"
    exit 1
}
