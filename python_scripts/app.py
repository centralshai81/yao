# -*- coding: utf-8 -*-
"""
储能并网检测知识问答系统 - Flask后端API
"""
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import pymysql
import hashlib
import json
from datetime import datetime, timedelta
import os
import requests
import time
import uuid
from werkzeug.utils import secure_filename
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set base dir to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
FRONTEND_DIST_DIR = os.path.join(FRONTEND_DIR, 'dist')

app = Flask(__name__)
app.secret_key = 'energy_storage_qa_secret_key_2024'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}}, allow_headers="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.before_request
def handle_preflight():
    """全局处理OPTIONS预检请求，确保返回200 OK状态码"""
    if request.method == 'OPTIONS':
        return '', 200

# ==================== 扣子(Coze) API配置 ====================
COZE_API_BASE = 'https://api.coze.cn'
COZE_API_TOKEN_DEFAULT = 'pat_y2eb1WyhDZi57vSGeKKdHITn4P3V8x13IvPOWaIXQImG0JzPedgq2FRCBui44Ezg'

def get_coze_token():
    """从数据库获取扣子API Token，回退到默认值"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_api_token'")
            row = cursor.fetchone()
            token = row.get('config_value', '') if row else ''
        conn.close()
        return token if token else COZE_API_TOKEN_DEFAULT
    except:
        return COZE_API_TOKEN_DEFAULT

def coze_headers():
    """获取扣子API请求头"""
    token = get_coze_token()
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Agw-Js-Conv': 'str'
    }

def coze_request(method, path, **kwargs):
    """发送扣子API请求"""
    url = f'{COZE_API_BASE}{path}'
    headers = kwargs.pop('headers', coze_headers())
    try:
        resp = requests.request(method, url, headers=headers, timeout=30, verify=True, **kwargs)
        result = resp.json()
        try:
            print(f'[Coze API] {method} {path} -> status={resp.status_code}, code={result.get("code")}')
        except Exception:
            pass
        return result
    except requests.exceptions.SSLError as e:
        try:
            print(f'[Coze API SSL Error] {method} {path}: {e}')
        except Exception:
            pass
        # SSL验证失败时自动重试，跳过验证
        try:
            resp = requests.request(method, url, headers=headers, timeout=30, verify=False, **kwargs)
            result = resp.json()
            try:
                print(f'[Coze API] (skip verify) {method} {path} -> status={resp.status_code}')
            except Exception:
                pass
            return result
        except Exception as e2:
            try:
                print(f'[Coze API Error] (skip verify) {method} {path}: {e2}')
            except Exception:
                pass
            return {'_error': True, '_type': 'ssl_retry_fail', 'message': str(e2)}
    except requests.exceptions.ConnectionError as e:
        try:
            print(f'[Coze API Connection Error] {method} {path}')
        except Exception:
            pass
        return {'_error': True, '_type': 'connection', 'message': f'无法连接到 {COZE_API_BASE}，请检查网络或代理设置'}
    except requests.exceptions.Timeout as e:
        try:
            print(f'[Coze API Timeout Error] {method} {path}')
        except Exception:
            pass
        return {'_error': True, '_type': 'timeout', 'message': f'请求超时({COZE_API_BASE})，请检查网络连接'}
    except Exception as e:
        try:
            print(f'[Coze API Error] {method} {path}: {type(e).__name__}')
        except Exception:
            pass
        return {'_error': True, '_type': 'unknown', 'message': str(e)}

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'yyy123',
    'database': 'energy_storage_qa',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def md5_encrypt(password):
    """MD5加密"""
    return hashlib.md5(password.encode()).hexdigest()

def success_response(data=None, message='操作成功'):
    """成功响应"""
    return jsonify({'code': 200, 'message': message, 'data': data})

def error_response(message='操作失败', code=400):
    """错误响应"""
    return jsonify({'code': code, 'message': message, 'data': None})

# ==================== 静态文件路由 ====================

def serve_frontend_asset(path):
    dist_path = os.path.join(FRONTEND_DIST_DIR, path)
    legacy_path = os.path.join(TEMPLATE_DIR, path)

    if os.path.exists(dist_path):
        return send_from_directory(FRONTEND_DIST_DIR, path)
    if os.path.exists(legacy_path):
        return send_from_directory(TEMPLATE_DIR, path)
    return None


@app.route('/')
def index():
    """首页"""
    if os.path.exists(os.path.join(FRONTEND_DIST_DIR, 'index.html')):
        return send_from_directory(FRONTEND_DIST_DIR, 'index.html')
    return send_from_directory(TEMPLATE_DIR, 'index.html')


@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    """上传文件"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/assets/<path:filename>')
def frontend_assets(filename):
    """前端构建产物"""
    dist_assets_dir = os.path.join(FRONTEND_DIST_DIR, 'assets')
    legacy_assets_dir = os.path.join(TEMPLATE_DIR, 'assets')

    if os.path.exists(os.path.join(dist_assets_dir, filename)):
        return send_from_directory(dist_assets_dir, filename)
    if os.path.exists(os.path.join(legacy_assets_dir, filename)):
        return send_from_directory(legacy_assets_dir, filename)
    return error_response('静态资源不存在', code=404)

@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件"""
    # API路径不应被此路由处理
    if path.startswith('api/'):
        return error_response('接口不存在', 404)

    index_path = os.path.join(FRONTEND_DIST_DIR, 'index.html')

    if path.endswith('.html') and os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

    result = serve_frontend_asset(path)
    if result is not None:
        return result

    if os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

    # 仅在文件存在时才尝试从TEMPLATE_DIR提供
    legacy_path = os.path.join(TEMPLATE_DIR, path)
    if os.path.exists(legacy_path) and os.path.isfile(legacy_path):
        return send_from_directory(TEMPLATE_DIR, path)

    if os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

    return error_response('页面不存在', 404)

UPLOAD_FOLDER = os.path.join(TEMPLATE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """通用文件上传接口"""
    if 'file' not in request.files:
        return error_response('没有上传文件')
    file = request.files['file']
    if file.filename == '':
        return error_response('没有选择文件')
    if file:
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        new_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)
        url = f"/uploads/{new_filename}"
        return success_response(data={"url": url}, message="上传成功")

# ==================== 用户认证相关 ====================

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    phone = data.get('phone', '')
    
    if not all([username, password, email]):
        return error_response('用户名、密码和邮箱不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户名是否存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return error_response('用户名已存在')
            
            # 检查邮箱是否存在
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return error_response('邮箱已被注册')
            
            # 插入新用户
            encrypted_password = md5_encrypt(password)
            sql = "INSERT INTO users (username, password, email, phone) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (username, encrypted_password, email, phone))
            conn.commit()
            
            return success_response(message='注册成功')
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return error_response('用户名和密码不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            encrypted_password = md5_encrypt(password)
            sql = "SELECT id, username, email, phone, avatar, status FROM users WHERE username = %s AND password = %s"
            cursor.execute(sql, (username, encrypted_password))
            user = cursor.fetchone()
            
            if not user:
                return error_response('用户名或密码错误')
            
            if user['status'] == 0:
                return error_response('账号已被禁用')
            
            # 设置session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_type'] = 'user'
            session.permanent = bool(data.get('remember_me', False))
            
            return success_response(data=user, message='登录成功')
    finally:
        conn.close()

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return error_response('用户名和密码不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            encrypted_password = md5_encrypt(password)
            sql = "SELECT id, username, email, role FROM admins WHERE username = %s AND password = %s"
            cursor.execute(sql, (username, encrypted_password))
            admin = cursor.fetchone()
            
            if not admin:
                return error_response('用户名或密码错误')
            
            # 设置session
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            session['user_type'] = 'admin'
            session.permanent = True
            
            return success_response(data=admin, message='登录成功')
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    """退出登录"""
    session.clear()
    return success_response(message='退出成功')

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取当前用户信息"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, email, phone, avatar, created_at FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            return success_response(data=user)
    finally:
        conn.close()

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """更新个人信息"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
        
    data = request.json
    username = data.get('username')
    email = data.get('email')
    phone = data.get('phone', '')
    avatar = data.get('avatar', '')
    
    if not username or not email:
        return error_response('用户名和邮箱不能为空')
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户名是否已存在（排除自己）
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
            if cursor.fetchone():
                return error_response('该用户名已被使用')
                
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s, phone = %s, avatar = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (username, email, phone, avatar, user_id))
            conn.commit()
            
            return success_response(message='修改成功')
    except Exception as e:
        return error_response(str(e))
    finally:
        conn.close()

# ==================== 知识库相关接口 ====================

@app.route('/api/knowledge/list', methods=['GET'])
def get_knowledge_list():
    """获取知识库文档列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    category = request.args.get('category', '')
    keyword = request.args.get('keyword', '')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 构建查询条件
            where_conditions = ["status = 1"]
            params = []
            
            if category:
                where_conditions.append("category = %s")
                params.append(category)
            
            if keyword:
                where_conditions.append("(title LIKE %s OR content LIKE %s OR tags LIKE %s)")
                keyword_pattern = f'%{keyword}%'
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM knowledge_documents WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 查询列表
            offset = (page - 1) * page_size
            list_sql = f"""
                SELECT id, title, category, LEFT(content, 200) as summary, tags, view_count, created_at 
                FROM knowledge_documents 
                WHERE {where_clause}
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, params + [page_size, offset])
            documents = cursor.fetchall()
            
            return success_response(data={
                'list': documents,
                'total': total,
                'page': page,
                'page_size': page_size
            })
    finally:
        conn.close()

@app.route('/api/knowledge/detail/<int:doc_id>', methods=['GET'])
def get_knowledge_detail(doc_id):
    """获取知识库文档详情"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 更新查看次数
            cursor.execute("UPDATE knowledge_documents SET view_count = view_count + 1 WHERE id = %s", (doc_id,))
            conn.commit()
            
            # 查询详情
            cursor.execute("SELECT * FROM knowledge_documents WHERE id = %s", (doc_id,))
            document = cursor.fetchone()
            
            if not document:
                return error_response('文档不存在', 404)
            
            return success_response(data=document)
    finally:
        conn.close()

@app.route('/api/admin/knowledge/list', methods=['GET'])
def admin_get_knowledge_list():
    """管理员获取知识库列表"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM knowledge_documents")
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            sql = """
                SELECT k.*, a.username as uploader_name 
                FROM knowledge_documents k
                LEFT JOIN admins a ON k.upload_by = a.id
                ORDER BY k.created_at DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (page_size, offset))
            documents = cursor.fetchall()
            
            return success_response(data={'list': documents, 'total': total, 'page': page, 'page_size': page_size})
    finally:
        conn.close()

@app.route('/api/admin/knowledge/add', methods=['POST'])
def admin_add_knowledge():
    """管理员添加知识库文档（自动同步到扣子）"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    data = request.json
    title = data.get('title')
    category = data.get('category')
    content = data.get('content')
    tags = data.get('tags', '')
    status = data.get('status', 1)
    
    if not all([title, category, content]):
        return error_response('标题、分类和内容不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO knowledge_documents (title, category, content, tags, upload_by, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (title, category, content, tags, session.get('admin_id'), status))
            conn.commit()
            doc_id = cursor.lastrowid
            
            # 自动同步到扣子知识库
            coze_synced = _sync_doc_to_coze(doc_id, title, content, conn)
            
            return success_response(message='添加成功' + ('（已同步到扣子）' if coze_synced else ''))
    finally:
        conn.close()

@app.route('/api/admin/knowledge/update/<int:doc_id>', methods=['PUT'])
def admin_update_knowledge(doc_id):
    """管理员更新知识库文档（自动同步到扣子）"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    data = request.json
    title = data.get('title')
    category = data.get('category')
    content = data.get('content')
    tags = data.get('tags', '')
    status = data.get('status', 1)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE knowledge_documents 
                SET title = %s, category = %s, content = %s, tags = %s, status = %s
                WHERE id = %s
            """
            cursor.execute(sql, (title, category, content, tags, status, doc_id))
            conn.commit()
            
            # 自动同步到扣子知识库
            coze_synced = _sync_doc_to_coze(doc_id, title, content, conn)
            
            return success_response(message='更新成功' + ('（已同步到扣子）' if coze_synced else ''))
    finally:
        conn.close()

def _sync_doc_to_coze(doc_id, title, content, conn=None):
    """将单个文档同步到扣子知识库"""
    try:
        # 获取默认dataset_id
        conn2 = conn or get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_dataset_id'")
                row = cur.fetchone()
                dataset_id = row.get('config_value', '') if row else ''
        finally:
            if not conn:
                conn2.close()
        
        if not dataset_id:
            print('[Coze Sync] 未配置默认知识库ID, 跳过同步')
            return False
        
        import base64
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {
            'dataset_id': dataset_id,
            'document_bases': [{
                'name': title,
                'source_info': {
                    'document_source': 0,
                    'file_base64': content_b64,
                    'file_type': 'txt'
                }
            }],
            'chunk_strategy': {'chunk_type': 0}
        }
        result = coze_request('POST', '/open_api/knowledge/document/create', json=payload)
        if result and result.get('code') == 0:
            conn3 = conn or get_db_connection()
            try:
                with conn3.cursor() as cur:
                    cur.execute("UPDATE knowledge_documents SET coze_synced = 1, coze_dataset_id = %s WHERE id = %s", (dataset_id, doc_id))
                    conn3.commit()
            finally:
                if not conn:
                    conn3.close()
            print(f'[Coze Sync] 文档 {doc_id} 同步成功')
            return True
        else:
            print(f'[Coze Sync] 文档 {doc_id} 同步失败: {result}')
            return False
    except Exception as e:
        print(f'[Coze Sync Error] {e}')
        return False

@app.route('/api/admin/knowledge/sync/<int:doc_id>', methods=['POST'])
def admin_sync_single_doc(doc_id):
    """手动同步单个文档到扣子"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, content FROM knowledge_documents WHERE id = %s", (doc_id,))
            doc = cursor.fetchone()
            if not doc:
                return error_response('文档不存在')
            
            ok = _sync_doc_to_coze(doc['id'], doc['title'], doc['content'], conn)
            if ok:
                return success_response(message='同步成功')
            else:
                return error_response('同步失败，请检查扣子配置（需在扣子平台管理中设置默认知识库ID）')
    finally:
        conn.close()

@app.route('/api/admin/knowledge/delete/<int:doc_id>', methods=['DELETE'])
def admin_delete_knowledge(doc_id):
    """管理员删除知识库文档"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_documents WHERE id = %s", (doc_id,))
            conn.commit()
            return success_response(message='删除成功')
    finally:
        conn.close()

# ==================== 对话管理 ====================

@app.route('/api/conversations/list', methods=['GET'])
def get_conversations():
    """获取用户对话列表"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    agent_id = request.args.get('agent_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if agent_id:
                # 智能体模式：只获取该智能体的对话
                sql = """
                    SELECT c.*, COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.user_id = %s AND c.agent_id = %s
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                """
                cursor.execute(sql, (user_id, agent_id))
            else:
                # 知识问答模式：只获取无智能体的普通对话
                sql = """
                    SELECT c.*, COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.user_id = %s AND (c.agent_id IS NULL OR c.agent_id = 0)
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                """
                cursor.execute(sql, (user_id,))
            conversations = cursor.fetchall()
            return success_response(data=conversations)
    finally:
        conn.close()

@app.route('/api/conversations/create', methods=['POST'])
def create_conversation():
    """创建新对话"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    title = data.get('title', '新对话')
    conv_type = data.get('type', 'qa')
    agent_id = data.get('agent_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO conversations (user_id, title, type, agent_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user_id, title, conv_type, agent_id))
            conn.commit()
            conversation_id = cursor.lastrowid
            return success_response(data={'id': conversation_id}, message='创建成功')
    finally:
        conn.close()

@app.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
def get_messages(conv_id):
    """获取对话消息"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证对话所属
            cursor.execute("SELECT user_id FROM conversations WHERE id = %s", (conv_id,))
            conv = cursor.fetchone()
            if not conv or conv['user_id'] != user_id:
                return error_response('无权限访问', 403)
            
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conv_id,))
            messages = cursor.fetchall()
            return success_response(data=messages)
    finally:
        conn.close()

@app.route('/api/conversations/<int:conv_id>/send', methods=['POST'])
def send_message(conv_id):
    """发送消息"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    content = data.get('content')
    
    if not content:
        return error_response('消息内容不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证对话所属并获取agent_id
            cursor.execute("SELECT user_id, agent_id FROM conversations WHERE id = %s", (conv_id,))
            conv = cursor.fetchone()
            if not conv or conv['user_id'] != user_id:
                return error_response('无权限访问', 403)
            
            # 插入用户消息
            cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)", (conv_id, content))
            
            # 调用扣子AI回复
            ai_response = generate_ai_response(content, agent_id=conv.get('agent_id'))
            cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'assistant', %s)", (conv_id, ai_response))
            
            # 更新对话时间
            cursor.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conv_id,))
            
            conn.commit()
            return success_response(data={'response': ai_response}, message='发送成功')
    finally:
        conn.close()

from flask import Response, stream_with_context

@app.route('/api/conversations/<int:conv_id>/send_stream', methods=['POST'])
def send_message_stream(conv_id):
    """流式发送消息（SSE）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'code': 401, 'message': '未登录'}), 401
    
    data = request.json
    content = data.get('content')
    if not content:
        return jsonify({'code': 400, 'message': '消息内容不能为空'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, agent_id FROM conversations WHERE id = %s", (conv_id,))
            conv = cursor.fetchone()
            if not conv or conv['user_id'] != user_id:
                return jsonify({'code': 403, 'message': '无权限'}), 403
            
            # 插入用户消息
            cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)", (conv_id, content))
            conn.commit()
    finally:
        conn.close()
    
    # 获取bot_id
    coze_bot_id = None
    agent_id = conv.get('agent_id')
    if agent_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT coze_bot_id FROM agents WHERE id = %s", (agent_id,))
                row = cur.fetchone()
                if row and row.get('coze_bot_id'):
                    coze_bot_id = row['coze_bot_id']
        finally:
            conn2.close()
    
    if not coze_bot_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    coze_bot_id = row['config_value']
        finally:
            conn2.close()
    
    if not coze_bot_id:
        # 无Coze Bot，使用本地回复
        local_reply = _local_ai_response(content)
        conn3 = get_db_connection()
        try:
            with conn3.cursor() as cur:
                cur.execute("INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'assistant', %s)", (conv_id, local_reply))
                cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conv_id,))
                conn3.commit()
        finally:
            conn3.close()
        
        def local_stream():
            yield f"data: {json.dumps({'event': 'delta', 'content': local_reply})}\n\n"
            yield f"data: {json.dumps({'event': 'done', 'content': local_reply})}\n\n"
        
        return Response(stream_with_context(local_stream()), mimetype='text/event-stream',
                       headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    
    # 调用Coze流式API
    def generate():
        full_answer = ''
        try:
            coze_token = ''
            conn4 = get_db_connection()
            try:
                with conn4.cursor() as cur:
                    cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_api_token'")
                    row = cur.fetchone()
                    if row:
                        coze_token = row.get('config_value', '')
            finally:
                conn4.close()
            
            # 如果数据库没有配置token，使用全局常量
            if not coze_token:
                coze_token = get_coze_token()
            
            print(f'[Coze Stream] bot_id={coze_bot_id}, token_len={len(coze_token)}, content={content[:50]}')
            
            headers = {
                'Authorization': f'Bearer {coze_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'bot_id': coze_bot_id,
                'user_id': str(user_id),
                'stream': True,
                'auto_save_history': True,
                'additional_messages': [
                    {'role': 'user', 'content': content, 'content_type': 'text'}
                ]
            }
            
            resp = requests.post('https://api.coze.cn/v3/chat', json=payload, headers=headers, stream=True, timeout=120)
            resp.encoding = 'utf-8'  # 强制UTF-8解码，避免中文乱码
            
            print(f'[Coze Stream] Response status: {resp.status_code}, encoding: {resp.encoding}')
            
            if resp.status_code != 200:
                error_msg = f'Coze API错误: {resp.status_code}'
                try:
                    err_body = resp.json()
                    error_msg = f'Coze API错误({resp.status_code}): {err_body.get("msg", err_body.get("message", ""))}'
                except:
                    pass
                print(f'[Coze Stream] Error: {error_msg}')
                yield f"data: {json.dumps({'event': 'error', 'content': error_msg})}\n\n"
                return
            
            # 检测Coze返回200但body是JSON错误（而非SSE流）的情况
            # 先peek第一行判断是否为SSE流格式
            first_line_checked = False
            current_event = ''
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    current_event = ''
                    continue
                
                # 第一行检查：如果不是SSE格式(event:/data:)，可能是JSON错误
                if not first_line_checked:
                    first_line_checked = True
                    if not line.startswith('event:') and not line.startswith('data:'):
                        # 尝试解析为JSON错误
                        try:
                            err_obj = json.loads(line)
                            if 'code' in err_obj and err_obj.get('code') != 0:
                                error_msg = err_obj.get('msg', err_obj.get('message', '未知错误'))
                                print(f'[Coze Stream] API error in body: code={err_obj.get("code")}, msg={error_msg}')
                                yield f"data: {json.dumps({'event': 'error', 'content': f'Coze API错误: {error_msg}'})}\n\n"
                                return
                        except json.JSONDecodeError:
                            pass
                
                print(f'[Coze SSE] {line[:120]}')
                
                # SSE格式: event: 和 data: 在不同行
                if line.startswith('event:'):
                    current_event = line[6:].strip()
                    continue
                
                if line.startswith('data:'):
                    data_str = line[5:].strip()
                    if data_str == '[DONE]':
                        break
                    try:
                        msg = json.loads(data_str)
                        
                        # 使用从event:行获取的事件类型
                        event_type = current_event
                        
                        if event_type == 'conversation.message.delta':
                            if isinstance(msg, str):
                                msg = json.loads(msg)
                            delta_content = msg.get('content', '')
                            if msg.get('role') == 'assistant' and msg.get('type') == 'answer':
                                full_answer += delta_content
                                yield f"data: {json.dumps({'event': 'delta', 'content': delta_content})}\n\n"
                        
                        elif event_type == 'conversation.message.completed':
                            if isinstance(msg, str):
                                msg = json.loads(msg)
                            if msg.get('role') == 'assistant' and msg.get('type') == 'answer':
                                full_answer = msg.get('content', full_answer)
                        
                        elif event_type == 'conversation.chat.completed':
                            pass
                        
                        elif event_type == 'done':
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
        except Exception as e:
            print(f'[Coze Stream Error] {e}')
            if not full_answer:
                full_answer = _local_ai_response(content)
                yield f"data: {json.dumps({'event': 'delta', 'content': full_answer})}\n\n"
        
        # 保存AI回复到数据库
        if full_answer:
            conn5 = get_db_connection()
            try:
                with conn5.cursor() as cur:
                    cur.execute("INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'assistant', %s)", (conv_id, full_answer))
                    cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conv_id,))
                    conn5.commit()
            finally:
                conn5.close()
        
        yield f"data: {json.dumps({'event': 'done', 'content': full_answer})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

def generate_ai_response(user_message, agent_id=None):
    """调用扣子API生成AI响应"""
    coze_bot_id = None
    if agent_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT coze_bot_id FROM agents WHERE id = %s", (agent_id,))
                row = cur.fetchone()
                if row and row.get('coze_bot_id'):
                    coze_bot_id = row['coze_bot_id']
        finally:
            conn2.close()

    if not coze_bot_id:
        # 查系统配置中的默认bot_id
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    coze_bot_id = row['config_value']
        finally:
            conn2.close()

    if not coze_bot_id:
        return _local_ai_response(user_message)

    try:
        payload = {
            'bot_id': coze_bot_id,
            'user_id': str(session.get('user_id', 'default_user')),
            'stream': False,
            'auto_save_history': True,
            'additional_messages': [
                {'role': 'user', 'content': user_message, 'content_type': 'text'}
            ]
        }
        result = coze_request('POST', '/v3/chat', json=payload)
        if result and result.get('code') == 0:
            chat_data = result.get('data', {})
            chat_id = chat_data.get('id')
            cid = chat_data.get('conversation_id')
            for _ in range(60):
                time.sleep(2)
                sr = coze_request('GET', f'/v3/chat/retrieve?chat_id={chat_id}&conversation_id={cid}')
                if sr and sr.get('code') == 0:
                    st = sr.get('data', {}).get('status')
                    if st == 'completed':
                        mr = coze_request('GET', f'/v3/chat/message/list?chat_id={chat_id}&conversation_id={cid}')
                        if mr and mr.get('code') == 0:
                            for m in mr.get('data', []):
                                if m.get('role') == 'assistant' and m.get('type') == 'answer':
                                    return m.get('content', '抱歉，未能获取回复。')
                        break
                    elif st == 'failed':
                        break
            return '抱歉，AI响应超时，请稍后重试。'
        else:
            return _local_ai_response(user_message)
    except Exception as e:
        print(f'[Coze Chat Exception] {e}')
        return _local_ai_response(user_message)

def _local_ai_response(user_message):
    """本地备用AI响应"""
    responses = {
        '并网': '储能系统并网需要满足国家标准GB/T 36547-2018《电化学储能系统接入电网技术规定》的要求。主要包括：\n\n1. 电压和频率适应性\n2. 功率控制能力\n3. 电能质量要求\n4. 保护功能配置\n5. 通信和调度能力',
        '检测': '储能系统并网检测主要包括：电气性能测试、保护功能测试、电能质量测试等。检测周期一般为3-7个工作日。',
        '安全': '储能系统安全管理要点：电池安全、消防安全、电气安全、环境安全、运维安全。建议参考GB/T 51048相关标准。',
        '标准': '储能系统相关主要标准：GB/T 36547-2018、GB/T 36548-2018、GB 51048-2014等。'
    }
    for keyword, response in responses.items():
        if keyword in user_message:
            return response
    return '感谢您的提问。作为储能并网技术助手，我可以帮您解答并网技术标准、检测流程、安全规范等方面的问题。请提出您的具体问题。'

@app.route('/api/conversations/delete/<int:conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    """删除对话"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conv_id, user_id))
            conn.commit()
            return success_response(message='删除成功')
    finally:
        conn.close()



@app.route('/api/agents/list', methods=['GET'])
def get_agents():
    """获取智能体列表"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT a.*, u.username as creator_name
                FROM agents a
                LEFT JOIN users u ON a.user_id = u.id
                WHERE a.user_id = %s OR a.is_public = 1
                ORDER BY a.created_at DESC
            """
            cursor.execute(sql, (user_id,))
            agents = cursor.fetchall()
            return success_response(data=agents)
    finally:
        conn.close()

@app.route('/api/agents/create', methods=['POST'])
def create_agent():
    """创建智能体（同步到扣子平台）"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    system_prompt = data.get('system_prompt', '')
    temperature = data.get('temperature', 0.7)
    is_public = data.get('is_public', 0)
    coze_bot_id = data.get('coze_bot_id', '')
    prologue = data.get('prologue', '')
    suggested_questions = data.get('suggested_questions', [])
    
    if not name:
        return error_response('智能体名称不能为空')
    
    # 如果没有手动填写coze_bot_id，自动同步到扣子默认工作空间
    if not coze_bot_id:
        conn_cfg = get_db_connection()
        try:
            with conn_cfg.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_space_id'")
                row = cur.fetchone()
                space_id = row.get('config_value', '') if row else ''
        finally:
            conn_cfg.close()
        
        if space_id:
            # 调用扣子API创建Bot
            payload = {
                'space_id': space_id,
                'name': name,
                'description': description or f'储能并网检测智能体 - {name}',
                'prompt_info': {
                    'prompt': system_prompt or '你是一个储能并网检测领域的专业助手。'
                },
                'onboarding_info': {
                    'prologue': prologue or f'你好，我是{name}，有什么可以帮助你的？',
                    'suggested_questions': suggested_questions if suggested_questions else [
                        '请介绍一下你的功能',
                        '储能并网检测有哪些关键指标？',
                        '如何进行并网安全评估？'
                    ]
                }
            }
            print(f'[Coze] Creating bot: {name}, prompt={system_prompt[:50]}...')
            result = coze_request('POST', '/v1/bot/create', json=payload)
            if result and result.get('code') == 0:
                bot_data = result.get('data', {})
                coze_bot_id = bot_data.get('bot_id') or bot_data.get('id') or ''
                print(f'[Coze] Bot created: {coze_bot_id}')
                
                # 自动发布Bot到API渠道
                if coze_bot_id:
                    pub_payload = {
                        'bot_id': coze_bot_id,
                        'connector_ids': ['1024']
                    }
                    pub_result = coze_request('POST', '/v1/bot/publish', json=pub_payload)
                    if pub_result and pub_result.get('code') == 0:
                        print(f'[Coze] Bot published: {coze_bot_id}')
                    else:
                        print(f'[Coze] Bot publish failed: {pub_result}')
            else:
                print(f'[Coze] Bot create failed: {result}')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO agents (user_id, name, description, system_prompt, temperature, is_public, coze_bot_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, name, description, system_prompt, temperature, is_public, coze_bot_id))
            conn.commit()
            agent_id = cursor.lastrowid
            return success_response(data={'id': agent_id, 'coze_bot_id': coze_bot_id}, message='创建成功' + ('（已同步到扣子平台）' if coze_bot_id else ''))
    finally:
        conn.close()

@app.route('/api/agents/update/<int:agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """更新智能体"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证所属
            cursor.execute("SELECT user_id FROM agents WHERE id = %s", (agent_id,))
            agent = cursor.fetchone()
            if not agent or agent['user_id'] != user_id:
                return error_response('无权限', 403)
            
            sql = """
                UPDATE agents 
                SET name = %s, description = %s, system_prompt = %s, temperature = %s, is_public = %s, coze_bot_id = %s
                WHERE id = %s
            """
            cursor.execute(sql, (
                data.get('name'), data.get('description'), data.get('system_prompt'),
                data.get('temperature'), data.get('is_public'), data.get('coze_bot_id', ''), agent_id
            ))
            conn.commit()
            return success_response(message='更新成功')
    finally:
        conn.close()

@app.route('/api/agents/delete/<int:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """删除智能体"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM agents WHERE id = %s AND user_id = %s", (agent_id, user_id))
            conn.commit()
            return success_response(message='删除成功')
    finally:
        conn.close()

# ==================== FAQ管理 ====================

@app.route('/api/faq/list', methods=['GET'])
def get_faq_list():
    """获取FAQ列表"""
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if category:
                sql = "SELECT * FROM faqs WHERE status = 1 AND category = %s ORDER BY order_num ASC, created_at DESC"
                cursor.execute(sql, (category,))
            else:
                sql = "SELECT * FROM faqs WHERE status = 1 ORDER BY order_num ASC, created_at DESC"
                cursor.execute(sql)
            
            faqs = cursor.fetchall()
            
            # 按分类分组
            grouped_faqs = {}
            for faq in faqs:
                cat = faq['category']
                if cat not in grouped_faqs:
                    grouped_faqs[cat] = []
                grouped_faqs[cat].append(faq)
            
            return success_response(data=grouped_faqs)
    finally:
        conn.close()

@app.route('/api/faq/view/<int:faq_id>', methods=['POST'])
def view_faq(faq_id):
    """增加FAQ查看次数"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE faqs SET view_count = view_count + 1 WHERE id = %s", (faq_id,))
            conn.commit()
            return success_response()
    finally:
        conn.close()

@app.route('/api/admin/faq/list', methods=['GET'])
def admin_get_faq_list():
    """管理员获取FAQ列表"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM faqs ORDER BY order_num ASC, created_at DESC")
            faqs = cursor.fetchall()
            return success_response(data=faqs)
    finally:
        conn.close()

@app.route('/api/admin/faq/add', methods=['POST'])
def admin_add_faq():
    """管理员添加FAQ"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    data = request.json
    category = data.get('category')
    question = data.get('question')
    answer = data.get('answer')
    order_num = data.get('order_num', 0)
    status = data.get('status', 1)
    
    if not all([category, question, answer]):
        return error_response('分类、问题和答案不能为空')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO faqs (category, question, answer, order_num, status) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (category, question, answer, order_num, status))
            conn.commit()
            return success_response(message='添加成功')
    finally:
        conn.close()

@app.route('/api/admin/faq/update/<int:faq_id>', methods=['PUT'])
def admin_update_faq(faq_id):
    """管理员更新FAQ"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    data = request.json
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE faqs 
                SET category = %s, question = %s, answer = %s, order_num = %s, status = %s
                WHERE id = %s
            """
            cursor.execute(sql, (
                data.get('category'), data.get('question'), data.get('answer'),
                data.get('order_num'), data.get('status'), faq_id
            ))
            conn.commit()
            return success_response(message='更新成功')
    finally:
        conn.close()

@app.route('/api/admin/faq/delete/<int:faq_id>', methods=['DELETE'])
def admin_delete_faq(faq_id):
    """管理员删除FAQ"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM faqs WHERE id = %s", (faq_id,))
            conn.commit()
            return success_response(message='删除成功')
    finally:
        conn.close()

# ==================== 创作管理 ====================

@app.route('/api/creations/list', methods=['GET'])
def get_creations():
    """获取创作列表"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM creations WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            creations = cursor.fetchall()
            return success_response(data=creations)
    finally:
        conn.close()

@app.route('/api/creations/create', methods=['POST'])
def create_creation():
    """创建作品"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    title = data.get('title')
    creation_type = data.get('type')
    prompt = data.get('prompt')
    
    if not all([title, creation_type, prompt]):
        return error_response('标题、类型和提示词不能为空')
    
    # 调用扣子AI生成内容
    content = generate_creation_content(creation_type, prompt)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO creations (user_id, title, type, prompt, content) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (user_id, title, creation_type, prompt, content))
            conn.commit()
            creation_id = cursor.lastrowid
            return success_response(data={'id': creation_id, 'content': content}, message='创建成功')
    finally:
        conn.close()

def generate_creation_content(creation_type, prompt):
    """调用扣子API生成创作内容"""
    # 尝试使用扣子API
    coze_bot_id = None
    conn2 = get_db_connection()
    try:
        with conn2.cursor() as cur:
            # 优先使用创作专用bot
            cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_creation_bot_id'")
            row = cur.fetchone()
            if row and row.get('config_value'):
                coze_bot_id = row['config_value']
            
            # 回退到默认bot
            if not coze_bot_id:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    coze_bot_id = row['config_value']
    finally:
        conn2.close()
    
    if coze_bot_id:
        try:
            # 获取token（从数据库 -> 回退默认值）
            coze_token = get_coze_token()
            
            full_prompt = f'请根据以下要求生成一篇专业的{creation_type}，内容要详细、专业、有深度：\n{prompt}'
            
            # 使用流式API获取完整内容
            headers = {
                'Authorization': f'Bearer {coze_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'bot_id': coze_bot_id,
                'user_id': str(session.get('user_id', 'default_creator')),
                'stream': True,
                'auto_save_history': False,
                'additional_messages': [
                    {'role': 'user', 'content': full_prompt, 'content_type': 'text'}
                ]
            }
            
            print(f'[Coze Creation] Calling bot_id={coze_bot_id}, prompt={full_prompt[:80]}...')
            
            resp = requests.post('https://api.coze.cn/v3/chat', json=payload, headers=headers, stream=True, timeout=120)
            resp.encoding = 'utf-8'
            
            if resp.status_code == 200:
                full_answer = ''
                current_event = ''
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        current_event = ''
                        continue
                    if line.startswith('event:'):
                        current_event = line[6:].strip()
                        continue
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            msg = json.loads(data_str)
                            if current_event == 'conversation.message.delta':
                                if msg.get('role') == 'assistant' and msg.get('type') == 'answer':
                                    full_answer += msg.get('content', '')
                            elif current_event == 'conversation.message.completed':
                                if msg.get('role') == 'assistant' and msg.get('type') == 'answer':
                                    full_answer = msg.get('content', full_answer)
                            elif current_event == 'done':
                                break
                        except json.JSONDecodeError:
                            continue
                
                if full_answer:
                    print(f'[Coze Creation] 成功生成内容，长度={len(full_answer)}')
                    return full_answer
                else:
                    print('[Coze Creation] 流式响应为空，回退到模板')
            else:
                print(f'[Coze Creation] API返回错误: {resp.status_code}')
        except Exception as e:
            print(f'[Coze Creation Error] {e}')
    
    # 回退到本地模板
    templates = {
        '技术方案': f'''# {prompt}

## 一、项目概述
本项目旨在{prompt}，通过采用先进的储能技术和智能控制系统，实现高效、安全、可靠的储能解决方案。

## 二、技术方案
### 2.1 技术路线选择
基于项目需求分析，推荐采用磷酸铁锂电池技术路线，具有以下优势：
- 安全性能优异
- 循环寿命长（>6000次）
- 温度适应性好
- 成本适中

### 2.2 系统构成
1. **电池系统**：采用模块化设计，便于扩展和维护
2. **储能变流器(PCS)**：双向变流，效率>95%
3. **能量管理系统(EMS)**：智能调度和优化
4. **电池管理系统(BMS)**：实时监控和保护

## 三、并网方案
### 3.1 并网接入点
根据电网条件，选择合适的电压等级接入点。

### 3.2 并网技术要求
严格按照GB/T 36547-2018标准执行。

## 四、安全设计
### 4.1 消防系统
配置自动灭火系统和烟感探测装置。

### 4.2 监控系统
7×24小时实时监控，异常自动报警。

## 五、经济性分析
预计投资回收期：5-7年
年均收益率：12-15%
''',
        '技术报告': f'''# {prompt}

## 摘要
本报告针对{prompt}进行了全面的技术分析和研究。

## 1. 引言
### 1.1 背景
### 1.2 目的和意义

## 2. 技术现状分析
### 2.1 国内外发展现状
### 2.2 关键技术分析

## 3. 技术方案
### 3.1 总体方案
### 3.2 关键技术
### 3.3 创新点

## 4. 实施建议
### 4.1 技术路线
### 4.2 实施步骤
### 4.3 风险控制

## 5. 结论
本报告提出的技术方案具有可行性和先进性，建议进一步推进实施。
''',
        '检测报告': f'''# {prompt}

## 基本信息
- 项目名称：{prompt}
- 检测单位：XX检测中心
- 检测日期：2024年XX月XX日
- 检测依据：GB/T 36548-2018

## 检测项目及结果

### 1. 电气性能测试
| 测试项目 | 标准要求 | 测试结果 | 结论 |
|---------|---------|---------|------|
| 额定功率 | ≥标称值 | 合格 | 通过 |
| 电压适应性 | 0.9-1.1Un | 合格 | 通过 |
| 频率适应性 | 49.5-50.5Hz | 合格 | 通过 |

### 2. 保护功能测试
所有保护功能测试均符合标准要求。

### 3. 电能质量测试
谐波含量、功率因数等指标均满足要求。

## 综合结论
该储能系统各项技术指标均符合并网要求，同意并网运行。
'''
    }
    
    return templates.get(creation_type, f'# {prompt}\n\n根据您的需求"{prompt}"，生成的内容如下：\n\n...')

# ==================== 管理员用户管理 ====================

@app.route('/api/admin/users/list', methods=['GET'])
def admin_get_users():
    """管理员获取用户列表"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    keyword = request.args.get('keyword', '')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if keyword:
                search_query = "SELECT COUNT(*) as total FROM users WHERE username LIKE %s OR email LIKE %s OR phone LIKE %s"
                cursor.execute(search_query, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
                total = cursor.fetchone()['total']
                
                offset = (page - 1) * page_size
                data_query = "SELECT * FROM users WHERE username LIKE %s OR email LIKE %s OR phone LIKE %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
                cursor.execute(data_query, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", page_size, offset))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM users")
                total = cursor.fetchone()['total']
                
                offset = (page - 1) * page_size
                cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s", (page_size, offset))
                
            users = cursor.fetchall()
            for user in users:
                user.pop('password', None)
            
            return success_response(data={'list': users, 'total': total, 'page': page, 'page_size': page_size})
    finally:
        conn.close()

@app.route('/api/admin/users/toggle-status/<int:user_id>', methods=['PUT'])
def admin_toggle_user_status(user_id):
    """管理员切换用户状态"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET status = 1 - status WHERE id = %s", (user_id,))
            conn.commit()
            return success_response(message='状态更新成功')
    finally:
        conn.close()

# ==================== 管理员对话记录管理 ====================

@app.route('/api/admin/conversations/list', methods=['GET'])
def admin_get_conversations():
    """管理员获取对话记录"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM conversations")
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            sql = """
                SELECT c.*, u.username, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN users u ON c.user_id = u.id
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (page_size, offset))
            conversations = cursor.fetchall()
            
            return success_response(data={'list': conversations, 'total': total, 'page': page, 'page_size': page_size})
    finally:
        conn.close()

@app.route('/api/admin/conversations/messages/<int:conversation_id>', methods=['GET'])
def admin_get_conversation_messages(conversation_id):
    """管理员查看对话详情 - 获取指定会话的全部消息记录"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 验证会话是否存在
            cursor.execute("SELECT c.*, u.username FROM conversations c LEFT JOIN users u ON c.user_id = u.id WHERE c.id = %s", (conversation_id,))
            conv = cursor.fetchone()
            if not conv:
                return error_response('对话不存在')

            # 绕过用户归属校验，直接查询全部消息
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conversation_id,))
            messages = cursor.fetchall()

            return success_response(data={'conversation': conv, 'messages': messages})
    finally:
        conn.close()

# ==================== 统计数据 ====================

@app.route('/api/admin/statistics', methods=['GET'])
def admin_get_statistics():
    """管理员获取统计数据"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            stats = {}
            
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 1")
            stats['active_users'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM knowledge_documents")
            stats['total_documents'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            stats['total_conversations'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            stats['total_messages'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM agents")
            stats['total_agents'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM faqs")
            stats['total_faqs'] = cursor.fetchone()['count']
            
            return success_response(data=stats)
    finally:
        conn.close()

# ==================== 扣子(Coze)平台集成API ====================

@app.route('/api/coze/chat', methods=['POST'])
def coze_chat():
    """通过扣子API发起对话（非流式，轮询等待结果）"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    bot_id = data.get('bot_id', '')
    message = data.get('message', '')
    coze_user_id = data.get('user_id', str(user_id))
    
    if not message:
        return error_response('消息内容不能为空')
    
    # 如果没有指定bot_id，使用默认配置
    if not bot_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    bot_id = row['config_value']
        finally:
            conn2.close()
    
    if not bot_id:
        return error_response('未配置默认Bot ID，请先在扣子平台管理中设置')
    
    payload = {
        'bot_id': bot_id,
        'user_id': coze_user_id,
        'stream': False,
        'auto_save_history': True,
        'additional_messages': [
            {'role': 'user', 'content': message, 'content_type': 'text'}
        ]
    }
    
    result = coze_request('POST', '/v3/chat', json=payload)
    if not result or result.get('code') != 0:
        return error_response(f'发起对话失败: {result.get("msg") if result else "请求失败"}')
    
    chat_data = result.get('data', {})
    chat_id = chat_data.get('id')
    conversation_id = chat_data.get('conversation_id')
    
    # 轮询等待完成
    for _ in range(60):
        time.sleep(2)
        sr = coze_request('GET', f'/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}')
        if sr and sr.get('code') == 0:
            status = sr.get('data', {}).get('status')
            if status == 'completed':
                # 获取消息列表
                mr = coze_request('GET', f'/v3/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}')
                if mr and mr.get('code') == 0:
                    answer = ''
                    for m in mr.get('data', []):
                        if m.get('role') == 'assistant' and m.get('type') == 'answer':
                            answer = m.get('content', '')
                            break
                    return success_response(data={
                        'chat_id': chat_id,
                        'conversation_id': conversation_id,
                        'status': 'completed',
                        'answer': answer,
                        'messages': mr.get('data', [])
                    })
                break
            elif status == 'failed':
                return error_response('对话处理失败')
    
    return error_response('对话响应超时')

@app.route('/api/coze/chat/retrieve', methods=['GET'])
def coze_retrieve_chat():
    """查看扣子对话详情"""
    chat_id = request.args.get('chat_id', '')
    conversation_id = request.args.get('conversation_id', '')
    
    if not chat_id or not conversation_id:
        return error_response('chat_id和conversation_id不能为空')
    
    # 获取对话状态
    sr = coze_request('GET', f'/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}')
    if not sr or sr.get('code') != 0:
        return error_response(f'查询对话失败: {sr.get("msg") if sr else "请求失败"}')
    
    chat_info = sr.get('data', {})
    
    # 获取消息列表
    messages = []
    mr = coze_request('GET', f'/v3/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}')
    if mr and mr.get('code') == 0:
        messages = mr.get('data', [])
    
    return success_response(data={
        'chat': chat_info,
        'messages': messages
    })

# ---------- 扣子会话管理 ----------

@app.route('/api/coze/conversations/create', methods=['POST'])
def coze_create_conversation():
    """创建扣子会话"""
    data = request.json or {}
    bot_id = data.get('bot_id', '')
    
    # 如果没指定bot_id, 从配置读取
    if not bot_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    bot_id = row['config_value']
        finally:
            conn2.close()
    
    payload = {}
    if bot_id:
        payload['bot_id'] = bot_id
    if data.get('meta_data'):
        payload['meta_data'] = data['meta_data']
    if data.get('messages'):
        payload['messages'] = data['messages']
    
    result = coze_request('POST', '/v1/conversation/create', json=payload)
    if result and result.get('code') == 0:
        return success_response(data=result.get('data'), message='会话创建成功')
    return error_response(f'创建失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/conversations/list', methods=['GET'])
def coze_list_conversations():
    """查看扣子会话列表"""
    bot_id = request.args.get('bot_id', '')
    
    if not bot_id:
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_bot_id'")
                row = cur.fetchone()
                if row and row.get('config_value'):
                    bot_id = row['config_value']
        finally:
            conn2.close()
    
    if not bot_id:
        return error_response('请提供bot_id或配置默认Bot ID')
    
    result = coze_request('GET', f'/v1/conversations?bot_id={bot_id}')
    if result and (result.get('code') == 0 or 'data' in result):
        return success_response(data=result.get('data'))
    return error_response(f'获取会话列表失败: {json.dumps(result, ensure_ascii=False) if result else "请求失败"}')

@app.route('/api/coze/conversations/retrieve/<conversation_id>', methods=['GET'])
def coze_retrieve_conversation(conversation_id):
    """查看扣子会话信息"""
    result = coze_request('GET', f'/v1/conversation/retrieve?conversation_id={conversation_id}')
    if result and (result.get('code') == 0 or 'data' in result):
        return success_response(data=result.get('data'))
    return error_response(f'查询失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/conversations/delete/<conversation_id>', methods=['DELETE'])
def coze_delete_conversation(conversation_id):
    """删除扣子会话"""
    result = coze_request('DELETE', f'/v1/conversations/{conversation_id}')
    if result and result.get('code') == 0:
        return success_response(message='会话删除成功')
    return error_response(f'删除失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/conversations/<conversation_id>/clear', methods=['POST'])
def coze_clear_conversation(conversation_id):
    """清空扣子会话消息"""
    result = coze_request('POST', f'/v1/conversations/{conversation_id}/clear')
    if result and result.get('code') == 0:
        return success_response(message='会话消息已清空')
    return error_response(f'清空失败: {result.get("msg") if result else "请求失败"}')


@app.route('/api/coze/test', methods=['GET'])
def coze_test_connection():
    """测试扣子API连接"""
    result = coze_request('GET', '/v1/workspaces')
    if result is None:
        return error_response('扣子API连接失败: 请求无返回结果，请检查网络连接')
    if result.get('_error'):
        err_type = result.get('_type', '')
        err_msg = result.get('message', '未知错误')
        if err_type == 'connection':
            return error_response(f'网络连接失败: 无法访问 {COZE_API_BASE}，请检查网络或代理设置')
        elif err_type == 'timeout':
            return error_response(f'网络连接超时: 请求 {COZE_API_BASE} 超时，请检查网络连接')
        elif err_type in ('ssl_retry_fail',):
            return error_response(f'SSL证书验证失败: {err_msg}')
        return error_response(f'请求失败: {err_msg}')
    if result.get('code') == 0 or 'data' in result:
        return success_response(data=result.get('data'), message='扣子API连接成功')
    code = result.get('code', '')
    msg = result.get('msg', '')
    if code == 401 or 'auth' in str(msg).lower() or 'token' in str(msg).lower():
        return error_response(f'认证失败: API Token 无效或已过期，请在扣子平台管理中重新配置Token')
    return error_response(f'扣子API连接失败: [{code}] {msg}')

@app.route('/api/coze/workspaces', methods=['GET'])
def coze_list_workspaces():
    """获取扣子工作空间列表"""
    page_num = request.args.get('page_num', '1')
    page_size = request.args.get('page_size', '50')
    result = coze_request('GET', f'/v1/workspaces?page_num={page_num}&page_size={page_size}')
    if result and (result.get('code') == 0 or 'data' in result):
        return success_response(data=result.get('data'))
    return error_response(f'获取工作空间列表失败: {json.dumps(result, ensure_ascii=False) if result else "请求失败"}')

@app.route('/api/coze/bots', methods=['GET'])
def coze_list_bots():
    """获取扣子智能体列表"""
    space_id = request.args.get('space_id', '')
    url = f'/v1/bots?workspace_id={space_id}&page_size=50' if space_id else '/v1/bots?page_size=50'
    result = coze_request('GET', url)
    if result and (result.get('code') == 0 or 'data' in result):
        return success_response(data=result.get('data'))
    return error_response(f'获取智能体列表失败: {json.dumps(result, ensure_ascii=False) if result else "请求失败"}')

@app.route('/api/coze/bot/create', methods=['POST'])
def coze_create_bot():
    """通过扣子API创建智能体"""
    data = request.json
    payload = {
        'space_id': data.get('space_id'),
        'name': data.get('name'),
        'description': data.get('description', ''),
        'prompt_info': {
            'prompt': data.get('system_prompt', '')
        }
    }
    result = coze_request('POST', '/v1/bot/create', json=payload)
    if result and result.get('code') == 0:
        bot_data = result.get('data', {})
        return success_response(data=bot_data, message='扣子智能体创建成功')
    return error_response(f'创建失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/bot/publish', methods=['POST'])
def coze_publish_bot():
    """发布扣子智能体到API"""
    data = request.json
    bot_id = data.get('bot_id')
    payload = {
        'bot_id': bot_id,
        'connector_ids': ['1024']
    }
    result = coze_request('POST', '/v1/bot/publish', json=payload)
    if result and result.get('code') == 0:
        return success_response(message='发布成功')
    return error_response(f'发布失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/bot/unpublish', methods=['POST'])
def coze_unpublish_bot():
    """下架扣子智能体"""
    data = request.json
    bot_id = data.get('bot_id')
    connector_id = data.get('connector_id', '1024')
    payload = {
        'connector_id': connector_id
    }
    result = coze_request('POST', f'/v1/bots/{bot_id}/unpublish', json=payload)
    if result and result.get('code') == 0:
        return success_response(message='下架成功')
    return error_response(f'下架失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/datasets', methods=['GET'])
def coze_list_datasets():
    """获取扣子知识库列表"""
    space_id = request.args.get('space_id', '')
    if not space_id:
        return error_response('请提供工作空间ID')
    result = coze_request('GET', f'/v1/datasets?space_id={space_id}&page_size=50')
    if result and (result.get('code') == 0 or 'data' in result):
        return success_response(data=result.get('data'))
    return error_response(f'获取知识库列表失败: {json.dumps(result, ensure_ascii=False) if result else "请求失败"}')

@app.route('/api/coze/datasets/create', methods=['POST'])
def coze_create_dataset():
    """创建扣子知识库"""
    data = request.json
    space_id = data.get('space_id', '')
    if not space_id:
        # 从配置读取默认工作空间
        conn2 = get_db_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_space_id'")
                row = cur.fetchone()
                space_id = row.get('config_value', '') if row else ''
        finally:
            conn2.close()
    if not space_id:
        return error_response('请先配置默认工作空间ID')
    
    payload = {
        'space_id': space_id,
        'name': data.get('name'),
        'description': data.get('description', ''),
        'format_type': data.get('format_type', 0)
    }
    result = coze_request('POST', '/v1/datasets', json=payload)
    if result and result.get('code') == 0:
        return success_response(data=result.get('data'), message='知识库创建成功')
    return error_response(f'创建失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/datasets/update/<dataset_id>', methods=['PUT'])
def coze_update_dataset(dataset_id):
    """修改扣子知识库信息"""
    data = request.json
    payload = {}
    if 'name' in data:
        payload['name'] = data['name']
    if 'description' in data:
        payload['description'] = data['description']
    if 'icon' in data:
        payload['icon'] = data['icon']
    
    result = coze_request('PUT', f'/v1/datasets/{dataset_id}', json=payload)
    if result and result.get('code') == 0:
        return success_response(message='知识库修改成功')
    return error_response(f'修改失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/datasets/delete/<dataset_id>', methods=['DELETE'])
def coze_delete_dataset(dataset_id):
    """删除扣子知识库"""
    result = coze_request('DELETE', f'/v1/datasets/{dataset_id}')
    if result and result.get('code') == 0:
        return success_response(message='知识库删除成功')
    return error_response(f'删除失败: {result.get("msg") if result else "请求失败"}')


@app.route('/api/coze/knowledge/upload', methods=['POST'])
def coze_upload_document():
    """上传文档到扣子知识库"""
    data = request.json
    dataset_id = data.get('dataset_id')
    documents = data.get('documents', [])
    
    doc_bases = []
    for doc in documents:
        doc_bases.append({
            'name': doc.get('name', 'document'),
            'source_info': {
                'document_source': 0,
                'file_base64': doc.get('content_base64', ''),
                'file_type': doc.get('file_type', 'txt')
            }
        })
    
    payload = {
        'dataset_id': dataset_id,
        'document_bases': doc_bases,
        'chunk_strategy': {
            'chunk_type': 0
        }
    }
    result = coze_request('POST', '/open_api/knowledge/document/create', json=payload)
    if result and result.get('code') == 0:
        return success_response(data=result.get('data'), message='文档上传成功')
    return error_response(f'上传失败: {result.get("msg") if result else "请求失败"}')

@app.route('/api/coze/knowledge/sync', methods=['POST'])
def coze_sync_knowledge():
    """同步本地知识库文档到扣子"""
    data = request.json
    dataset_id = data.get('dataset_id')
    doc_ids = data.get('doc_ids', [])
    
    if not dataset_id:
        return error_response('请选择目标扣子知识库')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if doc_ids:
                format_strings = ','.join(['%s'] * len(doc_ids))
                cursor.execute(f"SELECT id, title, content FROM knowledge_documents WHERE id IN ({format_strings})", doc_ids)
            else:
                cursor.execute("SELECT id, title, content FROM knowledge_documents WHERE status = 1")
            docs = cursor.fetchall()
        
        import base64
        success_count = 0
        for doc in docs:
            content_b64 = base64.b64encode(doc['content'].encode('utf-8')).decode('utf-8')
            payload = {
                'dataset_id': dataset_id,
                'document_bases': [{
                    'name': doc['title'],
                    'source_info': {
                        'document_source': 0,
                        'file_base64': content_b64,
                        'file_type': 'txt'
                    }
                }],
                'chunk_strategy': {'chunk_type': 0}
            }
            result = coze_request('POST', '/open_api/knowledge/document/create', json=payload)
            if result and result.get('code') == 0:
                success_count += 1
                cursor2 = conn.cursor()
                cursor2.execute("UPDATE knowledge_documents SET coze_synced = 1 WHERE id = %s", (doc['id'],))
                conn.commit()
        
        return success_response(data={'synced': success_count, 'total': len(docs)}, message=f'成功同步{success_count}篇文档')
    finally:
        conn.close()

@app.route('/api/coze/config', methods=['GET'])
def get_coze_config():
    """获取扣子配置"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_key, config_value FROM system_config WHERE config_key LIKE 'coze_%'")
            configs = cursor.fetchall()
            config_dict = {c['config_key']: c['config_value'] for c in configs}
            return success_response(data=config_dict)
    finally:
        conn.close()

@app.route('/api/coze/config', methods=['POST'])
def save_coze_config():
    """保存扣子配置"""
    if session.get('user_type') != 'admin':
        return error_response('无权限', 403)
    
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for key, value in data.items():
                if key.startswith('coze_'):
                    cursor.execute("""
                        INSERT INTO system_config (config_key, config_value, description)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE config_value = %s
                    """, (key, value, f'扣子配置: {key}', value))
            conn.commit()
            return success_response(message='配置保存成功')
    finally:
        conn.close()

# ==================== 用户知识库管理 ====================

@app.route('/api/user/datasets/create', methods=['POST'])
def user_create_dataset():
    """用户创建知识库（同步到扣子平台）"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '')
    format_type = data.get('format_type', 0)  # 0-文本, 1-表格, 2-图片
    
    if not name:
        return error_response('知识库名称不能为空')
    
    # 获取space_id
    conn_cfg = get_db_connection()
    try:
        with conn_cfg.cursor() as cur:
            cur.execute("SELECT config_value FROM system_config WHERE config_key = 'coze_default_space_id'")
            row = cur.fetchone()
            space_id = row.get('config_value', '') if row else ''
    finally:
        conn_cfg.close()
    
    if not space_id:
        return error_response('系统未配置扣子工作空间ID，请联系管理员')
    
    # 调用Coze API创建知识库
    payload = {
        'name': name,
        'space_id': space_id,
        'format_type': format_type,
        'description': description
    }
    result = coze_request('POST', '/v1/datasets', json=payload)
    
    if not result or result.get('code') != 0:
        msg = result.get('msg', '创建失败') if result else '请求失败'
        return error_response(f'创建知识库失败: {msg}')
    
    dataset_id = result.get('data', {}).get('dataset_id', '')
    
    # 保存到本地数据库
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """INSERT INTO user_datasets (user_id, name, description, format_type, coze_dataset_id)
                     VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(sql, (user_id, name, description, format_type, dataset_id))
            conn.commit()
            local_id = cursor.lastrowid
            return success_response(data={
                'id': local_id,
                'coze_dataset_id': dataset_id
            }, message='知识库创建成功')
    finally:
        conn.close()


@app.route('/api/user/datasets/list', methods=['GET'])
def user_list_datasets():
    """用户获取自己的知识库列表"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_datasets WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            datasets = cursor.fetchall()
            return success_response(data=datasets)
    finally:
        conn.close()


@app.route('/api/user/datasets/delete/<int:dataset_local_id>', methods=['DELETE'])
def user_delete_dataset(dataset_local_id):
    """用户删除知识库"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_datasets WHERE id = %s AND user_id = %s", (dataset_local_id, user_id))
            dataset = cursor.fetchone()
            if not dataset:
                return error_response('知识库不存在')
            
            coze_dataset_id = dataset.get('coze_dataset_id', '')
            
            # 调用Coze API删除
            if coze_dataset_id:
                result = coze_request('DELETE', f'/v1/datasets/{coze_dataset_id}')
                print(f'[Coze] Delete dataset {coze_dataset_id}: {result}')
            
            # 删除本地记录
            cursor.execute("DELETE FROM user_datasets WHERE id = %s", (dataset_local_id,))
            conn.commit()
            return success_response(message='知识库删除成功')
    finally:
        conn.close()


@app.route('/api/user/datasets/<int:dataset_local_id>/files/list', methods=['GET'])
def user_list_dataset_files(dataset_local_id):
    """查看知识库文件列表"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_datasets WHERE id = %s AND user_id = %s", (dataset_local_id, user_id))
            dataset = cursor.fetchone()
            if not dataset:
                return error_response('知识库不存在')
            
            coze_dataset_id = dataset.get('coze_dataset_id', '')
            if not coze_dataset_id:
                return success_response(data={'document_infos': [], 'total': 0})
            
            page = int(request.args.get('page', 1))
            size = int(request.args.get('size', 20))
            
            # 调用Coze API列出文件
            payload = {
                'dataset_id': coze_dataset_id,
                'page': page,
                'size': size
            }
            result = coze_request('POST', '/open_api/knowledge/document/list', json=payload)
            
            if result and result.get('code') == 0:
                return success_response(data={
                    'document_infos': result.get('data', {}).get('document_infos', result.get('document_infos', [])),
                    'total': result.get('data', {}).get('total', 0),
                    'dataset': dataset
                })
            else:
                return success_response(data={'document_infos': [], 'total': 0, 'dataset': dataset})
    finally:
        conn.close()


@app.route('/api/user/datasets/<int:dataset_local_id>/files/create', methods=['POST'])
def user_create_dataset_file(dataset_local_id):
    """在知识库中创建文件"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_datasets WHERE id = %s AND user_id = %s", (dataset_local_id, user_id))
            dataset = cursor.fetchone()
            if not dataset:
                return error_response('知识库不存在')
            
            coze_dataset_id = dataset.get('coze_dataset_id', '')
            if not coze_dataset_id:
                return error_response('知识库未关联扣子平台')
            
            data = request.json
            doc_name = data.get('name', '').strip()
            doc_content = data.get('content', '')
            source_type = data.get('source_type', 'text')  # text / url
            
            if not doc_name:
                return error_response('文件名称不能为空')
            
            import base64
            
            if source_type == 'url':
                # 在线网页类型
                url = data.get('url', '').strip()
                if not url:
                    return error_response('URL不能为空')
                document_base = {
                    'name': doc_name,
                    'source_info': {
                        'web_url': url,
                        'document_source': 1
                    }
                }
            else:
                # 文本类型 -> 转为base64上传为txt文件
                if not doc_content:
                    return error_response('文件内容不能为空')
                content_b64 = base64.b64encode(doc_content.encode('utf-8')).decode('utf-8')
                document_base = {
                    'name': doc_name,
                    'source_info': {
                        'file_base64': content_b64,
                        'file_type': 'txt',
                        'document_source': 0
                    }
                }
            
            payload = {
                'dataset_id': str(coze_dataset_id),
                'document_bases': [document_base],
                'format_type': 0,
                'chunk_strategy': {
                    'separator': '\n\n',
                    'max_tokens': 800,
                    'remove_extra_spaces': False,
                    'remove_urls_emails': False,
                    'chunk_type': 1
                }
            }
            
            print(f'[Coze Knowledge] Creating file: name={doc_name}, dataset_id={coze_dataset_id}, source_type={source_type}')
            print(f'[Coze Knowledge] Full payload: {json.dumps(payload, ensure_ascii=False)[:500]}')
            
            result = coze_request('POST', '/open_api/knowledge/document/create', json=payload)
            
            print(f'[Coze Knowledge] Result: {result}')
            
            if result and result.get('code') == 0:
                doc_infos = result.get('document_infos', result.get('data', {}).get('document_infos', []))
                return success_response(data={'document_infos': doc_infos}, message='文件创建成功')
            else:
                msg = result.get('msg', '创建失败') if result else '请求失败'
                return error_response(f'创建文件失败: {msg}')
    finally:
        conn.close()


@app.route('/api/user/datasets/<int:dataset_local_id>/files/delete', methods=['POST'])
def user_delete_dataset_file(dataset_local_id):
    """删除知识库文件"""
    user_id = session.get('user_id')
    if not user_id:
        return error_response('未登录', 401)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_datasets WHERE id = %s AND user_id = %s", (dataset_local_id, user_id))
            dataset = cursor.fetchone()
            if not dataset:
                return error_response('知识库不存在')
            
            data = request.json
            document_ids = data.get('document_ids', [])
            
            if not document_ids:
                return error_response('请选择要删除的文件')
            
            # 调用Coze API删除
            payload = {
                'document_ids': document_ids
            }
            result = coze_request('POST', '/open_api/knowledge/document/delete', json=payload)
            
            if result and result.get('code') == 0:
                return success_response(message='文件删除成功')
            else:
                msg = result.get('msg', '删除失败') if result else '请求失败'
                return error_response(f'删除文件失败: {msg}')
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
