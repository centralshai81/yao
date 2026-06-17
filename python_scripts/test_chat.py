import requests
#测试流式对话接口
session = requests.Session()
session.post('http://localhost:5000/api/login', json={'username': 'testuser', 'password': 'testuser'})

resp = session.post('http://localhost:5000/api/conversations/12/send_stream', json={'content': 'Hello'})
print('Status:', resp.status_code)
for line in resp.iter_lines():
    if line:
        print(line.decode('utf-8'))
