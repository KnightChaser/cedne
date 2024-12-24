# packaging.ps1
# Transforming the packaging script to a PowerShell script

Write-Host "Checking if PyInstaller is installed..."
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller is not installed. Installing it..."
    python -m pip install pyinstaller
}

# Set the path to your Python3 script
$scriptPath = "./client.py"

# Ensure the script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "The script $scriptPath does not exist."
    exit 1
}

# Create the standalone executable and check
$outputDir = "./dist"
if (Test-Path $outputDir) {
    Write-Host "Deleting existing dist directory..."
    Remove-Item -Recurse -Force $outputDir
}
Write-Host "Converting $scriptPath into a standalone executable..."
pyinstaller --onefile --distpath $outputDir $scriptPath

if (Test-Path "$outputDir/client.exe") {
    Write-Host "The executable is successfully created at $outputDir/client.exe"
    Write-Host "Deleting the automatically generated data..."
    Remove-Item -Recurse -Force "./build"
    Remove-Item -Force client.spec
} else {
    Write-Host "Failed to create the executable."
    exit 1
}