import requests
import json

url = "http://www.gpts-cristiano.com/cristiano/googleApi"

headers = {
  'Content-Type': 'application/x-www-form-urlencoded'
}
payload = {
  "query": "李白有哪些代表作？"
}
response = requests.post(url, headers=headers, data=payload)

print(json.loads(response.text))