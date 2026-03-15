import requests
import json

url = "http://localhost:8000/upload"
headers = {"X-Tenant-ID": "1"}
files = {"file": open("test_image.jpg", "rb")}

try:
    response = requests.post(url, headers=headers, files=files)
    print("STATUS:", response.status_code)
    print("JSON:", json.dumps(response.json(), indent=2))
except Exception as e:
    print("ERROR:", str(e))
