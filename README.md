# KefkaSaysSimulator

Basic mini game that simulates the Kefka Says phase in the Dancing Mad (Ultimate) raid encounter from Final Fantasy XIV.

Running:

```bash
# Make virtual environment
python -m venv env
# Use virtual environment so we don't pollute global python packages
source env/bin/activate
# Install pygame and pyinstaller
python -m pip install --no-cache-dir -r requirements.txt
# Run project
python sources/main.py

```

Building

```bash
# Must follow steps above to ensure virtual environment has the correct dependencies to buil to exe/binary with pyinstaller
# Ensure you are using virtual environment
source env/bin/activate
chmod +x build.sh
./build.sh
```
