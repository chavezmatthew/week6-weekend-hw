from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship
from sqlalchemy import Column, Integer, String, Float
from flask_marshmallow import Marshmallow
from datetime import date, timedelta
from typing import List
from marshmallow import ValidationError, fields
from sqlalchemy import select, delete
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Blackberry1!@localhost/ecom'

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


order_products = db.Table(
    "order_products",
    Base.metadata,
    db.Column('order_id', db.ForeignKey('orders.id'), primary_key=True),
    db.Column('product_id', db.ForeignKey('products.id'), primary_key=True)
)

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
    products = relationship("Products", secondary='order_products', back_populates="orders")

    def __init__(self, order_date, customer_id):
        self.order_date = order_date
        self.customer_id = customer_id
        self.expected_delivery_date = order_date + timedelta(days=7)

    def calculate_total_price(self):
        self.total_price = sum(product.price for product in self.products)

class Products(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    product_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock_level = Column(Integer, default=0, nullable=False)

    orders = relationship("Orders", secondary=order_products, back_populates="products")

with app.app_context():
    db.create_all()


class CustomerSchema(ma.Schema):
    id = fields.Integer(required = False)
    customer_name = fields.String(required=True)
    email = fields.String()
    phone = fields.String()

    class Meta:
        fields = ('id', 'customer_name', 'email', 'phone')


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

class OrderSchema(ma.Schema):
    id = fields.Integer(required=False)
    customer_id = fields.Integer(required=True)
    items = fields.List(fields.Nested(ProductSchema), required=True)
    order_date = fields.Date(required=False)
    expected_delivery_date = fields.Date()
    shipment_details = fields.String()
    status = fields.String()
    total_price = fields.Float()

    class Meta:
        ordered = True
        fields = ('id', 'customer_id', 'items', 'order_date', 'expected_delivery_date','shipment_details', 'status', 'total_price')
        

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
@app.route('/customers/<int:id>', methods = ['GET'])
def get_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({'Error': "Customer not found!"}), 404
    
    return customer_schema.jsonify(result)

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
@app.route('/customers/<int:id>', methods = ['DELETE'])
def delete_customer(id):
    query = delete(Customer).where(Customer.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error": "Customer not found."})
    
    db.session.commit()
    return jsonify({"Message": "Customer successfully deleted!"}), 200

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
@app.route('/orders/<int:id>', methods = ['GET'])
def get_order(id):
    query = select(Orders).where(Orders.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({'Error': "Order not found!"}), 404
    
    return order_schema.jsonify(result)

# Create Order
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_order = Orders(order_date=date.today(), customer_id=order_data['customer_id'])

    for item_id in order_data['items']:
        query = select(Products).where(Products.id == item_id)
        item = db.session.execute(query).scalar()

        if not item:
            return jsonify({"Error": f"Product with ID {item_id} not found."}), 404
        
        if item.stock_level <= 0:
            return jsonify({"Error": f"Product {item.product_name} is out of stock."}), 400
        
        new_order.products.append(item)
        item.stock_level -= 1

    new_order.calculate_total_price()

    try:
        db.session.add(new_order)
        db.session.commit()
        return jsonify({"Message": "New order placed!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"Error": str(e)}), 500


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
@app.route('/orders/<int:id>', methods = ['DELETE'])
def delete_order(id):
    query = delete(Orders).where(Orders.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error": "Order not found."})
    
    db.session.commit()
    return jsonify({"Message": "Order successfully deleted!"}), 200

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