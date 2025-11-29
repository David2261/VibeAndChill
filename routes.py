# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Role, UserRole, Product, Category, Order, OrderItem, Cart
from sqlalchemy import and_, or_, text
from werkzeug.utils import secure_filename
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Создаем папку для изображений, если она не существует
UPLOAD_FOLDER = os.path.join('static', 'images')
if not os.path.exists(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)

def get_product_image_path(product):
	"""Возвращает путь к изображению товара или путь к заглушке"""
	if product.product_image:
		image_path = os.path.join('static', product.product_image)
		if os.path.exists(image_path):
			return product.product_image
	return 'blank.jpg'

@auth_bp.route('/checkout')
@login_required
def checkout():
	try:
		cart_items = Cart.query.filter_by(user_id=current_user.id).all()
		total_cart_amount = sum([(item.product.price or 0) * (item.quantity or 0) for item in cart_items])
		if not cart_items:
			flash('Корзина пуста', 'error')
			return redirect(url_for('auth.products'))
		return render_template('user/checkout.html', cart_items=cart_items, total_cart_amount=total_cart_amount)
	except Exception as e:
		flash(f'Ошибка при загрузке оформления заказа: {str(e)}', 'error')
		return redirect(url_for('auth.products'))

@auth_bp.route('/process_checkout', methods=['POST'])
@login_required
def process_checkout():
	try:
		cart_items = Cart.query.filter_by(user_id=current_user.id).all()
		if not cart_items:
			flash('Корзина пуста', 'error')
			return redirect(url_for('auth.products'))

		total_amount = sum([(item.product.price or 0) * (item.quantity or 0) for item in cart_items])

		first_item = cart_items[0]
		seller_id = first_item.product.created_by

		order = Order(
			user_id=current_user.id,
			seller_id=seller_id,
			total_amount=total_amount,
			status='pending'
		)
		db.session.add(order)
		db.session.flush()

		for item in cart_items:
			order_item = OrderItem(
				order_id=order.id,
				product_id=item.product_id,
				quantity=item.quantity,
				price=item.product.price
			)
			db.session.add(order_item)

		for item in cart_items:
			db.session.delete(item)

		db.session.commit()
		flash('Заказ успешно оформлен', 'success')
		return redirect(url_for('auth.dashboard'))
	except Exception as e:
		db.session.rollback()
		flash(f'Ошибка при оформлении заказа: {str(e)}', 'error')
		return redirect(url_for('auth.checkout'))

@auth_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
	try:
		data = request.get_json(silent=True) or {}
		action = data.get('action')
		item = Cart.query.get_or_404(item_id)
		if item.user_id != current_user.id:
			return jsonify({"success": False}), 403

		if action == 'increase':
			item.quantity = (item.quantity or 0) + 1
		elif action == 'decrease':
			item.quantity = (item.quantity or 0) - 1
			if item.quantity <= 0:
				db.session.delete(item)
				db.session.commit()
				return jsonify({"success": True})
		else:
			return jsonify({"success": False}), 400

		db.session.commit()
		return jsonify({"success": True})
	except Exception as e:
		db.session.rollback()
		return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
	try:
		item = Cart.query.get_or_404(item_id)
		if item.user_id != current_user.id:
			return jsonify({"success": False}), 403
		db.session.delete(item)
		db.session.commit()
		return jsonify({"success": True})
	except Exception as e:
		db.session.rollback()
		return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
	try:
		product = Product.query.get_or_404(product_id)
		item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
		if item:
			item.quantity = (item.quantity or 0) + 1
		else:
			item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
			db.session.add(item)
		db.session.commit()
		flash('Товар добавлен в корзину', 'success')
		return redirect(request.referrer or url_for('auth.products'))
	except Exception as e:
		db.session.rollback()
		flash(f'Ошибка при добавлении в корзину: {str(e)}', 'error')
		return redirect(url_for('auth.products'))

@auth_bp.route('/')
def index():
	return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('auth.products'))

	if request.method == 'POST':
		email = request.form.get('email', '').strip()
		password = request.form.get('password', '').strip()

		user = User.query.filter_by(email=email).first()

		if user and user.check_password(password):
			login_user(user, remember=True)

			next_page = request.args.get('next')
			if next_page and next_page.startswith('/'):
				if user.is_admin() and 'admin' in next_page:
					flash('Добро пожаловать, Админ!', 'success')
					return redirect(next_page)
				return redirect(next_page)
			
			if user.is_admin():
				flash('Добро пожаловать, Админ!', 'success')
				return redirect(url_for('admin.index'))
			else:
				flash(f'Добро пожаловать, {user.first_name or user.username}!', 'success')
				return redirect(url_for('auth.products'))

		flash('Неверный email или пароль', 'error')

	return render_template('login.html')


@auth_bp.route('/about')
def about():
	return render_template('about.html')

@auth_bp.route('/contacts')
def contacts():
	return render_template('contacts.html')

@auth_bp.route('/privacy')
def privacy():
	return render_template('privacy.html')

@auth_bp.route('/agreement')
def agreement():
	return render_template('agreement.html')

@auth_bp.route('/dashboard')
@login_required
def dashboard():
	try:
		if current_user.role_id == 2:
			total_orders = Order.query.filter_by(seller_id=current_user.id).count()
			total_spent = db.session.query(db.func.sum(Order.total_amount)).filter_by(seller_id=current_user.id).scalar() or 0
			
			return render_template('dashboard.html',
								total_orders=total_orders,
								total_spent=total_spent)
		else:
			recent_orders = Order.query.filter_by(user_id=current_user.id)\
				.order_by(Order.created_at.desc())\
				.limit(5)\
				.all()
			
			return render_template('dashboard.html',
								recent_orders=recent_orders)
	except Exception as e:
		flash(f'Произошла ошибка: {str(e)}', 'error')
		return redirect(url_for('auth.products'))

@auth_bp.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		try:
			first_name = request.form['first_name']
			middle_name = request.form['middle_name']
			last_name = request.form['last_name']
			email = request.form['email']
			password = request.form['password']
			role_id = int(request.form['role'])  # Получаем выбранную роль
			
			# Проверяем, существует ли уже пользователь с таким email
			existing_user = User.query.filter_by(email=email).first()
			if existing_user:
				flash('Пользователь с таким email уже существует', 'error')
				return redirect(url_for('auth.register'))
			
			# Генерируем username на основе email
			username = email.split('@')[0]  # Берем часть email до @
			
			hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
			
			# Сбрасываем последовательность ID
			db.session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
			
			new_user = User(
				username=username,
				first_name=first_name,
				middle_name=middle_name,
				last_name=last_name,
				email=email,
				password_hash=hashed_password,
				role_id=role_id  # Используем выбранную роль
			)
			
			db.session.add(new_user)
			db.session.commit()
			
			flash('Регистрация успешна! Теперь вы можете войти.', 'success')
			return redirect(url_for('auth.login'))
			
		except Exception as e:
			db.session.rollback()
			flash(f'Произошла ошибка при регистрации: {str(e)}', 'error')
			return redirect(url_for('auth.register'))
	
	return render_template('register.html')

@auth_bp.route('/input-form', methods=['GET', 'POST'])
def input_form():
	if request.method == 'POST':
		try:
			# Получаем данные из формы
			name = request.form['name']
			email = request.form['email']
			phone = request.form['phone']
			message = request.form['message']
			
			# Разбиваем имя на части
			name_parts = name.split()
			first_name = name_parts[0] if len(name_parts) > 0 else ''
			middle_name = name_parts[1] if len(name_parts) > 1 else ''
			last_name = name_parts[2] if len(name_parts) > 2 else ''
			
			# Создаем нового пользователя
			new_user = User(
				first_name=first_name,
				middle_name=middle_name,
				last_name=last_name,
				email=email,
				phone=int(phone),
				user_password=generate_password_hash('default_password', method='pbkdf2:sha256')  # Генерируем временный пароль
			)
			
			# Добавляем пользователя в базу данных
			db.session.add(new_user)
			db.session.commit()
			
			# Находим роль "User"
			user_role = Role.query.filter_by(name='User').first()
			if user_role:
				# Создаем связь пользователя с ролью
				user_role_link = UserRole(user_id=new_user.id, role_id=user_role.id)
				db.session.add(user_role_link)
				db.session.commit()
			
			flash('Информация успешно сохранена!', 'success')
			return redirect(url_for('auth.input_form'))
			
		except Exception as e:
			db.session.rollback()
			flash(f'Произошла ошибка: {str(e)}', 'error')
			return redirect(url_for('auth.input_form'))
	
	return render_template('input_form.html')

@auth_bp.route('/products')
def products():
	try:
		# Получаем параметры фильтрации
		category_id = request.args.get('category', type=int)
		min_price = request.args.get('min_price', type=float)
		max_price = request.args.get('max_price', type=float)
		page = request.args.get('page', 1, type=int)
		per_page = 12  # Количество товаров на странице

		# Создаем базовый запрос
		query = Product.query.filter_by(is_published=True)

		# Применяем фильтры
		if category_id:
			query = query.filter_by(category_id=category_id)
		if min_price is not None:
			query = query.filter(Product.price >= min_price)
		if max_price is not None:
			query = query.filter(Product.price <= max_price)

		# Получаем все категории для фильтра
		categories = Category.query.all()

		# Применяем пагинацию
		pagination = query.paginate(page=page, per_page=per_page, error_out=False)
		products = pagination.items

		return render_template('products.html',
							products=products,
							categories=categories,
							selected_category=category_id,
							min_price=min_price,
							max_price=max_price,
							pagination=pagination,
							get_product_image_path=get_product_image_path)
	except Exception as e:
		flash(f'Произошла ошибка: {str(e)}', 'error')
		return redirect(url_for('auth.index'))

@auth_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	if request.method == 'POST':
		try:
			current_user.first_name = request.form['first_name']
			current_user.middle_name = request.form['middle_name']
			current_user.last_name = request.form['last_name']
			current_user.email = request.form['email']
			
			# Обновляем роль пользователя
			new_role_id = int(request.form['role_id'])
			if new_role_id != current_user.role_id:
				current_user.role_id = new_role_id
				flash('Роль успешно изменена', 'success')
			
			# Если пользователь ввел новый пароль
			if request.form['password']:
				current_user.password_hash = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
				flash('Пароль успешно изменен', 'success')
			
			db.session.commit()
			flash('Профиль успешно обновлен', 'success')
			return redirect(url_for('auth.dashboard'))
			
		except Exception as e:
			db.session.rollback()
			flash(f'Произошла ошибка при обновлении профиля: {str(e)}', 'error')
			return redirect(url_for('auth.edit_profile'))
	
	return render_template('edit_profile.html')

@auth_bp.route('/my_products')
@login_required
def my_products():
	try:
		# Проверяем, является ли пользователь продавцом
		if current_user.role_id != 2:  # 2 - это ID роли продавца
			flash('У вас нет прав для просмотра списка товаров', 'error')
			return redirect(url_for('auth.products'))
		
		# Получаем товары текущего пользователя
		products = Product.query.filter_by(created_by=current_user.id).all()
		
		# Получаем все категории для отображения
		categories = Category.query.all()
		
		return render_template('my_products.html',
							products=products,
							categories=categories,
							get_product_image_path=get_product_image_path)
	except Exception as e:
		flash(f'Ошибка при загрузке товаров: {str(e)}', 'error')
		return redirect(url_for('auth.dashboard'))

@auth_bp.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
	# Проверяем, является ли пользователь продавцом
	if current_user.role_id != 2:  # 2 - это ID роли продавца
		flash('У вас нет прав для добавления товаров', 'error')
		return redirect(url_for('auth.products'))
	
	if request.method == 'POST':
		try:
			# Сбрасываем последовательность ID
			db.session.execute(text("SELECT setval('products_id_seq', (SELECT MAX(id) FROM products))"))
			
			# Получаем данные из формы
			productname = request.form['productname']
			price = float(request.form['price'])
			category_id = int(request.form['category_id'])
			is_published = bool(request.form.get('is_published', False))
			
			# Обработка загрузки изображения
			product_image = None
			if 'product_image' in request.files:
				file = request.files['product_image']
				if file and file.filename:
					# Генерируем уникальное имя файла
					filename = secure_filename(file.filename)
					unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
					# Сохраняем файл
					file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
					product_image = os.path.join('images', unique_filename)
			
			# Создаем новый товар
			product = Product(
				productname=productname,
				price=price,
				category_id=category_id,
				created_by=current_user.id,
				is_published=is_published,
				product_image=product_image
			)
			
			db.session.add(product)
			db.session.commit()
			
			flash('Товар успешно добавлен', 'success')
			return redirect(url_for('auth.my_products'))
			
		except Exception as e:
			db.session.rollback()
			flash(f'Ошибка при добавлении товара: {str(e)}', 'error')
			return redirect(url_for('auth.add_product'))
	
	# Для GET запроса получаем список категорий
	categories = Category.query.all()
	return render_template('add_product.html', categories=categories)

@auth_bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
	# Проверяем, является ли пользователь продавцом
	if current_user.role_id != 2:  # 2 - это ID роли продавца
		flash('У вас нет прав для редактирования товаров', 'error')
		return redirect(url_for('auth.products'))
	
	# Получаем товар или возвращаем 404
	product = Product.query.get_or_404(product_id)
	
	# Проверяем, принадлежит ли товар текущему пользователю
	if product.created_by != current_user.id:
		flash('У вас нет прав для редактирования этого товара', 'error')
		return redirect(url_for('auth.my_products'))
	
	if request.method == 'POST':
		try:
			# Обновляем данные товара
			product.productname = request.form['productname']
			product.price = float(request.form['price'])
			product.category_id = int(request.form['category_id'])
			product.is_published = bool(request.form.get('is_published', False))
			
			# Обработка загрузки изображения
			if 'product_image' in request.files:
				file = request.files['product_image']
				if file and file.filename:
					# Удаляем старое изображение, если оно существует
					if product.product_image:
						old_image_path = os.path.join('static', product.product_image)
						if os.path.exists(old_image_path):
							os.remove(old_image_path)
					
					# Генерируем уникальное имя файла
					filename = secure_filename(file.filename)
					unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
					# Сохраняем файл
					file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
					product.product_image = os.path.join('images', unique_filename)
			
			db.session.commit()
			flash('Товар успешно обновлен', 'success')
			return redirect(url_for('auth.my_products'))
			
		except Exception as e:
			db.session.rollback()
			flash(f'Ошибка при обновлении товара: {str(e)}', 'error')
	
	# Для GET запроса получаем список категорий
	categories = Category.query.all()
	return render_template('edit_product.html', 
						 product=product, 
						 categories=categories,
						 get_product_image_path=get_product_image_path)

@auth_bp.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
	# Проверяем, является ли пользователь продавцом
	if current_user.role_id != 2:  # 2 - это ID роли продавца
		flash('У вас нет прав для удаления товаров', 'error')
		return redirect(url_for('auth.products'))
	
	# Получаем товар или возвращаем 404
	product = Product.query.get_or_404(product_id)
	
	# Проверяем, принадлежит ли товар текущему пользователю
	if product.created_by != current_user.id:
		flash('У вас нет прав для удаления этого товара', 'error')
		return redirect(url_for('auth.my_products'))
	
	try:
		# Удаляем изображение товара, если оно существует
		if product.product_image:
			image_path = os.path.join('static', product.product_image)
			if os.path.exists(image_path):
				os.remove(image_path)
		
		# Удаляем товар из базы данных
		db.session.delete(product)
		db.session.commit()
		
		flash('Товар успешно удален', 'success')
	except Exception as e:
		db.session.rollback()
		flash(f'Ошибка при удалении товара: {str(e)}', 'error')
	
	return redirect(url_for('auth.my_products'))

@auth_bp.route('/product_stats')
@login_required
def product_stats():
	"""Страница с многотабличным запросом - статистика товаров"""
	try:
		# Получаем статистику товаров с информацией о категориях и продавцах
		stats = db.session.query(
			Product,
			Category.category_name,
			User.username,
			db.func.count(OrderItem.id).label('order_count')
		).join(
			Category, Product.category_id == Category.id
		).join(
			User, Product.created_by == User.id
		).outerjoin(
			OrderItem, Product.id == OrderItem.product_id
		).group_by(
			Product.id, Category.id, User.id
		).all()
		
		return render_template('product_stats.html', 
							 stats=stats,
							 get_product_image_path=get_product_image_path)
	except Exception as e:
		flash(f'Ошибка при загрузке статистики: {str(e)}', 'error')
		return redirect(url_for('auth.products'))

@auth_bp.route('/search_products', methods=['GET', 'POST'])
@login_required
def search_products():
	"""Страница поиска товаров"""
	if request.method == 'POST':
		try:
			search_term = request.form.get('search_term', '')
			# Поиск по названию товара, категории и имени продавца
			products = db.session.query(
				Product, Category, User
			).join(
				Category, Product.category_id == Category.id
			).join(
				User, Product.created_by == User.id
			).filter(
				or_(
					Product.productname.ilike(f'%{search_term}%'),
					Category.category_name.ilike(f'%{search_term}%'),
					User.username.ilike(f'%{search_term}%')
				)
			).all()
			
			return render_template('search_products.html', 
								products=products, 
								search_term=search_term,
								get_product_image_path=get_product_image_path)
		except Exception as e:
			flash(f'Ошибка при поиске: {str(e)}', 'error')
	
	return render_template('search_products.html', get_product_image_path=get_product_image_path)

@auth_bp.route('/top_products')
@login_required
def top_products():
	try:
		# Самые дорогие товары
		most_expensive = Product.query.order_by(Product.price.desc()).limit(10).all()
		
		# Самые дешевые товары
		cheapest = Product.query.order_by(Product.price.asc()).limit(10).all()
		
		# Самые популярные товары (по количеству заказов)
		most_popular = db.session.query(
			Product,
			db.func.count(OrderItem.id).label('order_count')
		).join(
			OrderItem,
			Product.id == OrderItem.product_id
		).group_by(
			Product.id
		).order_by(
			db.desc('order_count')
		).limit(10).all()
		
		# Самые старые товары
		oldest = Product.query.order_by(Product.created_at.asc()).limit(10).all()
		
		return render_template('top_products.html',
							 most_expensive=most_expensive,
							 cheapest=cheapest,
							 most_popular=most_popular,
							 oldest=oldest,
							 get_product_image_path=get_product_image_path)
	except Exception as e:
		flash(f'Ошибка при загрузке топ-10 товаров: {str(e)}', 'error')
		return redirect(url_for('auth.index'))