
from flask import Flask, render_template, request, redirect, url_for, session, jsonify,flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import razorpay
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'rahul123$storeKey@2025'
UPLOAD_FOLDER = 'static/images'

# MySQL Config
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysql'
app.config['MYSQL_DB'] = 'tshirtstore'

# Razorpay Config
razorpay_client = razorpay.Client(auth=("rzp_test_4ZE5JZGNwaAa82", "tdv17Ptu8v7tCC4t2Uw3CDA2"))
mysql = MySQL(app)




@app.route('/')
def home():
    ad_path = os.path.join('static', 'ads', 'homepage_ad.jpg')
    ad_exists = os.path.exists(ad_path)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY position ASC, id DESC")
    categories = cursor.fetchall()

    return render_template('home.html', ad_exists=ad_exists, categories=categories)



@app.route('/category/<cat>')
def category(cat):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
    SELECT * FROM products
    WHERE category = %s AND status != 'removed'
    ORDER BY 
        CASE 
            WHEN status = 'outofstock' THEN 0 
            ELSE 1 
        END, id DESC
""", (cat,))
    products = cursor.fetchall()
    for product in products:
        cursor.execute("SELECT image FROM product_images WHERE product_id = %s", (product['id'],))
        product['images'] = [row['image'] for row in cursor.fetchall()]
    return render_template('products.html', products=products, category=cat.title())


@app.route('/buy/<int:product_id>')
def buy_product(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch single product by ID
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        return "Product not found", 404

    # Create Razorpay order
    payment = razorpay_client.order.create({
        "amount": int(product['price'] * 100),  # price in paisa
        "currency": "INR",
        "payment_capture": "1"
    })

    return render_template('checkout.html', product=product, payment=payment)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM admin WHERE admin_id = %s AND password = %s", (admin_id, password))
        admin = cursor.fetchone()

        if admin:
            session['admin'] = admin['admin_id']
            return redirect('/admin-dashboard')
        else:
            return render_template('admin-login.html', error="Invalid Admin ID or Password")

    return render_template('admin-login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch users to show in Registered Users section
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    # Fetch active & out-of-stock products to list in the dashboard
    cursor.execute("SELECT * FROM products WHERE status != 'removed' ORDER BY category, name")
    products = cursor.fetchall()

    # ✅ Fetch categories for filtering in template
    cursor.execute("SELECT DISTINCT LOWER(category) AS category FROM products WHERE status != 'removed'")
    categories_result = cursor.fetchall()
    categories = [row['category'] for row in categories_result]

    upload_message = "✅ Ad uploaded successfully!" if request.args.get('uploaded') else None

    return render_template(
        'admin-dashboard.html',
        users=users,
        products=products,
        upload_message=upload_message,
        categories=categories   # ✅ Pass categories to template
    )


@app.route('/admin/add-product', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('desc')
        price = request.form.get('price')
        category = request.form.get('category')

        # ✅ Handle sizes
        sizes_list = request.form.getlist('sizes')  # e.g., ['S', 'M', 'L']
        sizes_str = ','.join(sizes_list) if sizes_list else 'S,M,L,XL'

        # ✅ Handle multiple uploaded product images
        images = request.files.getlist('images')
        image_names = []

        for image in images:
            if image and image.filename:
                filename = secure_filename(image.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(save_path)
                image_names.append(filename)

        # ✅ Handle optional size chart image
        size_chart_file = request.files.get('size_chart')
        size_chart_filename = None
        if size_chart_file and size_chart_file.filename:
            size_chart_filename = secure_filename(size_chart_file.filename)
            size_chart_path = os.path.join(app.config['UPLOAD_FOLDER'], size_chart_filename)
            size_chart_file.save(size_chart_path)

        # Fallback if no product image
        cover_image = image_names[0] if image_names else 'default.jpg'

        # ✅ Insert product into products table with sizes and size chart
        cursor.execute("""
            INSERT INTO products (name, description, price, image, category, status, sizes, size_chart)
            VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
        """, (name, desc, price, cover_image, category, sizes_str, size_chart_filename))
        mysql.connection.commit()

        product_id = cursor.lastrowid

        # ✅ Insert additional product images
        for img in image_names:
            cursor.execute(
                "INSERT INTO product_images (product_id, image) VALUES (%s, %s)",
                (product_id, img)
            )
        mysql.connection.commit()

        # ✅ AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})

        return redirect(url_for('add_product', success='1'))

    # GET request
    success = request.args.get('success') == '1'
    cursor.execute("SELECT slug, name FROM categories WHERE is_active = 1 ORDER BY position ASC")
    categories = cursor.fetchall()

    return render_template('add-product.html', success=success, categories=categories)





@app.route('/admin/update-price', methods=['GET'])
def update_price_page():
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE status != 'removed'")
    products = cursor.fetchall()
    return render_template('update-price.html', products=products)



@app.route('/admin/update-price/<int:product_id>', methods=['POST'])
def update_product_price(product_id):
    if 'admin' not in session:
        return redirect('/admin-login')

    new_price = request.form['new_price']
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE products SET price = %s WHERE id = %s", (new_price, product_id))
    mysql.connection.commit()
    return redirect('/admin/update-price')


from flask import render_template, redirect, request

# Remove Products Page
from collections import defaultdict

@app.route('/admin/remove-products')
def admin_remove_products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE status != 'removed'")
    products = cursor.fetchall()

    # ✅ Dynamic category grouping
    grouped = defaultdict(list)
    for product in products:
        grouped[product['category']].append(product)

    # Convert defaultdict to normal dict
    grouped = dict(grouped)

    return render_template('admin-remove-products.html', grouped=grouped)



# Out of Stock Products Page
@app.route('/admin/out-of-stock')
def out_of_stock_products():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM products WHERE status != 'removed'")
    products = cur.fetchall()
    cur.close()
    return render_template("out-of-stock.html", products=products)




# Product Removal Action


@app.route('/admin/remove-product/<int:product_id>', methods=['POST'])
def remove_product(product_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE products SET status='removed' WHERE id=%s", [product_id])
    mysql.connection.commit()

    # If AJAX, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    # Else fallback (in case accessed normally)
    return redirect(url_for('admin_remove_products'))




# Toggle Out of Stock / Activate
@app.route('/admin/update-product-status/<int:product_id>', methods=['POST'])
def update_product_status(product_id):
    new_status = request.form['status']
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE products SET status = %s WHERE id = %s", (new_status, product_id))
    mysql.connection.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "new_status": new_status})

    return redirect('/admin/out-of-stock')  # fallback




@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    if 'user_id' not in session:
        session['next_product_id'] = product_id
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    # 🔁 Create Razorpay Order
    payment = razorpay_client.order.create({
        "amount": int(product['price'] * 100),  # in paise
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template("checkout.html", product=product, payment=payment)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        password = request.form['password']
        email = request.form.get('email')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE mobile = %s", (mobile,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("❗ Mobile number already registered.")
            return render_template("register.html")

        cursor.execute("INSERT INTO users (name, mobile, email, password) VALUES (%s, %s, %s, %s)", 
                       (name, mobile, email, password))
        mysql.connection.commit()

        flash("✅ Registration successful! Please log in.")
        return redirect('/login')

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form['mobile']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE mobile = %s AND password = %s", (mobile, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user.get('email', '')
            session['user_contact'] = user.get('mobile', '')

            # ✅ Fetch address from `address` table for this user
            cursor.execute("SELECT * FROM address WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user['id'],))
            address_record = cursor.fetchone()

            if address_record:
                full_address = f"{address_record.get('address', '')}, {address_record.get('landmark', '')}, {address_record.get('district', '')}, {address_record.get('state', '')}, {address_record.get('pincode', '')}"
                session['user_address'] = full_address
            else:
                session['user_address'] = "No address found"

            flash("✅ Login successful!")
            return redirect('/')
        else:
            flash("❌ Invalid mobile or password.")

    return render_template("login.html")



@app.route('/logout')
def logout():
    session.clear()
    flash("🚪 Logged out successfully.")
    return redirect('/login')



@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            orders.id AS order_id,
            products.id AS product_id,          -- ✅ Include product ID
            products.name AS product_name,
            products.price,
            products.image AS image,
            orders.payment_id,
            orders.order_time,
            orders.size
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.user_id = %s
        ORDER BY orders.order_time DESC
    """, (user_id,))
    orders = cursor.fetchall()

    return render_template('my-orders.html', orders=orders)





from flask import Flask, render_template, request, redirect, session, url_for

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # Support both JSON and form-data
    data = request.get_json(silent=True)
    size = data['size'] if data else request.form.get('size')

    if not size:
        return {'success': False, 'message': 'Size is required'}, 400

    key = f"{product_id}_{size}"

    if key in cart:
        cart[key] += 1
    else:
        cart[key] = 1

    session['cart'] = cart
    session.modified = True

    total_count = sum(cart.values())

    return {'success': True, 'cart_count': total_count}


@app.route('/update-cart/<cart_key>/<action>', methods=['POST'])
def update_cart(cart_key, action):
    if 'cart' not in session:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400

    cart = session['cart']

    if cart_key not in cart:
        return jsonify({'success': False, 'message': 'Item not in cart'}), 400

    # Ensure value is an integer
    try:
        cart[cart_key] = int(cart[cart_key])
    except:
        cart[cart_key] = 1

    if action == 'increase':
        cart[cart_key] += 1
    elif action == 'decrease' and cart[cart_key] > 1:
        cart[cart_key] -= 1

    session['cart'] = cart

    try:
        product_id, size = cart_key.split('_', 1)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid cart key format'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT price FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    item_total = float(product['price']) * cart[cart_key]

    # ✅ Fix: Calculate grand total correctly (without duplication)
    grand_total = 0
    processed_keys = set()

    for key, qty in cart.items():
        if key in processed_keys:
            continue
        try:
            pid, _ = key.split('_', 1)
        except:
            continue
        cursor.execute("SELECT price FROM products WHERE id = %s", (pid,))
        p = cursor.fetchone()
        if p:
            grand_total += float(p['price']) * qty
        processed_keys.add(key)

    return jsonify({
        'success': True,
        'quantity': cart[cart_key],
        'item_total': round(item_total, 2),
        'grand_total': round(grand_total, 2)
    })


@app.route('/update-cart-quantity/<cart_key>/<int:quantity>', methods=['POST'])
def update_cart_quantity(cart_key, quantity):
    if 'cart' not in session:
        return jsonify({'success': False, 'message': 'Cart not found'})

    cart = session['cart']

    # Check key format: must have productId_size
    if '_' not in cart_key:
        return jsonify({'success': False, 'message': 'Invalid cart key format'})

    # If the item is not in cart, return error
    if cart_key not in cart:
        return jsonify({'success': False, 'message': 'Item not in cart'})

    # Update quantity
    cart[cart_key] = quantity
    session.modified = True

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    grand_total = 0
    item_total = 0

    for key, qty in cart.items():
        try:
            pid, sz = key.split('_')
        except:
            continue  # skip malformed keys

        cursor.execute("SELECT price FROM products WHERE id = %s", (pid,))
        prod = cursor.fetchone()

        if prod:
            total = float(prod['price']) * int(qty)
            grand_total += total
            if key == cart_key:
                item_total = total

    return jsonify({
        'success': True,
        'item_total': round(item_total, 2),
        'grand_total': round(grand_total, 2)
    })


@app.route('/update-cart-size/<cart_key>', methods=['POST'])
def update_cart_size(cart_key):
    if 'cart' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Cart not found'}), 400
        return redirect('/cart')

    cart = session['cart']
    if cart_key not in cart:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
        return redirect('/cart')

    new_size = request.form.get('new_size')
    if new_size not in ['S', 'M', 'L', 'XL']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid size'}), 400
        return redirect('/cart')

    quantity = cart[cart_key]
    product_id, _ = cart_key.split('_', 1)

    # Remove old key, add new key
    new_key = f"{product_id}_{new_size}"
    if new_key in cart:
        cart[new_key] += quantity  # merge quantities
    else:
        cart[new_key] = quantity

    del cart[cart_key]
    session['cart'] = cart
    session.modified = True  # ✅ ensures session updates

    # ✅ If AJAX request, return JSON instead of redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'new_key': new_key, 'quantity': cart[new_key]})

    return redirect('/cart')




@app.route('/remove-from-cart/<cart_key>', methods=['POST'])
def remove_from_cart(cart_key):
    cart = session.get('cart', {})
    if cart_key in cart:
        cart.pop(cart_key)
        session['cart'] = cart

    # 🧠 Recalculate grand total after removal
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    grand_total = 0
    for key, qty in cart.items():
        try:
            pid, _ = key.split('_', 1)
            cursor.execute("SELECT price FROM products WHERE id = %s", (pid,))
            p = cursor.fetchone()
            if p:
                grand_total += float(p['price']) * qty
        except:
            continue

    return jsonify({'success': True, 'grand_total': grand_total})





@app.route('/cart')
def cart():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Fetch address
    address = None
    if 'user_id' in session:
        user_id = session['user_id']
        selected_address_id = session.get('selected_address_id')

        if selected_address_id:
            cursor.execute("SELECT * FROM address WHERE id = %s AND user_id = %s", (selected_address_id, user_id))
            address = cursor.fetchone()

        if not address:
            cursor.execute("SELECT * FROM address WHERE user_id = %s ORDER BY id DESC", (user_id,))
            address = cursor.fetchone()
            if address:
                session['selected_address_id'] = address['id']

    # ✅ Cart check
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart_items=[], grand_total=0, address=address)

    cart = session['cart']
    product_ids = []

    # Collect valid product IDs
    for key in cart.keys():
        if '_' in key:
            pid, _ = key.split('_', 1)
            if pid.isdigit():
                product_ids.append(pid)

    if not product_ids:
        return render_template('cart.html', cart_items=[], grand_total=0, address=address)

    format_strings = ','.join(['%s'] * len(product_ids))
    query = f"SELECT * FROM products WHERE id IN ({format_strings}) AND status='active'"
    cursor.execute(query, product_ids)
    products = cursor.fetchall()

    cart_items = []
    grand_total = 0

    for key, quantity in cart.items():
        try:
            product_id, size = key.split('_', 1)
        except:
            continue  # skip invalid keys

        product = next((p for p in products if str(p['id']) == product_id), None)
        if product:
            quantity_int = int(quantity)
            item_total = float(product['price']) * quantity_int
            grand_total += item_total

            # ✅ Extract available sizes for this product
            sizes_str = product.get('sizes') or ''
            available_sizes = sizes_str.split(',') if sizes_str else ['S', 'M', 'L', 'XL']

            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity_int,
                'total': item_total,
                'image': product['image'],
                'size': size,
                'available_sizes': available_sizes  # ✅ Inject into cart item
            })

    return render_template(
        'cart.html',
        cart_items=cart_items,
        grand_total=round(grand_total, 2),
        address=address
    )



@app.route('/pay-cart', methods=['POST', 'GET'])
def pay_cart():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cart = session.get('cart', {})

    if not cart:
        return redirect('/cart')

    selected_address = session.get('selected_address_id')

    if not selected_address:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM address WHERE user_id = %s", (user_id,))
        addresses = cursor.fetchall()
        if addresses:
            return redirect('/address')
        else:
            return redirect('/address')

    # ✅ Extract product IDs from session cart keys
    product_ids = list({int(key.split('_')[0]) for key in cart.keys()})
    if not product_ids:
        return redirect('/cart')

    format_strings = ','.join(['%s'] * len(product_ids))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(f"SELECT id, price FROM products WHERE id IN ({format_strings})", tuple(product_ids))
    products = cursor.fetchall()

    # ✅ Recalculate total based on live product prices and current cart quantities
    total = 0
    for p in products:
        matches = [key for key in cart if key.startswith(f"{p['id']}_")]
        for key in matches:
            total += float(p['price']) * int(cart[key])

    # ✅ Create Razorpay order with accurate amount
    payment = razorpay_client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    session['cart_payment'] = {
        'payment_id': payment['id'],
        'products': cart,
        'amount': total
    }

    return render_template("pay-cart.html", payment=payment, total=round(total, 2))




@app.route('/cart-payment-success/<payment_id>', methods=['GET'])
def cart_payment_success(payment_id):
    if 'user_id' not in session or 'cart_payment' not in session:
        return redirect('/')

    user_id = session['user_id']
    cart_data = session.pop('cart_payment')
    cart = cart_data['products']
    address_id = session.get('selected_address_id')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Ensure default product exists
    cursor.execute("SELECT id FROM products WHERE name = 'Default Product' LIMIT 1")
    default_product = cursor.fetchone()
    if not default_product:
        cursor.execute("""
            INSERT INTO products (name, description, price, image, category, status)
            VALUES ('Default Product', 'This is a placeholder product.', 0.00, 'default.jpg', 'tshirts', 'active')
        """)
        mysql.connection.commit()
        default_product_id = cursor.lastrowid
    else:
        default_product_id = default_product['id']

    # Insert orders
    for cart_key, qty in cart.items():
        try:
            product_id, size = cart_key.split('_')
            product_id = int(product_id)
        except ValueError:
            continue  # skip invalid keys

        # Validate product_id
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        valid_product = cursor.fetchone()
        if not valid_product:
            product_id = default_product_id  # fallback

        for _ in range(int(qty)):
            cursor.execute("""
                INSERT INTO orders (user_id, product_id, size, payment_id, address_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, product_id, size, payment_id, address_id))

    mysql.connection.commit()

    # Clear cart
    session.pop('cart', None)

    return render_template("payment-success.html", payment_id=payment_id)



@app.route('/admin/upload-ad', methods=['POST'])
def upload_ad():
    file = request.files.get('ad_image')
    if file:
        filename = 'homepage_ad.jpg'
        ad_folder = os.path.join('static', 'ads')
        os.makedirs(ad_folder, exist_ok=True)
        file.save(os.path.join(ad_folder, filename))
        return jsonify({'success': True, 'message': '✅ Ad uploaded successfully.'})
    return jsonify({'success': False, 'message': '❌ No file selected.'})


@app.route('/admin/remove-ad', methods=['POST'])
def remove_ad():
    ad_path = os.path.join('static', 'ads', 'homepage_ad.jpg')
    if os.path.exists(ad_path):
        os.remove(ad_path)
        return jsonify({'success': True, 'message': '🗑️ Ad image removed.'})
    else:
        return jsonify({'success': False, 'message': '⚠️ No ad image found.'})





@app.route('/address', methods=['GET'])
def address_page():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM address WHERE user_id = %s", (user_id,))
    addresses = cursor.fetchall()

    # ✅ If only one address and already selected, ask confirmation directly
    selected_address_id = session.get('selected_address_id')
    selected_address = None

    if selected_address_id:
        cursor.execute("SELECT * FROM address WHERE id = %s AND user_id = %s", (selected_address_id, user_id))
        selected_address = cursor.fetchone()
        if selected_address:
            return render_template('confirm-address.html', address=selected_address)

    return render_template('address.html', addresses=addresses)



@app.route('/add-address', methods=['POST'])
def add_address():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    state = request.form.get('state')
    district = request.form.get('district')
    address = request.form.get('address')
    landmark = request.form.get('landmark')
    pincode = request.form.get('pincode')
    mobile = request.form.get('mobile')


    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO address (user_id, state, district, address, landmark, pincode, mobile)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, state, district, address, landmark, pincode, mobile))


    mysql.connection.commit()

    session['selected_address_id'] = cursor.lastrowid
    cursor.close()

    return redirect('/cart')


@app.route('/reset-address')
def reset_address():
    session.pop('selected_address_id', None)
    return redirect('/cart')

@app.route('/manage-addresses', methods=['GET', 'POST'])
def manage_addresses():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch all saved addresses
    cursor.execute("SELECT * FROM address WHERE user_id = %s", (user_id,))


    addresses = cursor.fetchall()
    selected_id = session.get('selected_address_id')

    return render_template("manage-addresses.html", addresses=addresses, selected_id=selected_id)


@app.route('/manage-addresses/add', methods=['POST'])
def add_address_from_manage_page():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    state = request.form.get('state')
    district = request.form.get('district')
    address = request.form.get('address')
    landmark = request.form.get('landmark')
    pincode = request.form.get('pincode')
    mobile = request.form.get('mobile')  # ✅ fetch mobile

    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO address (user_id, state, district, address, landmark, pincode, mobile)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, state, district, address, landmark, pincode, mobile))  # ✅ include mobile

    mysql.connection.commit()
    session['selected_address_id'] = cursor.lastrowid

    return redirect('/manage-addresses')




@app.route('/select-address/<int:address_id>', methods=['POST'])
def choose_address(address_id):
    session['selected_address_id'] = address_id

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    return redirect('/cart')



@app.route('/delete-address/<int:address_id>', methods=['POST'])
def delete_address(address_id):
    if 'user_id' not in session:
        return redirect('/login')
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM address WHERE id = %s AND user_id = %s", (address_id, session['user_id']))
    mysql.connection.commit()
    return redirect('/manage-addresses')


@app.route('/edit-address/<int:address_id>', methods=['GET', 'POST'])
def edit_address(address_id):
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        state = request.form['state']
        district = request.form['district']
        address = request.form['address']
        landmark = request.form['landmark']
        pincode = request.form['pincode']
        mobile = request.form['mobile']

        cursor.execute("""
            UPDATE address
            SET state = %s, district = %s, address = %s, landmark = %s, pincode = %s, mobile = %s
            WHERE id = %s AND user_id = %s
        """, (state, district, address, landmark, pincode, mobile, address_id, session['user_id']))
        
        mysql.connection.commit()
        flash("Address updated successfully!")
        return redirect('/manage-addresses')

    # GET method – fetch address data to pre-fill form
    cursor.execute("SELECT * FROM address WHERE id = %s AND user_id = %s", (address_id, session['user_id']))
    address = cursor.fetchone()

    if not address:
        return "Address not found", 404

    return render_template('edit-address.html', address=address)


@app.route('/admin/registered-users')
def admin_registered_users():
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, mobile, email FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    return render_template('admin-users.html', users=users)



from collections import defaultdict
@app.route('/admin/orders')
def admin_orders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Try selecting size column only if it exists
    try:
        query = """
            SELECT o.id AS order_id,
                   u.name AS user_name,
                   p.name AS product_name,
                   p.price,
                   o.size,  -- safe to use now
                   o.payment_id,
                   o.order_time,
                   a.mobile,
                   CONCAT(a.address, ', ', a.landmark, ', ', a.district, ', ', a.state, ' - ', a.pincode) AS full_address
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN products p ON o.product_id = p.id
            LEFT JOIN address a ON o.address_id = a.id
            ORDER BY o.order_time DESC
        """
        cursor.execute(query)
        orders = cursor.fetchall()
    except MySQLdb.OperationalError as e:
        # Fallback if size column doesn't exist (e.g., migration not complete)
        if "Unknown column 'o.size'" in str(e):
            query = """
                SELECT o.id AS order_id,
                       u.name AS user_name,
                       p.name AS product_name,
                       p.price,
                       o.payment_id,
                       o.order_time,
                       a.mobile,
                       CONCAT(a.address, ', ', a.landmark, ', ', a.district, ', ', a.state, ' - ', a.pincode) AS full_address
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN products p ON o.product_id = p.id
                LEFT JOIN address a ON o.address_id = a.id
                ORDER BY o.order_time DESC
            """
            cursor.execute(query)
            orders = cursor.fetchall()
        else:
            raise e

    

    grouped_orders = defaultdict(list)
    for order in orders:
        grouped_orders[order['payment_id']].append(order)

    return render_template("admin_orders.html", grouped_orders=grouped_orders)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    row = cursor.fetchone()

    if not row:
        return "Product not found", 404

    product = {
        'id': row[0],
        'name': row[1],
        'description': row[2],
        'price': row[3],
        'status': (row[6] or '').strip().lower(),
        'sizes': (row[7] or ''),
        'size_chart': row[8]  # ✅ Add this line if it's the 9th column
    }


    cursor.execute("SELECT image FROM product_images WHERE product_id = %s", (product_id,))
    product['images'] = [img[0] for img in cursor.fetchall()]

    cursor.close()
    return render_template('product_detail.html', product=product)







@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            return render_template("admin-register.html", error="❗ Admin ID already exists.")

        cursor.execute("INSERT INTO admin (admin_id, password) VALUES (%s, %s)", (admin_id, password))
        mysql.connection.commit()

        return render_template("admin-register.html", success="✅ Admin registered successfully!")

    return render_template("admin-register.html")


from slugify import slugify  # pip install python-slugify
import MySQLdb
from werkzeug.utils import secure_filename

# ------------------ Manage Category (Admin) ------------------ #
@app.route('/admin/manage-category', methods=['GET', 'POST'])
def manage_category():
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        position = int(request.form.get('position', 0) or 0)
        is_active = 1 if request.form.get('is_active') == 'on' else 0

        if not name:
            flash("Name is required", "danger")
            return redirect('/admin/manage-category')

        slug = slugify(name)

        # Uniqueness check (don’t collide with existing)
        cursor.execute("SELECT id FROM categories WHERE slug = %s", (slug,))
        if cursor.fetchone():
            flash("Category with this name already exists.", "danger")
            return redirect('/admin/manage-category')

        img = request.files.get('image')
        if not img or img.filename == '':
            flash("Image is required", "danger")
            return redirect('/admin/manage-category')

        filename = secure_filename(img.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(path)

        cursor.execute("""
            INSERT INTO categories (name, slug, image, position, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, slug, filename, position, is_active))
        mysql.connection.commit()
        flash("✅ Category added!", "success")
        return redirect('/admin/manage-category')

    # GET
    cursor.execute("SELECT * FROM categories ORDER BY position ASC, id DESC")
    categories = cursor.fetchall()
    return render_template('manage-category.html', categories=categories)


@app.route('/admin/category/<int:cat_id>/toggle', methods=['POST'])
def toggle_category(cat_id):
    if 'admin' not in session:
        return redirect('/admin-login')

    cursor = mysql.connection.cursor()
    new_state = request.form.get('is_active') == '1'
    cursor.execute("UPDATE categories SET is_active = %s WHERE id = %s", (1 if new_state else 0, cat_id))
    mysql.connection.commit()
    return redirect('/admin/manage-category')


@app.route('/admin/category/<int:cat_id>/delete', methods=['POST'])
def delete_category(cat_id):
    """
    Delete the category AND all products (and their images) that belong to it.
    This matches your requirement: if a category is removed, products under it
    should not appear anywhere else and should be deleted from SQL too.
    """
    if 'admin' not in session:
        return redirect('/admin-login')

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1) Get the slug first
    cur.execute("SELECT slug FROM categories WHERE id = %s", (cat_id,))
    row = cur.fetchone()
    if not row:
        flash("Category not found", "warning")
        return redirect('/admin/manage-category')

    slug = row['slug']

    try:
        # 2) Delete product_images of products in that category
        cur.execute("""
            DELETE pi FROM product_images pi
            JOIN products p ON pi.product_id = p.id
            WHERE LOWER(TRIM(p.category)) = %s
        """, (slug.lower(),))

        # 3) Delete products of that category
        cur.execute("DELETE FROM products WHERE LOWER(TRIM(category)) = %s", (slug.lower(),))

        # 4) Delete the category itself
        cur.execute("DELETE FROM categories WHERE id = %s", (cat_id,))

        mysql.connection.commit()
        flash("🗑 Category and all its products deleted.", "warning")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"❌ Failed to delete category: {e}", "danger")

    return redirect('/admin/manage-category')


@app.route('/admin/category/<int:cat_id>/edit', methods=['POST'])
def edit_category(cat_id):
    if 'admin' not in session:
        return redirect('/admin-login')

    name = request.form.get('name', '').strip()
    position = int(request.form.get('position', 0) or 0)
    is_active = 1 if request.form.get('is_active') == 'on' else 0

    if not name:
        flash("Name is required", "danger")
        return redirect('/admin/manage-category')

    slug = slugify(name)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Ensure slug uniqueness (excluding current category)
    cursor.execute("SELECT id FROM categories WHERE slug = %s AND id != %s", (slug, cat_id))
    if cursor.fetchone():
        flash("Another category with this name already exists.", "danger")
        return redirect('/admin/manage-category')

    # build query
    image_sql = ""
    params = [name, slug, position, is_active, cat_id]

    img = request.files.get('image')
    if img and img.filename:
        filename = secure_filename(img.filename)
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_sql = ", image = %s"
        params = [name, slug, position, is_active, filename, cat_id]

    cursor.execute(f"""
        UPDATE categories
        SET name = %s, slug = %s, position = %s, is_active = %s {image_sql}
        WHERE id = %s
    """, tuple(params))

    mysql.connection.commit()
    flash("✏️ Category updated", "success")
    return redirect('/admin/manage-category')



if __name__ == '__main__':
    app.run(debug=True) 