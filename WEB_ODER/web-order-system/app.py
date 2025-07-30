
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# --- Database Models ---
class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=100)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(50), nullable=False)
    items = db.Column(db.String(500), nullable=False) # JSON string of items
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='접수') # 접수 -> 조리중 -> 완료

# --- Customer Routes ---
@app.route('/')
def index():
    return redirect(url_for('menu'))

@app.route('/menu')
def menu():
    menu_items = Menu.query.all()
    return render_template('menu.html', menu_items=menu_items)

@app.route('/cart')
def cart():
    return render_template('cart.html')

import json

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

@app.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    table_number = data['table_number']
    cart = data['cart']

    items_str = json.dumps(cart)
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())

    new_order = Order(table_number=table_number, items=items_str, total_price=total_price)
    db.session.add(new_order)
    db.session.commit()

    # Notify admin page
    socketio.emit('new_order', {'order_id': new_order.id, 'table_number': new_order.table_number})

    return {'success': True}

@app.route('/complete')
def complete():
    return render_template('complete.html')

# --- Admin Routes ---
from flask import jsonify

@app.route('/admin/orders')
def admin_orders():
    return render_template('admin_orders.html')

@app.route('/get_orders')
def get_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return jsonify({'orders': [{'id': o.id, 'table_number': o.table_number, 'status': o.status} for o in orders]})

@app.route('/admin/orders/<int:id>', methods=['GET', 'POST'])
def admin_order_detail(id):
    order = Order.query.get_or_404(id)
    if request.method == 'POST':
        order.status = request.form['status']
        db.session.commit()
        # Notify status change
        socketio.emit('status_update', {'order_id': order.id, 'status': order.status})
        return redirect(url_for('admin_orders'))

    order_items = json.loads(order.items)
    return render_template('admin_order_detail.html', order=order, items=order_items)

@app.route('/admin/menu')
def admin_menu():
    menu_items = Menu.query.all()
    return render_template('admin_menu.html', menu_items=menu_items)

@app.route('/admin/menu/create', methods=['POST'])
def admin_menu_create():
    name = request.form['name']
    price = request.form['price']
    stock = request.form['stock']
    new_menu = Menu(name=name, price=price, stock=stock)
    db.session.add(new_menu)
    db.session.commit()
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:id>')
def admin_menu_delete(id):
    menu_item = Menu.query.get_or_404(id)
    db.session.delete(menu_item)
    db.session.commit()
    return redirect(url_for('admin_menu'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
