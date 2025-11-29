from datetime import datetime, timedelta
from flask import redirect, url_for, request, flash
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func
from models import db, User, Role, Product, Order, OrderItem, Category, Supplier

def _is_admin():
    if not current_user.is_authenticated:
        return False
    r = current_user.role
    if not r or not r.name:
        return False
    return r.name.lower() == 'admin'

class SecureModelView(ModelView):
    def is_accessible(self):
        return _is_admin()
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))

class UsersModelView(SecureModelView):
    column_searchable_list = ['username', 'email', 'first_name', 'last_name']
    column_filters = ['role_id', 'is_active']
    column_editable_list = ['is_active', 'role_id']
    form_columns = ['username', 'email', 'first_name', 'middle_name', 'last_name', 'role_id', 'is_active']

class ProductsModelView(SecureModelView):
    column_searchable_list = ['productname']
    column_filters = ['category_id', 'is_published', 'created_by']
    column_editable_list = ['is_published', 'price', 'category_id']

class OrdersModelView(SecureModelView):
    column_filters = ['status', 'user_id', 'seller_id']
    column_editable_list = ['status']

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('auth.login') + '?next=' + url_for('admin.index'))

        now = datetime.utcnow()
        since = now - timedelta(days=30)
        users_count = User.query.count()
        products_count = Product.query.count()
        orders_count = Order.query.count()
        new_orders = Order.query.filter(Order.created_at >= since).count()
        new_products = Product.query.filter(Product.created_at >= since).count()

        new_clients = User.query.join(Role).filter(
            func.lower(func.trim(Role.name)) == 'user',
            User.created_at >= since
        ).count()

        new_sellers = User.query.join(Role).filter(
            func.lower(func.trim(Role.name)) == 'seller',
            User.created_at >= since
        ).count()

        users = User.query.order_by(User.created_at.desc()).limit(10).all()
        products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

        return self.render('admin/dashboard.html',
                           users_count=users_count,
                           products_count=products_count,
                           orders_count=orders_count,
                           new_orders=new_orders,
                           new_products=new_products,
                           new_clients=new_clients,
                           new_sellers=new_sellers,
                           users=users,
                           products=products,
                           recent_orders=recent_orders)


class AdminProfileView(BaseView):
    def is_accessible(self):
        return _is_admin()
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))
    @expose('/')
    def index(self):
        return self.render('admin/admin_profile.html')

class AdminManagementView(BaseView):
    def is_accessible(self):
        return _is_admin()
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))
    @expose('/')
    def index(self):
        clients = db.session.query(User).join(Role, User.role_id == Role.id).\
            filter(db.func.lower(db.func.trim(Role.name)) == 'user').order_by(User.created_at.desc()).all()
        sellers = db.session.query(User).join(Role, User.role_id == Role.id).\
            filter(db.func.lower(db.func.trim(Role.name)) == 'seller').order_by(User.created_at.desc()).all()
        orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
        products = Product.query.order_by(Product.created_at.desc()).limit(50).all()
        return self.render('admin/management.html', clients=clients, sellers=sellers, orders=orders, products=products)
    @expose('/change_user_role', methods=['POST'])
    def change_user_role(self):
        user_id = int(request.form.get('user_id'))
        role_name = request.form.get('role_name')
        user = User.query.get_or_404(user_id)
        role = Role.query.filter_by(name=role_name).first()
        if role:
            user.role_id = role.id
            db.session.commit()
        return redirect(url_for('adminmanagementview.index'))
    @expose('/toggle_user_active', methods=['POST'])
    def toggle_user_active(self):
        user_id = int(request.form.get('user_id'))
        user = User.query.get_or_404(user_id)
        user.is_active = not bool(user.is_active)
        db.session.commit()
        return redirect(url_for('adminmanagementview.index'))
    @expose('/update_order_status', methods=['POST'])
    def update_order_status(self):
        order_id = int(request.form.get('order_id'))
        status = request.form.get('status')
        order = Order.query.get_or_404(order_id)
        order.status = status
        db.session.commit()
        return redirect(url_for('adminmanagementview.index'))
    @expose('/toggle_product_publish', methods=['POST'])
    def toggle_product_publish(self):
        product_id = int(request.form.get('product_id'))
        product = Product.query.get_or_404(product_id)
        product.is_published = not bool(product.is_published)
        db.session.commit()
        return redirect(url_for('adminmanagementview.index'))

def init_admin(app):
    admin = Admin(app, name='Админка', index_view=MyAdminIndexView(name='Главная'))
    admin.add_view(UsersModelView(User, db.session, category='Управление'))
    admin.add_view(SecureModelView(Role, db.session, category='Управление'))
    admin.add_view(ProductsModelView(Product, db.session, category='Управление'))
    admin.add_view(SecureModelView(Category, db.session, category='Управление'))
    admin.add_view(SecureModelView(Supplier, db.session, category='Управление'))
    admin.add_view(OrdersModelView(Order, db.session, category='Управление'))
    admin.add_view(SecureModelView(OrderItem, db.session, category='Управление'))
    admin.add_view(AdminProfileView(name='Профиль', category='Администрирование'))
    admin.add_view(AdminManagementView(name='Управление', category='Администрирование'))