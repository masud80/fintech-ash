@echo off
set GOOGLE_APPLICATION_CREDENTIALS=C:\Projects\multi-agent\financial-analysis\fintech\serviceAccountKey.json
python -m fintech.validate_firestore
pause 