from flask import Blueprint, render_template, redirect, url_for, flash, request,current_app
from flask_login import login_user, logout_user, login_required, current_user
from db import db
import os
from models import User, Product, CartItem, Order, OrderItem, SQLQueryLog
from config import Config
from werkzeug.utils import secure_filename
from sqlalchemy import text
app_routes = Blueprint("app_routes", __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# =======================
# 📌 Главная страница
# =======================
@app_routes.route('/')
def home():
    products = Product.query.all()
    return render_template('index.html', products=products)


# =======================
# 📌 Регистрация
# =======================
@app_routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email уже используется!', 'danger')
            return redirect(url_for('app_routes.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('app_routes.login'))

    return render_template('register.html')


# =======================
# 📌 Авторизация
# =======================
@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('app_routes.home'))
        else:
            flash('Неверные данные!', 'danger')

    return render_template('login.html')


# =======================
# 📌 Выход из аккаунта
# =======================
@app_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('app_routes.home'))


# =======================
# 📌 Страница товара
# =======================
@app_routes.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = product.reviews  # Получение отзывов
    return render_template('product_detail.html', product=product, reviews=reviews)


# =======================
# 📌 Добавление в корзину
# =======================
@app_routes.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    flash('Товар добавлен в корзину!', 'success')
    return redirect(url_for('app_routes.cart'))


# =======================
# 📌 Корзина
# =======================
@app_routes.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

# =======================
# 📌 Удаление из корзины
# =======================
@app_routes.route('/cart/remove/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    try:
        cart_item = CartItem.query.get(cart_item_id)
        if cart_item and cart_item.user_id == current_user.id:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Товар удален из корзины', 'success')
        else:
            flash('Ошибка: товар не найден или не принадлежит вам', 'danger')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при удалении товара', 'danger')

    return redirect(url_for('app_routes.cart'))

# =======================
# 📌 Оформление заказа
# =======================
@app_routes.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Ваша корзина пуста!', 'danger')
        return redirect(url_for('app_routes.cart'))

    total_price = sum(item.product.price * item.quantity for item in cart_items)

    order = Order(user_id=current_user.id, total_price=total_price)
    db.session.add(order)
    db.session.flush()  # Получаем ID заказа

    for item in cart_items:
        product = Product.query.get(item.product_id)

        if product and product.stock >= item.quantity:
            # Уменьшаем количество доступных товаров
            product.stock -= item.quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                subtotal=item.product.price * item.quantity
            )
            db.session.add(order_item)
        else:
            flash(f'Недостаточно товара "{product.name}" в наличии!', 'danger')
            db.session.rollback()  # Откат, если товара недостаточно
            return redirect(url_for('app_routes.cart'))

    # Очистка корзины
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash('Заказ успешно оформлен!', 'success')
    return redirect(url_for('app_routes.orders'))


# =======================
# 📌 Мои заказы
# =======================
@app_routes.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=user_orders)


# =======================
# 📌 Панель администратора
# =======================
@app_routes.route('/admin')
@login_required
def admin_panel():
    if current_user.role != "admin":
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))
    orders = Order.query.all()
    products = Product.query.all()
    users = User.query.all()
    return render_template('admin.html', products=products, users=users, orders=orders)


# =======================
# 📌 SQL Запрос от Админа
# =======================
@app_routes.route('/admin/sql', methods=['GET', 'POST'])
@login_required
def admin_sql():
    if current_user.role != "admin":
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    results = None
    query = ""

    if request.method == 'POST':
        query = request.form['query']

        try:
            results = db.session.execute(text(query)).fetchall()
            log = SQLQueryLog(query=query)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            flash(f'Ошибка в запросе: {str(e)}', 'danger')

    return render_template('admin_sql.html', results=results, query=query)


# =======================
# 📌 Редактирование пользователя
# =======================
@app_routes.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required  # Убедимся, что пользователь авторизован
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.role != 'admin':
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))  # Если не текущий пользователь и не админ, редирект на главную

    if request.method == 'POST':
        # Обновляем данные пользователя
        user.username = request.form['username']
        user.email = request.form['email']

        # Обновление пароля
        if request.form['password']:
            user.set_password(request.form['password'])

        db.session.commit()
        return redirect(url_for('app_routes.user_detail', user_id=user.id))

    return render_template('user_detail_admin.html', user=user)

# =======================
# 📌 Добавление продукта
# =======================
@app_routes.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    if current_user.role != "admin":
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    stock = int(request.form['stock'])

    # Загрузка изображения, если оно есть
    image_filename = 'default.jpg'  # Изображение по умолчанию
    if 'image' in request.files:
        image = request.files['image']
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(Config.UPLOAD_FOLDER, image_filename))

    # Создание нового продукта
    new_product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        image=image_filename
    )

    try:
        db.session.add(new_product)
        db.session.commit()
        flash('Продукт успешно добавлен', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при добавлении продукта', 'danger')

    return redirect(url_for('app_routes.admin_panel'))

# =======================
# 📌 Редактирование продукта
# =======================
@app_routes.route('/admin/product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def product_detail_admin(product_id):
    if current_user.role != "admin":
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        # Обновляем данные продукта
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])

        # Загружаем новое изображение, если есть
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '' and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                image.save(image_path)
                product.image = filename

        db.session.commit()
        return redirect(url_for('app_routes.product_detail_admin', product_id=product.id))

    return render_template('product_detail_admin.html', product=product)

# =======================
# 📌 Удаление продукта
# =======================
@app_routes.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != "admin":
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    product = Product.query.get_or_404(product_id)

    try:
        # Удаляем изображение, если оно есть
        if product.image:
            image_path = os.path.join(current_app.root_path, Config.UPLOAD_FOLDER, product.image)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(product)
        db.session.commit()
        flash('Продукт успешно удален', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Произошла ошибка при удалении продукта: {e}", 'danger')

    return redirect(url_for('app_routes.admin_panel'))

# =======================
# 📌 Удаление пользователя
# =======================
@app_routes.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id and current_user.role != 'admin':
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('Пользователь успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при удалении пользователя', 'danger')
    return redirect(url_for('app_routes.admin_panel'))


# =======================
# 📌 Просмотр заказа
# =======================
@app_routes.route('/admin/order/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_detail.html', order=order)


# =======================
# 📌 Смена статуса заказа
# =======================
@app_routes.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    order = Order.query.get_or_404(order_id)

    new_status = request.form.get('status')
    if new_status not in ["new", "processed", "shipped", "completed"]:
        flash('Некорректный статус заказа!', 'danger')
        return redirect(url_for('app_routes.admin_panel'))

    try:
        order.status = new_status
        db.session.commit()
        flash('Статус заказа успешно обновлен!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении статуса: {str(e)}', 'danger')

    return redirect(url_for('app_routes.admin_panel'))


# =======================
# 📌 Удаление заказа
# =======================
@app_routes.route('/admin/delete_order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('app_routes.home'))

    try:
        order = Order.query.get_or_404(order_id)  # Если заказ не найден, поднимется ошибка 404

        # Если заказ не завершён (не "completed"), возвращаем товары на склад
        if order.status != 'completed':
            for item in order.items:
                product = Product.query.get(item.product_id)
                if product:
                    product.stock += item.quantity  # Возвращаем товары на склад

        # Удаляем все связанные элементы из OrderItem
        for item in order.items:
            db.session.delete(item)

        db.session.delete(order)
        db.session.commit()
        flash('Заказ успешно удалён', 'success')  # Сообщение об успешном удалении
    except Exception as e:
        db.session.rollback()  # Откатываем транзакцию в случае ошибки
        flash(f'Произошла ошибка при удалении заказа: {str(e)}', 'danger')  # Сообщение об ошибке

    return redirect(url_for('app_routes.admin_panel'))
