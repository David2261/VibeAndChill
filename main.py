import os
from flask import Flask
from flask_login import LoginManager
from flask import request, redirect, url_for
from dotenv import load_dotenv
from models import db, User, Role
from routes import auth_bp
from admin import init_admin


load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db.init_app(app)

login_manager = LoginManager(app)
# login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
	return db.session.get(User, int(user_id))


app.register_blueprint(auth_bp)
init_admin(app)

with app.app_context():
	# При первом старте, разблокировать
	# db.create_all()

	# desired_roles = ['Admin', 'Seller', 'User']
	# for role_name in desired_roles:
	# 	role = Role.query.filter_by(name=role_name).first()
	# 	if not role:
	# 		role = Role(name=role_name)
	# 		db.session.add(role)
	# 		print(f"Создана роль: {role_name}")
	# 	else:
	# 		print(f"Роль уже существует: {role_name} (id={role.id})")
	# db.session.commit()

	admin_role = Role.query.filter_by(name='Admin').first()
	if not admin_role:
		raise Exception("Роль Admin не найдена! Что-то пошло не так.")

	admin_username = os.getenv('ADMIN_USERNAME', 'admin').strip()
	admin_email = os.getenv('ADMIN_EMAIL', f"{admin_username}@example.com").strip()
	admin_password = os.getenv('ADMIN_PASSWORD', 'admin123').strip()

	admin_user = User.query.filter_by(email=admin_email).first()
	if admin_user:
		if admin_user.role_id != admin_role.id or admin_user.role.name != 'Admin':
			print(f"Предупреждение: Пользователь {admin_email} был не админом → исправляем роль!")
			admin_user.role_id = admin_role.id
		admin_user.username = admin_username
		admin_user.is_active = True
		admin_user.first_name = 'Админ'
		admin_user.last_name = 'Системы'
		admin_user.set_password(admin_password)
	else:
		admin_user = User(
			username=admin_username,
			email=admin_email,
			role_id=admin_role.id,
			is_active=True,
			first_name='Админ',
			last_name='Системы'
		)
		admin_user.set_password(admin_password)
		db.session.add(admin_user)
		print(f"Админ создан: {admin_email} / {admin_password}")

	db.session.commit()

if __name__ == '__main__':
	app.run(debug=True)