import urllib.request
import urllib.parse
import json
import time

# 1. Login
data = urllib.parse.urlencode({'username': 'admin@retailbi.com', 'password': 'Admin@123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(req) as res:
    token = json.loads(res.read().decode())['access_token']

print('1. Authenticated as Admin!')

# 2. Get ready dataset
req_ds = urllib.request.Request('http://127.0.0.1:8000/api/v1/datasets', headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req_ds) as res:
    data = json.loads(res.read().decode())
    datasets = data['data'] if isinstance(data, dict) and 'data' in data else data

ready_ds = [d for d in datasets if d['status'] == 'ready']
if not ready_ds:
    print('No ready dataset found!')
    exit(1)

dataset_id = ready_ds[0]['id']
print(f'2. Found Ready Dataset: {ready_ds[0]["original_filename"]} (ID: {dataset_id})')

# 3. Trigger Analysis
payload = json.dumps({'dataset_id': dataset_id, 'user_question': 'How can we increase profitability?'}).encode('utf-8')
req_run = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/analysis/run',
    data=payload,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
)

with urllib.request.urlopen(req_run) as res:
    run_info = json.loads(res.read().decode())
    print('3. Analysis Triggered:', run_info)
    analysis_id = run_info.get('analysis_id') or run_info.get('data', {}).get('analysis_id')

# 4. Poll status
print(f'4. Polling Analysis {analysis_id}...')
for i in range(25):
    time.sleep(1)
    req_status = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/analysis/{analysis_id}/status', headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req_status) as res:
        raw_st = json.loads(res.read().decode())
        st = raw_st.get('data') if isinstance(raw_st, dict) and 'data' in raw_st else raw_st
        print(f"  Step {i+1}: Status={st.get('status')}, Active={st.get('current_agent')}")
        if st.get('status') in ['completed', 'failed', 'verification_failed']:
            print(f"Final status reached: {st.get('status')}")
            break

# 5. Check report if completed
if st.get('status') == 'completed':
    req_rep = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/analysis/{analysis_id}/report', headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req_rep) as res:
        raw_rep = json.loads(res.read().decode())
        rep = raw_rep.get('data') if isinstance(raw_rep, dict) and 'data' in raw_rep else raw_rep
        print('5. Report Title:', rep.get('title'))
        print('   Verification Status:', rep.get('verification_status'))
        print('   Recommendations Count:', len(rep.get('recommendations', [])))
