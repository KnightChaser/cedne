# cedne
## A simplified copy of RoKRAT malware

### Project brief
`cedne` is a simple copy of implementing the LNK(Windows Link)-based system infiltration malware's technique, leveraging unintended PowerShell script inside the LNK file.
```
<PROJECT>
- /client
    - /dist
        - (compiled executable will be included...)
    - client.py
    - packaging.ps1
- /lnk
    - /asset
        - KnightShopOrderList.xlsx
    - /generate
        - lnkGenerator.py
    - /scripts
        - find.ps1
        - search.dat
- /server
    - server.py
.gitignore
README.md
requirements.txt
```

- `lnkGenerator.py` will generate the dummy file(binary file) and LNK file. Those two will become the payload for system infiltration.
    - I assume the dummy file and LNK file are located in the same directory somewhere in accessible Windows directory.
    - If LNK file is executed, it'll unpack the dummy file and drop benign(decoy) XLSX file in the current directory to fool victim. Other required files for further steps will be dropped in `$env:public` path.
    - After LNK file finishes data unpacking and ready to proceed the next step, it'll delete itself and dummy file to be clear.
- Previous stage will invoke `$env:public\find.ps1`, which invokes `$env:public\search.dat`(Actually a PowerShell script, but the extension is set to `.dat`.) by PowerShell execution block to pretend benign.
- `$env:public\search.dat` will automatically decrypt encrypted client program(`$env:public\c.exe.e`) and produce `$env:public\c.exe`, then execute the code.
    - It works as a reverse shell or a backdoor to the victim system.
    - Since now, the attacker can control the victim(PowerShell prompt to the victim will be available now)


> This repository's goal is to understand the major threat actors leveraging LNK as an infiltration means, so details may be abbreviated.