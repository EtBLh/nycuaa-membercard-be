# NYCUAA membercard system
A python server for managing nycuaa membercard, it handles:
- issue membercard
- [DOING] qrcode check-in for member conference 
- [TODO] admin panel: 
  - view check-in history and 
  - add member data to database
  - update membercard

## Requirement

- OS: ubuntu | debian
- python3
- poetry (manage python enviroment and packages)

## Deploy
```
poetry install
eval $(poetry env activate)
python ./scripts/init_server.py
```

## API list

### Unauth API

**POST** `/api/login`   

Description: login with member's govid and name, a email will sent to member's email addr afterward, after entering the otp code in email, member will log in successfully.

request (json):
| field | value_type |
| ---- | ---------- |
| name | string |
| govid | string |

resposne (json) 200:  
| field | value_type |
| ---- | ---------- |
| message | "otp code sent" |
| email | "hello****@gamil.com" |

--------

**POST** `/api/otp_verify`  
Description: verify the otp code in email, the access token, alongside with member data will sent to frontend as response

request (json):
| field | value_type |
| ---- | ---------- |
| code | string |

resposne (json):
| field | value_type |
| ---- | ---------- |
| token | string |
| name | string |
| id | string |
| email | string |
| govid | string |

--------

### Authed API
Api below need authorization, please make sure you have a header in your request

| field | value_type |
| ---- | ---------- |
| Authorization | "Bearer <the_token>" |

--------

**POST** `/api/member/check_token`  
Description: check is the token valid

**for valid token**

resposne (JSON) 200:
| field | value_type |
| ---- | ---------- |
| valid | true |

**for invalid token**

resposne (JSON) 401:
| field | value_type |
| ---- | ---------- |
| valid | true |


--------

**POST** `/api/member/pass`  
Description: Issue a new pass for the current logged in member

resposne (JSON) 200:
| field | value_type |
| ---- | ---------- |
| status | 'success' |

--------

**GET** `/api/member/pass`  
Description: get the member pkpass files if exists

resposne (file) 200: the pkpass file
response 

--------

**PUT** `/api/member/icon`  
Description: upload the member icon

request (form_data):
| field | value_type |
| ---- | ---------- |
| file | the icon file(.jpg, .jpeg, .png, .gif) |

resposne (json) 200:
| field | value_type |
| ---- | ---------- |
| message | 'Icon uploaded successfully' |

--------

**GET** `/api/member/icon`  
Description: get the member icon  

request: none  

resposne (file) 200: the member's icon  

--------

## API for Admin privilege

**POST** `/api/check-in/:qrcode`  
Description: check in for member conference using member qrcode, need admin privilege

resposne (json):
| field | value_type |
| ---- | ---------- |
| name | string |

--------