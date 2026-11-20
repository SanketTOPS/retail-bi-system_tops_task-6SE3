import urllib.request
import urllib.parse
import json

# 1. Login
data = urllib.parse.urlencode({'username': 'admin@retailbi.com', 'password': 'Admin@123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(req) as res:
    token = json.loads(res.read().decode())['access_token']

print('Token acquired!')

# 2. Upload file
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
file_path = r'c:\Users\Admin\Desktop\AI_Task\Six_Industry_CrewAI_Datasets\03_Retail.xlsx'
with open(file_path, 'rb') as f:
    file_bytes = f.read()

part1 = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="03_Retail.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'.encode('utf-8')
part2 = f'\r\n--{boundary}--\r\n'.encode('utf-8')
body = part1 + file_bytes + part2

req2 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/datasets/upload',
    data=body,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    }
)

try:
    with urllib.request.urlopen(req2) as res2:
        print('Upload response code:', res2.status)
        print(res2.read().decode()[:400])
except urllib.error.HTTPError as e:
    print('Upload FAILED HTTP:', e.code, e.read().decode())
except Exception as e:
    print('Upload FAILED EXCEPTION:', type(e), e)
