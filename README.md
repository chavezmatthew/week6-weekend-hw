# Ecommerce Application Overview

## About

This is an ecommerce application where users can perform various actions such as adding, viewing, editing, and deleting customers, products, orders, and customer accounts. Customers have functionalities like making orders, tracking orders, canceling orders, and viewing order history. Administrators have additional privileges such as viewing stock levels, updating stock levels, and restocking items if stock levels fall too low.

## Setup

1. **Set up a virtual environment:**
   - Windows: `python -m venv venv`
   - Mac: `python3 -m venv venv`

2. **Activate your virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Mac: `source venv/bin/activate`

3. **Install requirements:**
   - `pip install -r requirements.txt`

## Running the Application

4. **Run app.py:**
   - If database issues occur, use the provided database queries in the `ecom.sql` file.

## Using Postman

5. **Navigate to Postman app and click import:**
   - Copy and paste text from the `postman_collection` file into the Postman app import field.

6. **Send Postman requests to test out the app:**
   - Use Postman to interact with various endpoints.

## Accessing Web Pages

7. **Access pages via web browser:**
   - [Home Page](http://127.0.0.1:5000/)
   - [Customers](http://127.0.0.1:5000/customers)
   - [Customer Accounts](http://127.0.0.1:5000/customer_accounts)
   - [Orders](http://127.0.0.1:5000/orders)
   - [Products](http://127.0.0.1:5000/products)
   - [Product Stock](http://127.0.0.1:5000/products/stock)

---

### Notes:
- Ensure the virtual environment is activated before running the application or using Postman.
- Adjust URLs (e.g., `127.0.0.1:5000`) as per your setup or deployment environment.
- For database issues, refer to `ecom.sql` for queries and setup instructions.