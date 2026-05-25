import os
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# 設定 Secret Key 供 Session 使用
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# 設定資料庫：優先讀取環境變數 DATABASE_URL (Neon 提供)，若無則使用 SQLite 供本地測試
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==========================================
# 資料庫模型 (Models)
# ==========================================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), default='茶飲')

# 系統啟動時初始化資料庫
with app.app_context():
    db.create_all()
    # 預設加入一些測試商品
    if Product.query.count() == 0:
        db.session.add_all([
            Product(name="波霸奶茶", price=50, category="奶茶"),
            Product(name="四季春青茶", price=30, category="原茶"),
            Product(name="紅茶瑪奇朵", price=55, category="瑪奇朵")
        ])
        db.session.commit()

# ==========================================
# 視覺樣式與模板 (HTML/CSS)
# 主色：酒紅色 (#722F37 / #800020)
# ==========================================
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>專業飲品 POS 系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-wine: #800020; /* 酒紅色主色 */
            --secondary-wine: #5e0017;
            --accent-gold: #D4AF37; /* 專業感點綴 */
            --bg-light: #f8f9fa;
        }
        body { background-color: var(--bg-light); font-family: 'Helvetica Neue', Arial, sans-serif; }
        .bg-wine { background-color: var(--primary-wine) !important; color: white; }
        .text-wine { color: var(--primary-wine) !important; }
        .btn-wine { background-color: var(--primary-wine); color: white; border: none; }
        .btn-wine:hover { background-color: var(--secondary-wine); color: white; }
        .navbar { box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card { border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 10px; }
        .item-card { cursor: pointer; transition: transform 0.2s; }
        .item-card:hover { transform: scale(1.02); border: 1px solid var(--primary-wine); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg bg-wine">
        <div class="container-fluid">
            <a class="navbar-brand text-white fw-bold" href="{{ url_for('pos_frontend') }}">🍵 飲品 POS 系統</a>
            <div class="d-flex text-white">
                {% if session.get('logged_in') %}
                    <a href="{{ url_for('pos_frontend') }}" class="btn btn-outline-light me-2 btn-sm">前台點餐</a>
                    <a href="{{ url_for('admin_dashboard') }}" class="btn btn-outline-light me-2 btn-sm">後台管理</a>
                    <a href="{{ url_for('logout') }}" class="btn btn-light btn-sm text-wine fw-bold">登出</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row justify-content-center mt-5">
    <div class="col-md-4">
        <div class="card p-4">
            <h3 class="text-center text-wine mb-4 fw-bold">系統登入</h3>
            {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">帳號</label>
                    <input type="text" name="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">密碼</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-wine w-100 fw-bold">登入</button>
            </form>
        </div>
    </div>
</div>
""")

POS_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row">
    <div class="col-md-8">
        <h4 class="text-wine fw-bold mb-3">飲品選單</h4>
        <div class="row g-3">
            {% for p in products %}
            <div class="col-md-4">
                <div class="card item-card p-3 text-center h-100" onclick="addToCart('{{ p.name }}', {{ p.price }})">
                    <h5 class="fw-bold">{{ p.name }}</h5>
                    <span class="badge bg-secondary mb-2">{{ p.category }}</span>
                    <h4 class="text-wine mb-0">${{ p.price }}</h4>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    <div class="col-md-4">
        <div class="card p-3 h-100 sticky-top" style="top: 20px;">
            <h4 class="text-wine fw-bold mb-3">目前訂單</h4>
            <ul id="cartList" class="list-group mb-3" style="min-height: 200px; max-height: 400px; overflow-y: auto;">
                </ul>
            <hr>
            <div class="d-flex justify-content-between mb-3">
                <span class="fs-5 fw-bold">總計:</span>
                <span class="fs-4 fw-bold text-wine" id="totalPrice">$0</span>
            </div>
            <button class="btn btn-wine w-100 py-2 fs-5 fw-bold" onclick="checkout()">結帳 (列印單據)</button>
            <button class="btn btn-outline-danger w-100 mt-2" onclick="clearCart()">清空</button>
        </div>
    </div>
</div>
""").replace("{% block scripts %}{% endblock %}", """
<script>
    let cart = [];
    function addToCart(name, price) {
        cart.push({name, price});
        renderCart();
    }
    function renderCart() {
        const list = document.getElementById('cartList');
        let total = 0;
        list.innerHTML = '';
        cart.forEach((item, index) => {
            total += item.price;
            list.innerHTML += `<li class="list-group-item d-flex justify-content-between align-items-center">
                ${item.name} 
                <div>
                    <span class="me-3 text-wine fw-bold">$${item.price}</span>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeItem(${index})">X</button>
                </div>
            </li>`;
        });
        document.getElementById('totalPrice').innerText = '$' + total;
    }
    function removeItem(index) {
        cart.splice(index, 1);
        renderCart();
    }
    function clearCart() {
        cart = [];
        renderCart();
    }
    function checkout() {
        if(cart.length === 0) return alert('購物車是空的！');
        alert('結帳成功！總金額：$' + cart.reduce((a,b)=>a+b.price, 0) + '\\n(此處可串接後端儲存訂單與列印邏輯)');
        clearCart();
    }
</script>
""")

ADMIN_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row">
    <div class="col-md-12">
        <h4 class="text-wine fw-bold mb-4">後台商品管理</h4>
        <div class="card p-4 mb-4">
            <form method="POST" action="{{ url_for('add_product') }}" class="row g-3 align-items-end">
                <div class="col-md-4">
                    <label class="form-label">商品名稱</label>
                    <input type="text" name="name" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <label class="form-label">分類</label>
                    <input type="text" name="category" class="form-control" required>
                </div>
                <div class="col-md-3">
                    <label class="form-label">價格</label>
                    <input type="number" name="price" class="form-control" required>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-wine w-100">新增商品</button>
                </div>
            </form>
        </div>
        
        <table class="table table-hover bg-white shadow-sm rounded">
            <thead class="bg-wine text-white">
                <tr>
                    <th>ID</th>
                    <th>名稱</th>
                    <th>分類</th>
                    <th>價格</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for p in products %}
                <tr>
                    <td>{{ p.id }}</td>
                    <td class="fw-bold">{{ p.name }}</td>
                    <td>{{ p.category }}</td>
                    <td class="text-wine fw-bold">${{ p.price }}</td>
                    <td>
                        <a href="{{ url_for('delete_product', id=p.id) }}" class="btn btn-sm btn-outline-danger">刪除</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
""")

# ==========================================
# 路由邏輯 (Routes)
# ==========================================
@app.before_request
def check_login():
    # 保護所有路由，除了登入頁面與靜態檔案
    if request.endpoint and request.endpoint != 'login' and request.endpoint != 'static':
        if not session.get('logged_in'):
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # 預設帳號密碼 admin / admin
        if username == 'admin' and password == 'admin':
            session['logged_in'] = True
            return redirect(url_for('pos_frontend'))
        else:
            error = '帳號或密碼錯誤'
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def pos_frontend():
    products = Product.query.all()
    return render_template_string(POS_TEMPLATE, products=products)

@app.route('/admin')
def admin_dashboard():
    products = Product.query.all()
    return render_template_string(ADMIN_TEMPLATE, products=products)

@app.route('/admin/add', methods=['POST'])
def add_product():
    name = request.form['name']
    category = request.form['category']
    price = request.form['price']
    new_product = Product(name=name, category=category, price=int(price))
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # 本地測試時執行
    app.run(debug=True)