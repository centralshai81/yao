import requests
# 综合测试用户注册、登录、会话列表、创建会话等基础接口
session = requests.Session()

# register注册
reg_resp = session.post('http://localhost:5000/api/register', json={
    'username': 'testuser',
    'password': 'testuser',
    'email': 'testuser@test.com'
})
print('Register:', reg_resp.json())

# login登录
login_resp = session.post('http://localhost:5000/api/login', json={
    'username': 'testuser',
    'password': 'testuser'
})
print('Login:', login_resp.json())

# get conversations获取会话列表
conv_resp = session.get('http://localhost:5000/api/conversations/list')
print('Conversations:', conv_resp.text)

# create conversation创建会话
create_resp = session.post('http://localhost:5000/api/conversations/create', json={
    'title': 'test conv',
    'type': 'qa'
})
print('Create Conv:', create_resp.json())

conv_resp2 = session.get('http://localhost:5000/api/conversations/list')
print('Conversations after create:', conv_resp2.text)

