# NYCUAA membercard system
A python server for managing nycuaa membercard, it handles:
- issue membercard
- [DOING] qrcode check-in for member conference 
- [TODO] admin panel: 
  - view check-in history and 
  - add member data to database
  - update membercard

## Deploy
```
poetry install
eval $(poetry env activate)
python ./scripts/init_server.py
```

## API

**POST** `/api/newpass?govid=<govid>&name=<name>`  
Description: Issue a new pass for the current loged in member

request (json):
| field | value_type |
| ---- | ---------- |
| icon | string, icon image in base64 encoding |

resposne (text):
"success"  
  
*todo: this should be changed to checking token instead of govid and name*

### to be implement

**POST** `/api/check-in/:qrcode`  
Description: check in for member conference using member qrcode, need admin privilege

request (json):
| field | value_type |
| ---- | ---------- |
| token | string |

resposne (json):
| field | value_type |
| ---- | ---------- |
| name | string |

**POST** `/api/newpass`  
Description: Issue a new pass for the current loged in member

request (json):
| field | value_type |
| ---- | ---------- |
| token | string |
| icon | string, icon image in base64 encoding |

resposne (text):
"success"  

**POST** `/api/login`  
Description: login with member's govid and name, a email will sent to member's email addr afterward, after clicking the url in email, member will log in successfully.

request (json):
| field | value_type |
| ---- | ---------- |
| name | string |
| govid | string |

resposne (text):
"success"

**POST** `/api/validate_email_token`  
Description: after clicking the url in email, the newly entered web page will use this api to validate the email_token(as a url param), and eventually fetch a real token 

request (json):
| field | value_type |
| ---- | ---------- |
| email_token | string |

resposne (json):
| field | value_type |
| ---- | ---------- |
| token | string |