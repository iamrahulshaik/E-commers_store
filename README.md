# 🛒 E-Commerce Store (Flask + MySQL)

This is a **full-featured e-commerce web application** built with **Flask**, **MySQL**, HTML, CSS, and JavaScript.  
It supports user registration, login, product browsing, shopping cart, checkout with Razorpay integration, and an **admin panel** for managing products, categories, ads, and orders.

---

## 🚀 Features

### 👤 User Features
- User registration & login  
- Browse products by category (T-Shirts, Oversize, Caps, etc.)  
- View product details with available sizes (S, M, L, XL)  
- Add to Cart (with size selection)  
- Update or remove items from cart  
- Save multiple addresses for checkout  
- Checkout with Razorpay (UPI/Cards)  
- Order confirmation with invoice download (PDF)  

### 🛠️ Admin Features
- Admin login (MySQL authentication)  
- Dashboard with registered users & orders  
- Add / Update / Remove Products  
- Manage Categories (name + image)  
- Upload / Remove Homepage Ads  
- View transactions grouped by order/payment ID  

---

## 🗂️ Folder Structure

ecommerce-store/

│── app.py # Main Flask application

│── requirements.txt # Python dependencies

│── README.md # Project documentation

│

├── static/ # Static assets

│ ├── css/

│ │ └── style.css

│ ├── js/

│ │ └── script.js

│ └── images/

│ └── placeholder.png
│
├── templates/ # HTML Templates

│ ├── index.html

│ ├── product_detail.html

│ ├── cart.html

│ ├── checkout.html

│ ├── order_success.html

│ ├── login.html

│ ├── register.html

│ ├── admin_login.html

│ ├── admin_dashboard.html

│ ├── manage_products.html

│ ├── manage_category.html

│ ├── manage_ads.html

│ └── manage_orders.html

│
└── database/

└── schema.sql # MySQL schema (users, products, orders, etc.)



