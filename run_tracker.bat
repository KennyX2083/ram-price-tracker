@echo off

cd /d "C:\Users\jerry\OneDrive\Desktop\Documents\VS Code\python-shit\ram-tracker-project"

echo ========================================== >> data\tracker.log
echo Run started: %date% %time% >> data\tracker.log

call .venv\Scripts\activate.bat

python main.py >> data\tracker.log 2>&1

echo Run finished: %date% %time% >> data\tracker.log

deactivate