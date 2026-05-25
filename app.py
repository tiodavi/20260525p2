import os
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# 資料庫設定 (Neon / SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pos_v2.db')
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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan", lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    # 新增客製化標籤欄位
    sweetness = db.Column(db.String(30), nullable=False) # 正常糖/半糖...
    ice_level = db.Column(db.String(30), nullable=False) # 正常冰/微冰...
    toppings = db.Column(db.String(100), default='')     # 加波霸/加椰果...

# 初始化資料庫與 50 嵐風格預設茶單
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        db.session.add_all([
            Product(name="茉莉綠茶", price=30, category="原茶"),
            Product(name="四季春青茶", price=30, category="原茶"),
            Product(name="波霸奶茶", price=50, category="奶茶"),
            Product(name="珍波椰青茶", price=50, category="混調"),
            Product(name="紅茶瑪奇朵", price=55, category="瑪奇朵"),
            Product(name="旺來紅", price=60, category="季節限定")
        ])
        db.session.commit()

# ==========================================
# 視覺樣式與模板 (專業酒紅色系)
# ==========================================
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>專業連鎖飲品 POS 系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-wine: #722F37;    /* 酒紅主色 */
            --dark-wine: #521e24;       /* 深酒紅 */
            --light-wine: #fcf6f6;      /* 淡淡酒紅襯底 */
            --accent-gold: #C5A059;     /* 輔助金色 */
        }
        body { background-color: #fdfdfd; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }
        .bg-wine { background-color: var(--primary-wine) !important; color: white; }
        .text-wine { color: var(--primary-wine) !important; }
        .btn-wine { background-color: var(--primary-wine); color: white; border: none; font-weight: 600; }
        .btn-wine:hover { background-color: var(--dark-wine); color: white; }
        .btn-outline-wine { border: 1px solid var(--primary-wine); color: var(--primary-wine); font-weight: 500; }
        .btn-outline-wine:hover, .btn-check:checked + .btn-outline-wine { background-color: var(--primary-wine); color: white; }
        .navbar { box-shadow: 0 2px 12px rgba(114,47,55,0.15); }
        .card { border: 1px solid #eee; box-shadow: 0 4px 10px rgba(0,0,0,0.03); border-radius: 12px; }
        .item-card { cursor: pointer; transition: all 0.2s ease-in-out; background: #fff; }
        .item-card:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(114,47,55,0.12); border-color: var(--primary-wine); }
        .nav-tabs .nav-link.active { background-color: var(--primary-wine); color: white; border: none; }
        .nav-tabs .nav-link { color: var(--primary-wine); font-weight: bold; }
        .sticky-cart { position: sticky; top: 24px; max-height: calc(100vh - 100px); display: flex; flex-direction: column; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg bg-wine mb-4">
        <div class="container-fluid">
            <a class="navbar-brand text-white fw-bold fs-4" href="{{ url_for('pos_frontend') }}">🍷 Premium POS 飲品系統</a>
            <div class="d-flex">
                {% if session.get('logged_in') %}
                    <a href="{{ url_for('pos_frontend') }}" class="btn btn-outline-light me-2 btn-sm px-3">前台點餐系統</a>
                    <a href="{{ url_for('admin_dashboard') }}" class="btn btn-outline-light me-2 btn-sm px-3">後台決策管理</a>
                    <a href="{{ url_for('logout') }}" class="btn btn-light btn-sm text-wine fw-bold px-3">安全登出</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container-fluid px-4">
        {% block content %}{% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row justify-content-center" style="margin-top: 8%;">
    <div class="col-md-4 col-sm-8">
        <div class="card p-4 shadow">
            <div class="text-center mb-4">
                <h3 class="text-wine fw-bold">智能收銀系統</h3>
                <small class="text-muted">請輸入憑證以存取前/後台</small>
            </div>
            {% if error %}<div class="alert alert-danger py-2 fs-6">{{ error }}</div>{% endif %}
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label fw-bold">管理員帳號</label>
                    <input type="text" name="username" class="form-control" placeholder="預設：admin" required>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-bold">密碼</label>
                    <input type="password" name="password" class="form-control" placeholder="預設：admin" required>
                </div>
                <button type="submit" class="btn btn-wine w-100 py-2 fs-5">驗證並登入</button>
            </form>
        </div>
    </div>
</div>
""")

POS_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row">
    <div class="col-lg-8 col-md-7">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="text-wine fw-bold m-0">Menu / 飲品選單</h4>
        </div>
        <div class="row g-3">
            {% for p in products %}
            <div class="col-xl-3 col-lg-4 col-sm-6">
                <div class="card item-card p-3 h-100" onclick="openCustomizeModal('{{ p.name }}', {{ p.price }})">
                    <span class="badge bg-light text-wine border align-self-start mb-2">{{ p.category }}</span>
                    <h5 class="fw-bold text-dark mb-1">{{ p.name }}</h5>
                    <div class="text-end mt-auto">
                        <span class="fs-4 fw-bold text-wine">${{ p.price }}</span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="col-lg-4 col-md-5">
        <div class="card p-3 sticky-cart shadow-sm bg-white">
            <h4 class="text-wine fw-bold mb-3 pb-2 border-bottom">Current Order / 當前訂單</h4>
            <div id="cartList" class="list-group flex-grow-1 my-2" style="overflow-y: auto; min-height: 250px; max-height: calc(100vh - 350px);">
                </div>
            <div class="border-top pt-3">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <span class="fs-5 fw-bold">應收總計:</span>
                    <span class="fs-3 fw-bold text-wine" id="totalPrice">$0</span>
                </div>
                <button class="btn btn-wine w-100 py-3 fs-5" onclick="checkout()">確認結帳 (傳送至資料庫)</button>
                <button class="btn btn-link text-danger w-100 mt-2 btn-sm" onclick="clearCart()">清空當前購物車</button>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="customModal" data-bs-backdrop="static" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header bg-wine text-white">
                <h5 class="modal-title fw-bold" id="modalProductName">飲品規格客製化</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="mb-4">
                    <label class="form-label fw-bold border-start border-4 border-danger ps-2 text-dark">1. 選擇糖分 (Sweetness)</label>
                    <div class="row g-2 mt-1">
                        {% for s in ['正常糖', '少糖(7分)', '半糖(5分)', '微糖(3分)', '無糖'] %}
                        <div class="col-4">
                            <input type="radio" class="btn-check" name="sweetness" id="sweet_{{loop.index}}" value="{{s}}" {% if loop.index==4 %}checked{% endif %}>
                            <label class="btn btn-outline-wine w-100 btn-sm py-2" for="sweet_{{loop.index}}">{{s}}</label>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label fw-bold border-start border-4 border-danger ps-2 text-dark">2. 選擇冰量 (Ice Level)</label>
                    <div class="row g-2 mt-1">
                        {% for i in ['正常冰', '少冰', '微冰', '去冰', '常溫', '熱飲'] %}
                        <div class="col-4">
                            <input type="radio" class="btn-check" name="ice" id="ice_{{loop.index}}" value="{{i}}" {% if loop.index==3 %}checked{% endif %}>
                            <label class="btn btn-outline-wine w-100 btn-sm py-2" for="ice_{{loop.index}}">{{i}}</label>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div class="mb-2">
                    <label class="form-label fw-bold border-start border-4 border-danger ps-2 text-dark">3. 加料加價 (+ $10)</label>
                    <div class="row g-2 mt-1">
                        {% for t in ['波霸', '珍珠', '椰果', '仙草凍', '燕麥'] %}
                        <div class="col-4">
                            <input type="checkbox" class="btn-check" name="topping" id="top_{{loop.index}}" value="{{t}}">
                            <label class="btn btn-outline-wine w-100 btn-sm py-2" for="top_{{loop.index}}">+ {{t}}</label>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div class="modal-footer bg-light">
                <button type="button" class="btn btn-secondary px-4" data-bs-dismiss="modal">取消</button>
                <button type="button" class="btn btn-wine px-5" onclick="confirmAddToCart()">加入清單</button>
            </div>
        </div>
    </div>
</div>
""").replace("{% block scripts %}{% endblock %}", """
<script>
    let cart = [];
    let currentItem = null;
    let customModalInstance = null;

    document.addEventListener("DOMContentLoaded", function() {
        customModalInstance = new bootstrap.Modal(document.getElementById('customModal'));
    });

    // 點擊商品：暫存基本資訊並彈出規格視窗
    function openCustomizeModal(name, price) {
        currentItem = { name, price };
        document.getElementById('modalProductName').innerText = `客製規格：${name} ($${price})`;
        
        // 重置加料勾選狀態
        document.querySelectorAll('input[name="topping"]').forEach(cb => cb.checked = false);
        
        customModalInstance.show();
    }

    // 規格視窗點擊確認：計算加價並塞入購物車陣列
    function confirmAddToCart() {
        const selectedSweetness = document.querySelector('input[name="sweetness"]:checked').value;
        const selectedIce = document.querySelector('input[name="ice"]:checked').value;
        
        let toppings = [];
        let toppingPrice = 0;
        document.querySelectorAll('input[name="topping"]:checked').forEach(cb => {
            toppings.push(cb.value);
            toppingPrice += 10; // 每項配料加 10 元
        });

        // 檢查購物車中是否已有「完全相同規格」的飲品
        let finalPrice = currentItem.price + toppingPrice;
        let toppingsStr = toppings.join(',');

        let found = cart.find(item => 
            item.name === currentItem.name && 
            item.sweetness === selectedSweetness && 
            item.ice_level === selectedIce && 
            item.toppings === toppingsStr
        );

        if (found) {
            found.quantity += 1;
        } else {
            cart.push({
                name: currentItem.name,
                price: finalPrice,
                sweetness: selectedSweetness,
                ice_level: selectedIce,
                toppings: toppingsStr,
                quantity: 1
            });
        }

        customModalInstance.hide();
        renderCart();
    }

    // 渲染購物車介面
    function renderCart() {
        const list = document.getElementById('cartList');
        let total = 0;
        list.innerHTML = '';

        cart.forEach((item, index) => {
            let itemTotal = item.price * item.quantity;
            total += itemTotal;

            let toppingBadge = item.toppings ? `<span class="badge bg-warning text-dark me-1">+${item.toppings.replace(/,/g, '/')}</span>` : '';

            list.innerHTML += `
            <div class="list-group-item d-flex justify-content-between align-items-start p-2 mb-2 border rounded bg-light">
                <div class="ms-2 me-auto">
                    <div class="fw-bold text-dark">${item.name} <span class="text-wine">x${item.quantity}</span></div>
                    <div class="mt-1">
                        <span class="badge bg-wine text-white me-1">${item.sweetness}</span>
                        <span class="badge bg-secondary text-white me-1">${item.ice_level}</span>
                        ${toppingBadge}
                    </div>
                </div>
                <div class="text-end">
                    <span class="fw-bold text-wine d-block">$${itemTotal}</span>
                    <button class="btn btn-sm text-danger p-0 border-0 mt-1" onclick="removeItem(${index})">移除</button>
                </div>
            </div>`;
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

    // 將包含規格的點餐清單發送到後端寫入資料庫
    function checkout() {
        if(cart.length === 0) return alert('當前訂單無任何品項。');
        
        fetch('/api/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: cart })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                alert(`✨ 結帳成功！\\n訂單編號: #${data.order_id}\\n點餐清單已成功存入 Neon 雲端資料庫。`);
                clearCart();
            } else {
                alert('交易失敗：' + data.message);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系統連線異常，請檢查網路。');
        });
    }
</script>
""")

ADMIN_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<div class="row">
    <div class="col-md-12">
        <ul class="nav nav-tabs mb-4" id="adminTab" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="orders-tab" data-bs-toggle="tab" data-bs-target="#orders" type="button">🧾 即時訂單銷貨紀錄</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="products-tab" data-bs-toggle="tab" data-bs-target="#products" type="button">📦 飲品品項維護</button>
            </li>
        </ul>
        
        <div class="tab-content" id="adminTabContent">
            <div class="tab-pane fade show active" id="orders">
                <h5 class="text-wine fw-bold mb-3">營運歷史紀錄 (最新排前)</h5>
                {% for o in orders %}
                <div class="card mb-3 p-3 bg-white">
                    <div class="d-flex justify-content-between align-items-center bg-light p-3 rounded">
                        <div>
                            <span class="badge bg-wine fs-6 me-2">單號 #{{ o.id }}</span>
                            <span class="text-muted fw-medium">交易時間：{{ o.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</span>
                        </div>
                        <span class="fs-4 fw-bold text-wine">總應收：${{ o.total_price }}</span>
                    </div>
                    <div class="mt-3 table-responsive px-2">
                        <table class="table table-sm table-borderless align-middle mb-0">
                            <thead class="text-secondary border-bottom">
                                <tr><th>品項名稱</th><th>客製化規格 (糖分/冰量/加料)</th><th>數量</th><th>單杯小計</th></tr>
                            </thead>
                            <tbody>
                                {% for item in o.items %}
                                <tr>
                                    <td class="fw-bold text-dark" style="width: 25%;">{{ item.product_name }}</td>
                                    <td>
                                        <span class="badge bg-wine me-1">{{ item.sweetness }}</span>
                                        <span class="badge bg-secondary me-1">{{ item.ice_level }}</span>
                                        {% if item.toppings %}
                                        <span class="badge bg-warning text-dark">+{{ item.toppings.replace(/,/g, ' +') }}</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-dark fw-bold">x {{ item.quantity }}</td>
                                    <td class="text-wine fw-bold">${{ item.price * item.quantity }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
                {% else %}
                <div class="alert alert-light text-center py-4 border">目前暫無銷售紀錄，請至前台模擬點餐結帳。</div>
                {% endfor %}
            </div>
            
            <div class="tab-pane fade" id="products">
                <div class="card p-4 mb-4 bg-light">
                    <h5 class="text-wine fw-bold mb-3">上架新飲品</h5>
                    <form method="POST" action="{{ url_for('add_product') }}" class="row g-3 align-items-end">
                        <div class="col-md-4"><label class="form-label fw-bold">品名</label><input type="text" name="name" class="form-control" required></div>
                        <div class="col-md-3"><label class="form-label fw-bold">系列分類</label><input type="text" name="category" class="form-control" placeholder="如：原茶/奶茶" required></div>
                        <div class="col-md-3"><label class="form-label fw-bold">基準售價</label><input type="number" name="price" class="form-control" required></div>
                        <div class="col-md-2"><button type="submit" class="btn btn-wine w-100 py-2">確認上架</button></div>
                    </form>
                </div>
                
                <table class="table table-hover bg-white border">
                    <thead class="bg-wine text-white">
                        <tr><th>商品識別碼</th><th>飲品名稱</th><th>系列歸屬</th><th>基準價格</th><th>營運操作</th></tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td>{{ p.id }}</td>
                            <td class="fw-bold">{{ p.name }}</td>
                            <td><span class="badge bg-light text-dark border">{{ p.category }}</span></td>
                            <td class="text-wine fw-bold">${{ p.price }}</td>
                            <td><a href="{{ url_for('delete_product', id=p.id) }}" class="btn btn-sm btn-outline-danger">淘汰下架</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
""")

# ==========================================
# 路由與 控制 API 核心 (Controller)
# ==========================================
@app.before_request
def check_login():
    if request.endpoint and request.endpoint not in ['login', 'static'] and not request.endpoint.startswith('api'):
        if not session.get('logged_in'):
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['logged_in'] = True
            return redirect(url_for('pos_frontend'))
        error = '認證失敗：帳號或密碼不正確。'
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
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template_string(ADMIN_TEMPLATE, products=products, orders=orders)

@app.route('/admin/add', methods=['POST'])
def add_product():
    new_product = Product(
        name=request.form['name'], 
        category=request.form['category'], 
        price=int(request.form['price'])
    )
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ------------------------------------------
# 客製化結帳核心 API (含客製屬性處理)
# ------------------------------------------
@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    data = request.get_json()
    if not data or 'items' not in data or len(data['items']) == 0:
        return jsonify({'success': False, 'message': '無效的點餐清單'}), 400
    
    try:
        # 計算整筆訂單總和
        total = sum(item['price'] * item['quantity'] for item in data['items'])
        
        # 建立訂單主檔
        new_order = Order(total_price=total)
        db.session.add(new_order)
        db.session.flush() 
        
        # 逐筆寫入帶有「糖分」、「冰量」、「加料」的訂單明細
        for item in data['items']:
            order_item = OrderItem(
                order_id=new_order.id,
                product_name=item['name'],
                price=item['price'],
                quantity=item['quantity'],
                sweetness=item['sweetness'],
                ice_level=item['ice_level'],
                toppings=item.get('toppings', '')
            )
            db.session.add(order_item)
            
        db.session.commit()
        return jsonify({'success': True, 'order_id': new_order.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
