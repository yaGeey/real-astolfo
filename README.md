!! You need config files for it to work right now. Put `Астольфік.exe` in the parent directory after clonning the repo.

building from source
```
uv sync
uvx pyinstaller --noconfirm --onefile --windowed --icon ".\public\astlofo4.ico" --name "Астольфік" "astolfo.py"
```