from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from flask_marshmallow import Marshmallow
from datetime import date, timedelta, datetime, timezone
from typing import List
from marshmallow import ValidationError, fields
from sqlalchemy import select, delete, text
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from dotenv import load_dotenv
import os

app = Flask(__name__)

CORS(app)

load_dotenv()

user = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')


app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{user}:{password}@localhost/{db_name}'


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(db.String(75), nullable=False)
    email: Mapped[str] = mapped_column(db.String(150))
    phone: Mapped[str] = mapped_column(db.String(16))
    orders: Mapped[List["Orders"]] = db.relationship(back_populates='customer')
    account: Mapped['CustomerAccount'] = db.relationship('CustomerAccount', back_populates='customer', uselist=False)



class CustomerAccount(Base):
    __tablename__ = 'customer_account'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(50), unique=True, nullable=False)
    password_hash: Mapped[str]=mapped_column(db.String(255), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customer.id'), unique=True)
    customer: Mapped['Customer'] = db.relationship('Customer', back_populates = 'account')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Orders(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.Date, nullable=False, default=date.today)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    shipment_details = db.Column(db.String(255), default='None') 
    expected_delivery_date = db.Column(db.Date)
    total_price = db.Column(db.Float, nullable=False, default=0.0)

    customer = relationship("Customer", back_populates="orders")
    products = relationship("OrderProduct", back_populates="order", cascade="all, delete-orphan")

    def __init__(self, customer_id, products, order_date, shipment_details, status, total_price):
        self.customer_id = customer_id
        self.order_date = order_date
        self.expected_delivery_date = order_date + timedelta(days=7)
        self.shipment_details = shipment_details
        self.status = status
        self.total_price = total_price

        # Create OrderProduct instances from the product dictionaries
        for product_data in products:
            order_product = OrderProduct(product_id=product_data['product_id'], quantity=product_data['quantity'])
            self.products.append(order_product)


class OrderProduct(Base):
    __tablename__ = 'order_products'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Orders", back_populates="products")
    product = relationship("Products")



class Products(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock_level = db.Column(db.Integer, default=0, nullable=False)

    orders = db.relationship("OrderProduct", back_populates="product")

with app.app_context():
    db.create_all()  

class OrderProductSchema(ma.Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True)


class OrderSchema(ma.Schema):
    id = fields.Integer(required=False)
    customer_id = fields.Integer(required=True)
    products = fields.List(fields.Nested(OrderProductSchema), required=True)
    order_date = fields.Date(required=False)
    expected_delivery_date = fields.Date()
    shipment_details = fields.String()
    status = fields.String()
    total_price = fields.Float()

    class Meta:
        fields = ('id', 'customer_id', 'items', 'order_date', 'expected_delivery_date','shipment_details', 'status', 'total_price')
        ordered = True


class CustomerSchema(ma.Schema):
    id = fields.Integer(required = False)
    customer_name = fields.String(required=True)
    email = fields.String()
    phone = fields.String()
    orders = fields.List(fields.Nested(OrderSchema), dump_only=True)

    class Meta:
        fields = ('id', 'customer_name', 'email', 'phone', 'orders')


class CustomerAccountSchema(ma.Schema):
    id = fields.Integer(required=False)
    username = fields.String (required=True)
    password = fields.String(required=True)
    customer_id = fields.Integer(required = True)

    class Meta:
        fields = ('id', 'username', 'password', 'customer_id')


class ProductSchema(ma.Schema):
    id = fields.Integer(required=False)
    product_name = fields.String(required=True)
    price = fields.Float(required=True)

    class Meta:
        fields = ('id', 'product_name', 'price')

class ProductStockSchema(ma.Schema):
    id = fields.Integer(required=False)
    product_name = fields.String(required=True)
    price = fields.Float(required=True)
    stock_level = fields.Integer(required=True)

    class Meta:
        fields = ('id', 'product_name', 'price', 'stock_level')

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

customer_account_schema = CustomerAccountSchema()
customers_account_schema = CustomerAccountSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many= True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

product_stock_schema = ProductStockSchema()
products_stock_schema = ProductStockSchema(many=True)

# Home
@app.route('/')
def home():
    return "Welcome to the ecommerce app!"

# Create Customer
@app.route('/customers', methods = ['POST'])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify({e.messages}), 400
    
    new_customer = Customer(customer_name= customer_data['customer_name'], email = customer_data['email'], phone = customer_data['phone'])
    db.session.add(new_customer)
    db.session.commit()

    return jsonify({"Message": "New customer added successfully!"}), 201

# Get Customers
@app.route('/customers', methods = ['GET'])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars()
    customers = result.all()
    
    return customers_schema.jsonify(customers)

# Get Customer
@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    customer = db.session.get(Customer, id)

    if customer is None:
        return jsonify({"message": "Customer not found"}), 404


    return customer_schema.jsonify(customer), 200

# Update Customer
@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"Error": "Customer not found."}), 404
    
    customer = result
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in customer_data.items():
        setattr(customer, field, value)
    
    db.session.commit()
    return jsonify({"Message": "Customer details have been updated!"})

# Delete Customer
@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    try:
        db.session.execute(text("DELETE FROM customer_account WHERE customer_id = :id"), {'id': id})
        db.session.execute(text("DELETE FROM customer WHERE id = :id"), {'id': id})
        db.session.commit()

        return jsonify({"message": "Customer deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error during deletion: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Create Customer Account
@app.route('/customer_accounts', methods=['POST'])
def create_customer_account():
    try:
        account_data = customer_account_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    username = account_data['username']
    existing_account = db.session.execute(select(CustomerAccount).where(CustomerAccount.username == username)).scalar()
    if existing_account:
        return jsonify({"Error": "Username already exists"}), 400
    
    new_account = CustomerAccount(    
        username = account_data['username'],
        customer_id = account_data['customer_id']
        )
    new_account.set_password(account_data['password'])

    db.session.add(new_account)
    db.session.commit()

    return jsonify({"Message": "Customer account created successfully!"}), 201

# Customer Sign Up
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        customer_data = {
            "customer_name": data.get("customer_name"),
            "email": data.get("email"),
            "phone": data.get("phone")
        }

        try:
            validated_customer = customer_schema.load(customer_data)
        except ValidationError as ve:
            return jsonify({"customer_errors": ve.messages}), 400

        account_data = {
            "username": data.get("username"),
            "password": data.get("password")
        }

        account_errors = {}
        if not account_data["username"]:
            account_errors["username"] = ["Username is required."]
        if not account_data["password"]:
            account_errors["password"] = ["Password is required."]
        
        if account_errors:
            return jsonify({"account_errors": account_errors}), 400

        new_customer = Customer(
            customer_name=validated_customer['customer_name'],
            email=validated_customer.get('email'),
            phone=validated_customer.get('phone')
        )
        db.session.add(new_customer)
        db.session.flush()

        existing_account = db.session.execute(
            select(CustomerAccount).where(CustomerAccount.username == account_data['username'])
        ).scalar()
        if existing_account:
            db.session.rollback()
            return jsonify({"account_errors": {"username": ["Username already exists."]}}), 400

        new_account = CustomerAccount(
            username=account_data['username'],
            customer_id=new_customer.id
        )
        new_account.set_password(account_data['password'])
        db.session.add(new_account)

        db.session.commit()

        return jsonify({
            "message": "User signed up successfully!",
            "customer_id": new_customer.id,
            "username": new_account.username
        }), 201

    except IntegrityError as ie:
        db.session.rollback()
        return jsonify({"error": "Database integrity error.", "details": str(ie)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

# Customer Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json

    login_input = data.get('username_or_email')
    password = data.get('password')

    if not login_input or not password:
        return jsonify({"error": "Username/Email and password are required"}), 400

    if '@' in login_input:
        account = db.session.execute(
            select(CustomerAccount).join(Customer).where(Customer.email == login_input)
        ).scalar()
    else:
        account = db.session.execute(
            select(CustomerAccount).where(CustomerAccount.username == login_input)
        ).scalar()

    if not account:
        return jsonify({"error": "Invalid username/email or password"}), 400

    if not account.check_password(password):
        return jsonify({"error": "Invalid username/email or password"}), 400

    return jsonify({"message": "Login successful", "username": account.username}), 200

# Get Customer Accounts
@app.route('/customer_accounts', methods = ['GET'])
def get_customer_accounts():
    query = select(CustomerAccount)
    result = db.session.execute(query).scalars()
    customer_accounts = result.all()
    
    return customers_account_schema.jsonify(customer_accounts)

# Get Customer Account
@app.route('/customer_accounts/<int:id>', methods=['GET'])
def get_customer_account(id):
    account = db.session.execute(select(CustomerAccount).where(CustomerAccount.id == id)).scalar()
    
    if not account:
        return jsonify({'Error': "Customer account not found!"}), 404
    
    return customer_account_schema.jsonify(account)

# Update Customer Account
@app.route('/customer_accounts/<int:id>', methods=['PUT'])
def update_customer_account(id):
    account = db.session.execute(select(CustomerAccount).where(CustomerAccount.id == id)).scalar()
    
    if not account:
        return jsonify({"Error": "Customer account not found."}), 404
    
    try:
        account_data = customer_account_schema.load(request.json, partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    if 'username' in account_data:
        account.username = account_data['username']
    
    if 'password' in account_data:
        account.set_password(account_data['password'])
    
    db.session.commit()
    return jsonify({"Message": "Customer account details have been updated!"})

# Delete Customer Account
@app.route('/customer_accounts/<int:id>', methods=['DELETE'])
def delete_customer_account(id):
    account = db.session.execute(select(CustomerAccount).where(CustomerAccount.id == id)).scalar()
    
    if not account:
        return jsonify({"Error": "Customer account not found."}), 404
    
    db.session.delete(account)
    db.session.commit()
    return jsonify({"Message": "Customer account successfully deleted!"}), 200

# Get Products
@app.route('/products', methods = ['GET'])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars()
    products = result.all()
    
    return products_schema.jsonify(products)

# Get Product
@app.route('/products/<int:id>', methods = ['GET'])
def get_product(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({'Error': "Product not found!"}), 404
    
    return product_schema.jsonify(result)

# Create Product
@app.route('/products', methods = ['POST'])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify (e.messages), 400
    
    new_product = Products(product_name= product_data['product_name'], price = product_data['price'])
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"Message": "New product successfully added!"}), 201

# Update Product
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"Error": "Product not found."}), 404
    
    product = result
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in product_data.items():
        setattr(product, field, value)
    
    db.session.commit()
    return jsonify({"Message": "Product details have been updated!"})

# Delete Product
@app.route('/products/<int:id>', methods = ['DELETE'])
def delete_product(id):
    query = delete(Products).where(Products.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error": "Product not found."})
    
    db.session.commit()
    return jsonify({"Message": "Product successfully deleted!"}), 200


# Get Orders
@app.route('/orders', methods = ['GET'])
def get_orders():
    query = select(Orders)
    result = db.session.execute(query).scalars()
    orders = result.all()
    
    return orders_schema.jsonify(orders)

# Get Order
@app.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    try:
        order = Orders.query.get(id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        products_data = [
            {
                "product_id": op.product_id,
                "product_name": op.product.product_name if op.product else None,
                "quantity": op.quantity
            }
            for op in order.products
        ]

        order_data = {
            "id": order.id,
            "customer_id": order.customer_id,
            "order_date": order.order_date.strftime("%a, %d %b %Y"),
            "expected_delivery_date": order.expected_delivery_date.strftime("%a, %d %b %Y"),
            "products": products_data,
            "shipment_details": order.shipment_details,
            "status": order.status,
            "total_price": order.total_price,
        }

        return jsonify(order_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # Create Order
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()

    total_price = 0
    products_list = []

    for product_data in data['products']:
        product = db.session.get(Products, product_data['product_id'])
        if product:
            total_price += product.price * product_data['quantity']
            products_list.append({
                'product_id': product.id,
                'quantity': product_data['quantity']
            })
    order_date = datetime.now(timezone.utc).date()

    order = Orders(
        customer_id=data['customer_id'],
        shipment_details=data['shipment_details'],
        status=data['status'],
        order_date= order_date,
        total_price=total_price,
        products=products_list
    )

    db.session.add(order)
    db.session.commit()

    return jsonify({'message': 'Order created successfully'}), 201


# Update Order
@app.route('/orders/<int:id>', methods=['PUT'])
def update_order(id):
    query = select(Orders).where(Orders.id == id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"Error": "Order not found."}), 404
    
    order = result
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in order_data.items():
        setattr(order, field, value)
    
    db.session.commit()
    return jsonify({"Message": "Order details have been updated!"})

# Delete Order
@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        db.session.execute(text("DELETE FROM order_product WHERE order_id = :order_id"), {'order_id': order_id})
        db.session.execute(text("DELETE FROM orders WHERE id = :order_id"), {'order_id': order_id})

        db.session.commit()

        return jsonify({"message": "Order deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error during deletion: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Cancel Order
@app.route('/orders/cancel/<int:id>', methods=['PUT'])
def cancel_order(id):
    order = db.session.execute(select(Orders).where(Orders.id == id)).scalar()

    if not order:
        return jsonify({"Error": "Order not found."}), 404

    if order.status in ["Shipped", "Completed"]:
        return jsonify({"Error": "Cannot cancel order. It has already been shipped or completed."}), 400

    order.status = "Canceled"

    try:
        db.session.commit()
        return jsonify({"Message": "Order canceled successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"Error": str(e)}), 500

# Get Order Items
@app.route("/order_items/<int:id>", methods=['GET'])
def order_items(id):
    query = select(Orders).where(Orders.id == id)
    order = db.session.execute(query).scalar()

    if order is None:
        return jsonify({"Error": "Order not found!"}), 404
    
    order_dict = order_schema.dump(order)
    order_dict['items'] = [{'id': product.id, 'product_name': product.product_name} for product in order.products]

    return jsonify(order_dict)

# Get Products Stock
@app.route('/products/stock', methods = ['GET'])
def get_products_stock():
    query = select(Products)
    result = db.session.execute(query).scalars()
    products = result.all()
    
    return products_stock_schema.jsonify(products)

#Get Product Stock
@app.route('/products/stock/<int:id>', methods=['GET'])
def get_product_stock(id):
    product = db.session.execute(select(Products).where(Products.id == id)).scalar()

    if not product:
        return jsonify({'Error': "Product not found!"}), 404
    
    return jsonify({"product_name": product.product_name, "stock_level": product.stock_level})

# Update Product Stock
@app.route('/products/stock/<int:id>', methods=['PUT'])
def update_product_stock(id):
    product = db.session.execute(select(Products).where(Products.id == id)).scalar()

    if not product:
        return jsonify({"Error": "Product not found."}), 404

    try:
        new_stock_level = request.json['stock_level']
        product.stock_level = new_stock_level
        db.session.commit()
        return jsonify({"Message": "Product stock level updated successfully!"})
    except KeyError:
        return jsonify({"Error": "Stock level field is required in the request."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"Error": str(e)}), 500

#Restock Products
@app.route('/restock_products', methods=['GET'])
def restock_products():
    threshold = 10
    low_stock_products = db.session.query(Products).filter(Products.stock_level < threshold).all()

    if not low_stock_products:
        return jsonify({"Message": "No products below restock threshold."}), 200

    try:
        for product in low_stock_products:
            new_stock_level = 50
            product.stock_level = new_stock_level

            db.session.commit()

        return jsonify({"Message": "Products restocked successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"Error": f"Failed to restock products. Error: {str(e)}"}), 500

# Get Order History
@app.route('/customers/order_history/<int:customer_id>', methods=['GET'])
def get_order_history(customer_id):
    query = select(Orders).where(Orders.customer_id == customer_id)
    result = db.session.execute(query).scalars()
    orders = result.all()

    serialized_orders = orders_schema.dump(orders)

    return jsonify(serialized_orders)



if __name__ == "__main__":
    app.run(debug=True)