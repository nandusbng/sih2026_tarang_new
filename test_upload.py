import requests

url = 'http://localhost:3000/api/v1/xtf/upload'
filepath = 'tarang_synthetic_survey_001.xtf'

with open(filepath, 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files)
    
print("Status Code:", response.status_code)
try:
    print("JSON:", response.json())
except:
    print("Response text:", response.text)
