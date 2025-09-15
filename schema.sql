-- Create database
CREATE DATABASE IF NOT EXISTS tshirtstore
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE tshirtstore;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    mobile VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(100)
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    price DECIMAL(10,2),
    image VARCHAR(255),
    category VARCHAR(50),
    status ENUM('active', 'outofstock', 'removed') DEFAULT 'active',
    sizes TEXT DEFAULT 'S,M,L,XL',
    size_chart VARCHAR(255)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    image VARCHAR(255) NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    position INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default categories
INSERT INTO categories (name, slug, image, position)
VALUES
('Oversize', 'oversize', 'black_oversize.jpg', 1),
('T-Shirts', 'tshirts', 'white_tshirt.jpg', 2),
('Caps', 'caps', 'cap1.jpg', 3)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Address table
CREATE TABLE IF NOT EXISTS address (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    state VARCHAR(100),
    district VARCHAR(100),
    address TEXT,
    landmark VARCHAR(150),
    pincode VARCHAR(10),
    mobile VARCHAR(15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT NULL,
    address_id INT,
    payment_id VARCHAR(100),
    size ENUM('S', 'M', 'L', 'XL') NOT NULL DEFAULT 'M',
    order_group_id VARCHAR(50),
    order_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
    FOREIGN KEY (address_id) REFERENCES address(id)
);

-- Cart table
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    size ENUM('S', 'M', 'L', 'XL') NOT NULL DEFAULT 'M',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Insert initial products
INSERT INTO products (name, description, price, image, category, status)
VALUES
('Oversize Black Tee', 'Premium cotton black oversized T-shirt.', 499.00, 'black_oversize.jpg', 'oversize', 'active'),
('Classic White Tee', 'Regular fit white T-shirt.', 399.00, 'white_tshirt.jpg', 'tshirts', 'active'),
('Snapback Cap', 'Stylish adjustable snapback cap.', 299.00, 'cap1.jpg', 'caps', 'active')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert default product (placeholder) if missing
INSERT INTO products (name, description, price, image, category, status)
SELECT 'Default Product', 'This is a placeholder product.', 0.00, 'default.jpg', 'tshirts', 'active'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'Default Product');

-- Fix invalid product_id in orders
SET @default_product_id = (SELECT id FROM products WHERE name = 'Default Product' LIMIT 1);

UPDATE orders
SET product_id = @default_product_id
WHERE product_id NOT IN (SELECT id FROM products);

-- Cleanup invalid cart items
DELETE FROM cart WHERE product_id NOT IN (SELECT id FROM products);



