# NYCUAA membercard system
A python server for issue and update nycuaa membercard

## Deploy
```
poetry install
eval $(poetry env activate)
python ./scripts/init_server.py
```

## API

**POST** `/api/newpass?govid=<govid>&name=<name>`  
request (json):
| field | value_type |
| ---- | ---------- |
| icon | string, icon image in base64 encoding |

resposne (text):
"success"