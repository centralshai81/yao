import requests
#测试获取对话消息列表接口
session = requests.Session()
session.post('http://localhost:5000/api/login', json={'username': 'testuser', 'password': 'testuser'})
resp = session.get('http://localhost:5000/api/conversations/12/messages')
print('Messages:', resp.json())
