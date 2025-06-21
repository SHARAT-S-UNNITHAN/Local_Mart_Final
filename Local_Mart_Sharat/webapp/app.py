from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Database initialization
def init_db():
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
            address TEXT,
            store_name TEXT,
            license_file TEXT,
            store_images TEXT,
            approved INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )''')
        c.execute("PRAGMA table_info(products)")
        columns = {info[1]: info for info in c.fetchall()}
        if 'category' not in columns or columns['category'][2].upper() != 'INTEGER' or 'stock' not in columns:
            c.execute('''CREATE TABLE products_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                image TEXT,
                category INTEGER NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE,
                FOREIGN KEY (category) REFERENCES categories(id)
            )''')
            if 'products' in [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                c.execute('''INSERT OR IGNORE INTO categories (name) VALUES ('Other')''')
                c.execute('SELECT id FROM categories WHERE name = "Other"')
                other_id = c.fetchone()[0]
                c.execute('''INSERT INTO products_new (id, seller_id, name, description, price, image, category, stock)
                            SELECT id, seller_id, name, description, price, image, ?, 100
                            FROM products''', (other_id,))
                c.execute('DROP TABLE products')
            c.execute('ALTER TABLE products_new RENAME TO products')
        c.execute('''CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL,
            product_ids TEXT NOT NULL,
            quantities TEXT NOT NULL,
            total_price REAL NOT NULL,
            payment_method TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')
        c.execute('''INSERT OR IGNORE INTO users (username, email, password, role) 
                     VALUES ('admin', 'admin@example.com', 'admin123', 'admin')''')
        initial_categories = ['Fashion', 'Electronics', 'Home', 'Food', 'Books', 'Sports', 'Other']
        for cat in initial_categories:
            c.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,))
        conn.commit()

# File upload helper
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper to fetch categories
def get_categories():
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, name FROM categories ORDER BY name')
        return c.fetchall()

# Routes
@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/home')
def home():
    cart_count = 0
    is_approved_seller = False
    categories = [cat[1] for cat in get_categories()]
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT p.id, p.name, p.description, p.price, p.image, s.store_name, c.name, p.stock
                     FROM products p 
                     JOIN sellers s ON p.seller_id = s.id 
                     JOIN categories c ON p.category = c.id
                     WHERE s.approved = 1''')
        products = c.fetchall()
        c.execute('''SELECT s.id, s.user_id, s.store_name, s.phone, s.address, s.store_images, u.username 
                     FROM sellers s JOIN users u ON s.user_id = u.id WHERE s.approved = 1''')
        sellers = c.fetchall()
        if 'user_id' in session and session.get('role') != 'seller':
            if 'cart' in session:
                cart_count = sum(quantity for product_id, quantity in session['cart'].items())
            else:
                c.execute('SELECT SUM(quantity) FROM cart WHERE user_id = ?', (session['user_id'],))
                result = c.fetchone()[0]
                cart_count = result or 0
        if 'user_id' in session and session.get('role') == 'seller':
            c.execute('SELECT approved FROM sellers WHERE user_id = ?', (session['user_id'],))
            seller = c.fetchone()
            if seller and seller[0] == 1:
                is_approved_seller = True
    return render_template('home.html', products=products, sellers=sellers, cart_count=cart_count, 
                          is_approved_seller=is_approved_seller, categories=categories)

@app.route('/info')
def info():
    cart_count = len(session.get('cart', {}))
    return render_template('info.html', cart_count=cart_count, session=session)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    sort = request.args.get('sort', 're relevant')
    cart_count = 0
    categories = [cat[1] for cat in get_categories()]

    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        sql = '''SELECT p.id, p.name, p.description, p.price, p.image, s.store_name, c.name, p.stock
                 FROM products p 
                 JOIN sellers s ON p.seller_id = s.id 
                 JOIN categories c ON p.category = c.id
                 WHERE s.approved = 1'''
        params = []

        if query:
            sql += ' AND (p.name LIKE ? OR p.description LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])

        if category and category in categories:
            sql += ' AND c.name = ?'
            params.append(category)

        if min_price and min_price.isdigit():
            sql += ' AND p.price >= ?'
            params.append(float(min_price))

        if max_price and max_price.isdigit():
            sql += ' AND p.price <= ?'
            params.append(float(max_price))

        if sort == 'price_low':
            sql += ' ORDER BY p.price ASC'
        elif sort == 'price_high':
            sql += ' ORDER BY p.price DESC'
        else:
            if query:
                sql += ' ORDER BY (p.name LIKE ? + p.description LIKE ?) DESC'
                params.extend([f'{query}%', f'{query}%'])

        c.execute(sql, params)
        products = c.fetchall()

        if 'user_id' in session and session.get('role') != 'seller':
            if 'cart' in session:
                cart_count = sum(quantity for product_id, quantity in session['cart'].items())
            else:
                c.execute('SELECT SUM(quantity) FROM cart WHERE user_id = ?', (session['user_id'],))
                result = c.fetchone()[0]
                cart_count = result or 0

    return render_template('search.html', products=products, query=query, category=category,
                          min_price=min_price, max_price=max_price, sort=sort,
                          cart_count=cart_count, categories=categories)

@app.route('/seller_dashboard', methods=['GET', 'POST'])
def seller_dashboard():
    if 'user_id' not in session or session['role'] != 'seller':
        flash('Please sign in as a seller.')
        return redirect(url_for('signin'))
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('SELECT approved, id FROM sellers WHERE user_id = ?', (session['user_id'],))
        seller = c.fetchone()
        if not seller or seller[0] == 0:
            flash('Your seller account is not approved yet.')
            return redirect(url_for('home'))
        
        seller_id = seller[1]
        
        # Handle add product
        if request.method == 'POST' and 'add_product' in request.form:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '')
            category_id = request.form.get('category_id', '')
            stock = request.form.get('stock', '')
            image = request.files.get('image')
            
            if not name or not description or not price or not category_id or not stock:
                flash('All fields are required.')
            else:
                try:
                    price = float(price)
                    stock = int(stock)
                    if price <= 0 or stock < 0:
                        raise ValueError
                    c.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
                    if not c.fetchone():
                        flash('Invalid category selected.')
                    else:
                        filename = 'default_product.jpg'
                        if image and allowed_file(image.filename):
                            filename = secure_filename(image.filename)
                            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        c.execute('''INSERT INTO products (seller_id, name, description, price, image, category, stock) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                 (seller_id, name, description, price, filename, category_id, stock))
                        conn.commit()
                        flash('Product added successfully!')
                except ValueError:
                    flash('Invalid price or stock.')
                except sqlite3.Error:
                    flash('Error adding product.')
            return redirect(url_for('seller_dashboard'))
        
        # Handle product deletion
        if request.method == 'POST' and 'delete_product_id' in request.form:
            product_id = request.form['delete_product_id']
            c.execute('SELECT seller_id FROM products WHERE id = ?', (product_id,))
            product = c.fetchone()
            if product and product[0] == seller_id:
                c.execute('DELETE FROM cart WHERE product_id = ?', (product_id,))
                c.execute('DELETE FROM products WHERE id = ? AND seller_id = ?', (product_id, seller_id))
                conn.commit()
                flash('Product deleted successfully!')
            else:
                flash('Product not found or unauthorized.')
            return redirect(url_for('seller_dashboard'))
        
        # Handle product editing
        if request.method == 'POST' and 'edit_product_id' in request.form:
            product_id = request.form['edit_product_id']
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '')
            category_id = request.form.get('category_id', '')
            stock = request.form.get('stock', '')
            image = request.files.get('image')
            
            if not name or not description or not price or not category_id or not stock:
                flash('All fields are required.')
            else:
                try:
                    price = float(price)
                    stock = int(stock)
                    if price <= 0 or stock < 0:
                        raise ValueError
                    c.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
                    if not c.fetchone():
                        flash('Invalid category selected.')
                    else:
                        c.execute('SELECT seller_id FROM products WHERE id = ?', (product_id,))
                        product = c.fetchone()
                        if product and product[0] == seller_id:
                            update_data = [name, description, price, category_id, stock]
                            if image and allowed_file(image.filename):
                                filename = secure_filename(image.filename)
                                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                                update_data.append(filename)
                                c.execute('''UPDATE products SET name = ?, description = ?, price = ?, category = ?, stock = ?, image = ? 
                                             WHERE id = ? AND seller_id = ?''', 
                                         update_data + [product_id, seller_id])
                            else:
                                c.execute('''UPDATE products SET name = ?, description = ?, price = ?, category = ?, stock = ? 
                                             WHERE id = ? AND seller_id = ?''', 
                                         update_data + [product_id, seller_id])
                            conn.commit()
                            flash('Product updated successfully!')
                        else:
                            flash('Product not found or unauthorized.')
                except ValueError:
                    flash('Invalid price or stock.')
                except sqlite3.Error:
                    flash('Error updating product.')
            return redirect(url_for('seller_dashboard'))
        
        # Fetch seller's products
        c.execute('''SELECT p.id, p.name, p.description, p.price, p.image, c.name, p.stock 
                     FROM products p JOIN categories c ON p.category = c.id 
                     WHERE p.seller_id = ?''', (seller_id,))
        products = c.fetchall()
        
        # Fetch orders containing seller's products
        c.execute('SELECT id FROM products WHERE seller_id = ?', (seller_id,))
        seller_product_ids = {str(row[0]) for row in c.fetchall()}
        logger.debug(f"Seller product IDs for seller_id {seller_id}: {seller_product_ids}")
        c.execute('SELECT id, user_id, full_name, product_ids, quantities, total_price, order_date FROM orders')
        all_orders = c.fetchall()
        orders = []
        for order in all_orders:
            order_id, user_id, full_name, product_ids, quantities, total_price, order_date = order
            logger.debug(f"Processing order {order_id} with user_id {user_id}")
            product_id_list = product_ids.split(',')
            quantity_list = quantities.split(',')
            relevant_products = []
            for pid, qty in zip(product_id_list, quantity_list):
                if pid in seller_product_ids:
                    c.execute('SELECT name, price FROM products WHERE id = ?', (int(pid),))
                    product = c.fetchone()
                    if product:
                        relevant_products.append({
                            'name': product[0],
                            'quantity': int(qty),
                            'price': float(product[1]),
                            'subtotal': float(product[1]) * int(qty)
                        })
            if relevant_products:
                c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                username = user[0] if user else 'Unknown'
                logger.debug(f"Username for user_id {user_id}: {username}")
                orders.append({
                    'id': order_id,
                    'customer_name': full_name,
                    'username': username,
                    'products': relevant_products,
                    'total_price': sum(p['subtotal'] for p in relevant_products),
                    'order_date': order_date
                })
    
    categories = get_categories()
    return render_template('seller_dashboard.html', products=products, categories=categories, orders=orders)

@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        flash('Please sign in to access your account.')
        return redirect(url_for('signin'))
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email, role FROM users WHERE id = ?', (session['user_id'],))
        user = c.fetchone()
        if not user:
            flash('User not found.')
            session.clear()
            return redirect(url_for('signin'))
        
        seller = None
        if user[3] == 'seller':
            c.execute('''SELECT store_name, phone, address, approved, license_file, store_images 
                         FROM sellers WHERE user_id = ?''', (session['user_id'],))
            seller = c.fetchone()
        
        cart_items = []
        total_price = 0.0
        cart_count = 0
        if user[3] != 'seller':
            c.execute('''SELECT p.id, p.name, p.price, p.image, c.quantity, s.store_name, cat.name, p.stock
                        FROM cart c
                        JOIN products p ON c.product_id = p.id
                        JOIN sellers s ON p.seller_id = s.id
                        JOIN categories cat ON p.category = cat.id
                        WHERE c.user_id = ? AND s.approved = 1''', (session['user_id'],))
            cart_items = c.fetchall()
            total_price = sum(item[2] * item[4] for item in cart_items)
            cart_count = sum(item[4] for item in cart_items)
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not username or not email:
                flash('Username and email are required.')
            else:
                try:
                    c.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, session['user_id']))
                    if c.fetchone():
                        flash('Username already taken.')
                    else:
                        c.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
                        if c.fetchone():
                            flash('Email already taken.')
                        else:
                            if password:
                                c.execute('UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?',
                                         (username, email, password, session['user_id']))
                            else:
                                c.execute('UPDATE users SET username = ?, email = ? WHERE id = ?',
                                         (username, email, session['user_id']))
                            conn.commit()
                            flash('Profile updated successfully!')
                            return redirect(url_for('account'))
                except sqlite3.IntegrityError:
                    flash('Error updating profile.')
            return render_template('account.html', user=user, seller=seller, cart_items=cart_items, total_price=total_price, cart_count=cart_count)
    
    return render_template('account.html', user=user, seller=seller, cart_items=cart_items, total_price=total_price, cart_count=cart_count)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cart_count = 0
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT p.id, p.name, p.description, p.price, p.image, s.store_name, c.name, p.stock
                     FROM products p 
                     JOIN sellers s ON p.seller_id = s.id 
                     JOIN categories c ON p.category = c.id
                     WHERE p.id = ? AND s.approved = 1''', (product_id,))
        product = c.fetchone()
        if 'user_id' in session and session.get('role') != 'seller':
            if 'cart' in session:
                cart_count = sum(quantity for product_id, quantity in session['cart'].items())
            else:
                c.execute('SELECT SUM(quantity) FROM cart WHERE user_id = ?', (session['user_id'],))
                result = c.fetchone()[0]
                cart_count = result or 0
    if product:
        return render_template('product_detail.html', product=product, cart_count=cart_count)
    flash('Product not found.')
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' in session and session.get('role') == 'seller':
        flash('Sellers cannot add products to the cart.')
        return redirect(url_for('product_detail', product_id=product_id))
    
    quantity = int(request.form.get('quantity', 1))
    if quantity < 1:
        flash('Invalid quantity.')
        return redirect(url_for('product_detail', product_id=product_id))
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('SELECT stock, seller_id FROM products WHERE id = ?', (product_id,))
        product = c.fetchone()
        if not product:
            flash('Product not found.')
            return redirect(url_for('product_detail', product_id=product_id))
        stock, seller_id = product
        c.execute('SELECT approved FROM sellers WHERE id = ?', (seller_id,))
        seller = c.fetchone()
        if not seller or seller[0] == 0:
            flash('Product is from an unapproved seller.')
            return redirect(url_for('product_detail', product_id=product_id))
        if stock < quantity:
            flash(f'Insufficient stock. Available: {stock}.')
            return redirect(url_for('product_detail', product_id=product_id))
    
        logger.debug(f"Adding product {product_id} with quantity {quantity} for user_id {session.get('user_id')}")
    
        if 'user_id' in session:
            c.execute('SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?', 
                     (session['user_id'], product_id))
            existing = c.fetchone()
            if existing:
                new_quantity = existing[0] + quantity
                if new_quantity > stock:
                    flash(f'Cannot add {quantity} more. Total exceeds stock: {stock}.')
                    return redirect(url_for('product_detail', product_id=product_id))
                c.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?', 
                         (new_quantity, session['user_id'], product_id))
            else:
                c.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', 
                         (session['user_id'], product_id, quantity))
            conn.commit()
            logger.debug(f"Cart updated in DB: user_id {session['user_id']}, product_id {product_id}, quantity {new_quantity if existing else quantity}")
        else:
            if 'cart' not in session:
                session['cart'] = {}
            cart = session['cart']
            cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
            if cart[str(product_id)] > stock:
                flash(f'Cannot add {quantity} more. Total exceeds stock: {stock}.')
                cart[str(product_id)] = max(0, cart[str(product_id)] - quantity)
                session['cart'] = cart
                session.modified = True
                return redirect(url_for('product_detail', product_id=product_id))
            session['cart'] = cart
            session.modified = True
            logger.debug(f"Cart updated in session: {session['cart']}")
    
    flash('Product added to cart!')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' in session and session.get('role') == 'seller':
        flash('Sellers cannot access the cart.')
        return redirect(url_for('home'))
    
    action = request.form.get('action')
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('SELECT quantity, stock FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = ? AND c.product_id = ?', 
                 (session['user_id'], product_id))
        result = c.fetchone()
        if not result:
            flash('Item not found in cart.')
            return redirect(url_for('cart'))
        
        current_quantity, stock = result
        new_quantity = current_quantity
        
        if action == 'increase' and current_quantity < stock:
            new_quantity += 1
        elif action == 'decrease' and current_quantity > 1:
            new_quantity -= 1
        else:
            flash('Quantity cannot be updated.')
            return redirect(url_for('cart'))
        
        c.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?', 
                 (new_quantity, session['user_id'], product_id))
        conn.commit()
        flash('Cart updated successfully!')
    
    return redirect(url_for('cart'))

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    if 'user_id' in session and session.get('role') == 'seller':
        flash('Sellers cannot access the cart.')
        return redirect(url_for('home'))
    
    if 'cart' in session:
        session['cart'] = {}
        session.modified = True
    
    if 'user_id' in session:
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
            conn.commit()
    
    flash('Cart cleared successfully!')
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user_id' in session and session.get('role') == 'seller':
        flash('Sellers cannot access the cart.')
        return redirect(url_for('home'))
    
    cart_items = []
    total_price = 0.0
    cart_count = 0
    
    if 'user_id' in session:
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            c.execute('''SELECT p.id, p.name, p.price, p.image, c.quantity, s.store_name, cat.name, p.stock
                        FROM cart c
                        JOIN products p ON c.product_id = p.id
                        JOIN sellers s ON p.seller_id = s.id
                        JOIN categories cat ON p.category = cat.id
                        WHERE c.user_id = ? AND s.approved = 1''', (session['user_id'],))
            cart_items = c.fetchall()
            logger.debug(f"Cart items for user_id {session['user_id']}: {cart_items}")
            total_price = sum(item[2] * item[4] for item in cart_items)
            cart_count = sum(item[4] for item in cart_items)
    elif 'cart' in session:
        cart = session['cart']
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            for product_id, quantity in cart.items():
                c.execute('''SELECT p.id, p.name, p.price, p.image, ?, s.store_name, c.name, p.stock
                            FROM products p 
                            JOIN sellers s ON p.seller_id = s.id
                            JOIN categories c ON p.category = c.id
                            WHERE p.id = ? AND s.approved = 1''', (quantity, int(product_id)))
                item = c.fetchone()
                if item:
                    cart_items.append(item)
                    total_price += item[2] * item[4]
                    cart_count += item[4]
            logger.debug(f"Session cart items: {cart_items}")
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price, cart_count=cart_count)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session or session.get('role') == 'seller':
        flash('Please sign in as a customer to checkout.')
        return redirect(url_for('signin'))
    
    cart_items = []
    total_price = 0.0
    cart_count = 0
    user_details = None
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT p.id, p.name, p.price, p.image, c.quantity, s.store_name, cat.name, p.stock
                    FROM cart c
                    JOIN products p ON c.product_id = p.id
                    JOIN sellers s ON p.seller_id = s.id
                    JOIN categories cat ON p.category = cat.id
                    WHERE c.user_id = ? AND s.approved = 1''', (session['user_id'],))
        cart_items = c.fetchall()
        logger.debug(f"Checkout cart items for user_id {session['user_id']}: {cart_items}")
        total_price = sum(item[2] * item[4] for item in cart_items)
        cart_count = sum(item[4] for item in cart_items)
        
        if not cart_items:
            flash('Your cart is empty.')
            return redirect(url_for('cart'))
        
        # Check stock before proceeding
        for item in cart_items:
            if item[4] > item[7]:
                flash(f'Insufficient stock for {item[1]}. Available: {item[7]}.')
                return redirect(url_for('cart'))
        
        # Fetch user email
        c.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],))
        user_email = c.fetchone()
        if not user_email:
            flash('User email not found.')
            session.clear()
            return redirect(url_for('signin'))
        user_email = user_email[0]
        
        # Fetch latest order details
        c.execute('''SELECT full_name, phone, address FROM orders 
                     WHERE user_id = ? ORDER BY order_date DESC LIMIT 1''', (session['user_id'],))
        last_order = c.fetchone()
        if last_order:
            user_details = {
                'full_name': last_order[0],
                'phone': last_order[1],
                'address': last_order[2]
            }
        
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            
            if not full_name or not phone or not address:
                flash('All fields are required.')
            elif len(phone) < 10 or not phone.isdigit():
                flash('Please enter a valid phone number (at least 10 digits).')
            else:
                try:
                    # Verify cart items again
                    c.execute('''SELECT p.id, c.quantity, p.stock
                                FROM cart c JOIN products p ON c.product_id = p.id
                                WHERE c.user_id = ?''', (session['user_id'],))
                    current_items = c.fetchall()
                    if not current_items:
                        flash('Cart is empty during order placement.')
                        return redirect(url_for('cart'))
                    
                    # Prepare order data
                    product_ids = ','.join(str(item[0]) for item in cart_items)
                    quantities = ','.join(str(item[4]) for item in cart_items)
                    
                    # Update stock
                    for item in cart_items:
                        c.execute('UPDATE products SET stock = stock - ? WHERE id = ?', 
                                 (item[4], item[0]))
                    
                    # Insert order into orders table
                    c.execute('''INSERT INTO orders (user_id, full_name, phone, address, email, product_ids, quantities, total_price, payment_method)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (session['user_id'], full_name, phone, address, user_email, product_ids, quantities, total_price, 'Cash on Delivery'))
                    
                    # Clear the user's cart
                    c.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
                    conn.commit()
                    
                    flash('Order placed successfully! You will pay via Cash on Delivery.')
                    return redirect(url_for('home'))
                except sqlite3.Error as e:
                    logger.error(f"Error placing order: {e}")
                    flash('Error placing order. Please try again.')
            
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price, cart_count=cart_count, 
                          user_email=user_email, user_details=user_details)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'user_id' in session and session.get('role') == 'seller':
        flash('Sellers cannot access the cart.')
        return redirect(url_for('home'))
    
    if 'cart' in session:
        cart = session['cart']
        if str(product_id) in cart:
            del cart[str(product_id)]
            session['cart'] = cart
            session.modified = True
    
    if 'user_id' in session:
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?', 
                     (session['user_id'], product_id))
            conn.commit()
    
    flash('Product removed from cart.')
    return redirect(url_for('cart'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')
        
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            try:
                c.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                         (username, email, password, role))
                user_id = c.lastrowid
                
                if role == 'seller':
                    phone = request.form.get('phone', '').strip()
                    address = request.form.get('address', '').strip()
                    store_name = request.form.get('store_name', '').strip()
                    license_file = request.files.get('license')
                    store_images = request.files.getlist('store_images')
                    
                    if not phone or not address or not store_name or not license_file:
                        flash('All seller fields are required.')
                        return render_template('signup.html')
                    if not allowed_file(license_file.filename):
                        flash('Invalid license file format.')
                        return render_template('signup.html')
                    if len(phone) < 10 or not phone.isdigit():
                        flash('Please enter a valid phone number (at least 10 digits).')
                        return render_template('signup.html')
                    
                    filename = secure_filename(license_file.filename)
                    license_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    
                    image_paths = []
                    for img in store_images:
                        if img and allowed_file(img.filename):
                            img_filename = secure_filename(img.filename)
                            img.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
                            image_paths.append(img_filename)
                    
                    c.execute('INSERT INTO sellers (user_id, phone, address, store_name, license_file, store_images) VALUES (?, ?, ?, ?, ?, ?)',
                             (user_id, phone, address, store_name, filename, ','.join(image_paths)))
                
                conn.commit()
                flash('Sign-up successful! Awaiting admin approval for sellers.' if role == 'seller' else 'Sign-up successful!')
                return redirect(url_for('signin'))
            except sqlite3.IntegrityError:
                flash('Username or email already taken.')
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('ecommerce.db') as conn:
            c = conn.cursor()
            c.execute('SELECT id, role FROM users WHERE email = ? AND password = ?', (email, password))
            user = c.fetchone()
            if user:
                user_id, role = user
                session['user_id'] = user_id
                session['role'] = role
                logger.debug(f"User signed in: user_id {user_id}, role {role}")
                if role != 'seller' and 'cart' in session:
                    cart = session['cart']
                    logger.debug(f"Merging session cart: {cart}")
                    for product_id, quantity in cart.items():
                        try:
                            c.execute('SELECT id, stock, seller_id FROM products WHERE id = ?', (int(product_id),))
                            product = c.fetchone()
                            if product:
                                product_id, stock, seller_id = product
                                c.execute('SELECT approved FROM sellers WHERE id = ?', (seller_id,))
                                seller = c.fetchone()
                                if seller and seller[0] == 1 and stock >= quantity:
                                    c.execute('SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?', 
                                             (user_id, product_id))
                                    existing = c.fetchone()
                                    if existing:
                                        new_quantity = existing[0] + quantity
                                        if new_quantity <= stock:
                                            c.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?', 
                                                     (new_quantity, user_id, product_id))
                                            logger.debug(f"Updated cart: product_id {product_id}, new_quantity {new_quantity}")
                                        else:
                                            logger.warning(f"Cannot merge: product_id {product_id}, new_quantity {new_quantity} exceeds stock {stock}")
                                    else:
                                        c.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', 
                                                 (user_id, product_id, quantity))
                                        logger.debug(f"Inserted cart: product_id {product_id}, quantity {quantity}")
                                else:
                                    logger.warning(f"Skipped product_id {product_id}: unapproved seller or insufficient stock")
                            else:
                                logger.warning(f"Product not found: product_id {product_id}")
                        except sqlite3.Error as e:
                            logger.error(f"Error merging cart item {product_id}: {e}")
                    conn.commit()
                    session['cart'] = {}
                    session.modified = True
                    logger.debug("Session cart cleared after merge")
                if role == 'seller':
                    c.execute('SELECT approved FROM sellers WHERE user_id = ?', (user_id,))
                    seller = c.fetchone()
                    if seller and seller[0] == 0:
                        flash('Your seller account is awaiting admin approval.')
                        return redirect(url_for('home'))
                return redirect(url_for('home'))
            flash('Invalid credentials.')
    return render_template('signin.html')

@app.route('/signout')
def signout():
    session.clear()
    flash('You have been signed out.')
    return redirect(url_for('signin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Admin access only.')
        return redirect(url_for('signin'))
    
    with sqlite3.connect('ecommerce.db') as conn:
        c = conn.cursor()
        # Fetch all sellers
        c.execute('''SELECT s.id, s.user_id, s.store_name, s.phone, s.address, s.store_images, s.license_file, s.approved, u.username 
                     FROM sellers s JOIN users u ON s.user_id = u.id''')
        sellers = c.fetchall()
        
        # Fetch all users
        c.execute('SELECT id, username, email, role FROM users')
        users = c.fetchall()
        
        # Fetch all categories
        c.execute('SELECT id, name FROM categories ORDER BY name')
        categories = c.fetchall()
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'approve_seller':
                seller_id = request.form.get('seller_id')
                c.execute('UPDATE sellers SET approved = 1 WHERE id = ?', (seller_id,))
                conn.commit()
                flash('Seller approved successfully!')
            
            elif action == 'reject_seller':
                seller_id = request.form.get('seller_id')
                c.execute('SELECT user_id FROM sellers WHERE id = ?', (seller_id,))
                user_id = c.fetchone()
                if user_id:
                    c.execute('DELETE FROM sellers WHERE id = ?', (seller_id,))
                    conn.commit()
                    flash('Seller rejected and removed successfully!')
                else:
                    flash('Seller not found.')
            
            elif action == 'delete_user':
                user_id = request.form.get('user_id')
                c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                if user and user[0] == 'admin':
                    flash('Cannot delete admin users.')
                else:
                    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
                    conn.commit()
                    flash('User deleted successfully!')
            
            elif action == 'add_category':
                category_name = request.form.get('category_name', '').strip()
                if not category_name:
                    flash('Category name is required.')
                elif len(category_name) > 50:
                    flash('Category name must be 50 characters or less.')
                else:
                    try:
                        c.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
                        conn.commit()
                        flash('Category added successfully!')
                    except sqlite3.IntegrityError:
                        flash('Category already exists.')
            
            elif action == 'edit_category':
                category_id = request.form.get('category_id')
                category_name = request.form.get('category_name', '').strip()
                if not category_name:
                    flash('Category name is required.')
                elif len(category_name) > 50:
                    flash('Category name must be 50 characters or less.')
                else:
                    try:
                        c.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
                        if not c.fetchone():
                            flash('Category not found.')
                        else:
                            c.execute('UPDATE categories SET name = ? WHERE id = ?', (category_name, category_id))
                            conn.commit()
                            flash('Category updated successfully!')
                    except sqlite3.IntegrityError:
                        flash('Category name already exists.')
            
            elif action == 'delete_category':
                category_id = request.form.get('category_id')
                try:
                    c.execute('SELECT COUNT(*) FROM products WHERE category = ?', (category_id,))
                    product_count = c.fetchone()[0]
                    if product_count > 0:
                        flash('Cannot delete category as it is associated with products.')
                    else:
                        c.execute('DELETE FROM categories WHERE id = ?', (category_id,))
                        conn.commit()
                        flash('Category deleted successfully!')
                except sqlite3.Error:
                    flash('Error deleting category.')
            
            return redirect(url_for('admin'))
    
    return render_template('admin.html', sellers=sellers, users=users, categories=categories)

@app.route('/admin/download/<filename>')
def download_file(filename):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Admin access only.')
        return redirect(url_for('signin'))
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found.')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)