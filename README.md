One of my first coding projects. The first line of code was written on 24.11.2023. It serves as an everyday helper for my daily routine - the most useful feature is automatically switching my laptop to the eco power plan whenever I go AFK, preventing it from sucking in dust.

!! Note: You need config files for it to work. After cloning the repo, place `Астольфік.exe` in the parent directory.

### building from source:
```
uv sync
uvx pyinstaller --noconfirm --onefile --windowed --icon ".\public\astlofo4.ico" --name "Астольфік" "astolfo.py"
```