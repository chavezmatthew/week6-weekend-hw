CREATE DATABASE ecom;

USE ecom; -

CREATE TABLE customer (
id INT AUTO_INCREMENT PRIMARY KEY,
customer_name VARCHAR(75) NOT NULL,
email VARCHAR(150) NULL
);

CREATE TABLE orders (id INT AUTO_INCREMENT PRIMARY KEY,
order_date DATE NOT NULL,
customer_id INT,
FOREIGN KEY (customer_id) REFERENCES customer(id)
);


ALTER TABLE customer ADD (phone VARCHAR(16), address VARCHAR(150));

ALTER TABLE customer ADD phone VARCHAR(16);

ALTER TABLE customer 
ADD address VARCHAR(150);


ALTER TABLE customer 
DROP COLUMN address;

SELECT * FROM orders;

ALTER TABLE customer_account MODIFY password_hash VARCHAR(255);

ALTER TABLE products
ADD COLUMN stock_level INT NOT NULL DEFAULT 0;

ALTER TABLE orders
ADD COLUMN status VARCHAR(50) DEFAULT 'Pending',
ADD COLUMN shipment_details VARCHAR(255),
ADD COLUMN expected_delivery_date DATE;

ALTER TABLE orders
ADD total_price FLOAT DEFAULT 0.0 NOT NULL;