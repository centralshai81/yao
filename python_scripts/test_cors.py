import requests
#测试跨域（CORS）配置是否正常
resp = requests.get('http://localhost:5000/api/knowledge/list', headers={'Origin': 'http://127.0.0.1:5000'})
print('Allow-Origin:', resp.headers.get('Access-Control-Allow-Origin'))
print('Allow-Credentials:', resp.headers.get('Access-Control-Allow-Credentials'))
