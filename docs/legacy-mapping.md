# Legacy code migration map

The original prototype remains outside this repository as a local backup. Its functionality was consolidated as follows:

| Original file/group | New module or command |
| --- | --- |
| `main.py`, `windowtest.py`, `test icon.py` | `door_guardian.gui` |
| `data_collection.py` | `door-guardian collect` and `door_guardian.face.FaceService.collect` |
| `training.py` | `door-guardian train` and `FaceService.train` |
| `face_recognition.py` | `door-guardian recognize` and `FaceService.recognize` |
| `email_test.py` | `door_guardian.notifier` with environment-only credentials |
| `tts.py`, `untils/tts1.py` | `door_guardian.speech` using optional offline TTS |
| `weather_forecast.py`, `voice_test.py` | `door_guardian.weather`; no Excel or web scraping |
| `record01.py`, `untils/voiceMonitor*.py`, `app.py` | Removed from the production path; microphone/cloud credentials are no longer required |
| plaintext global password | `door_guardian.access` with salted PBKDF2 hashing |
| `record.txt` | private JSON Lines audit log in `data/events.jsonl` |

No original credential, face image, trained model, personal email address, or absolute workstation path is included in the reorganized repository.

