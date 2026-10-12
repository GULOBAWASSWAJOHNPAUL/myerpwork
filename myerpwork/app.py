from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DB_NAME = 'erp_system.db'

def init_db():
    """Initializes the single integrated database with relational constraints."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Module 1: Materials Management/ Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT NOT NULL,
            unit_price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0)
        )
    ''')

    # Module 2: Sales and Financials Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_name TEXT NOT NULL,
            total_amount REAL NOT NULL DEFAULT 0.00,
            payment_status TEXT CHECK (payment_status IN ('Pending', 'Paid', 'Cancelled')) DEFAULT 'Paid'
        )
    ''')

    # Inter-module Bridge Table (Enforces single source of truth data flow)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        
        )
    ''')

    conn.commit()
    conn.close()

    @app.route('/')
    def index():
        """Renders the dashboard with current inventory and finanicial records."""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM products')
        products = cursor.fetchall()

        cursor.execute('SELECT * FROM orders ORDER BY order_date DESC')
        orders = cursor.fetchall()

        conn.close()
        return render_template('index.html', products=products, orders=orders)

    @app.route('/add_product', methods=['POST'])
    def add_product():
        """Inventory Module: Add new product stock."""
        name = request.form['name']
        sku = request.form['sku']
        unit_price = float(request.form['unit_price'])
        stock_quantity = int(request.form['stock_quantity'])

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO products (name, sku, unit_price, stock_quantity) VALUES (?, ?, ?, ?)",
                           (name, sku, unit_price, stock_quantity))
            conn.commit()
        except Exception as e:
            print(f"Error adding product: {e}")
        finally:
            conn.close()

        return redirect(url_for('index'))

 @app.route("/add_order", methods=["POST"])
def add_order():
    customer_name = request.form['customer_name']
    product_id = int(request.form['product_id'])
    quantity_sold = int(request.form['quantity_sold'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT stock_quantity, unit_price FROM products WHERE product_id = ?",
            (product_id,)
        )
        product = cursor.fetchone()

        if not product or product[0] < quantity_sold:
            raise ValueError("Insufficient stock available.")

        _, unit_price = product
        total_amount = unit_price * quantity_sold

        cursor.execute(
            "INSERT INTO orders (customer_name, total_amount, payment_status) "
            "VALUES (?, ?, ?)",
            (customer_name, total_amount, 'Paid')
        )
        order_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO order_items "
            "(order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, product_id, quantity_sold, unit_price)
        )

        cursor.execute(
            "UPDATE products SET stock_quantity = stock_quantity - ? "
            "WHERE product_id = ?",
            (quantity_sold, product_id)
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Transaction failed: {e}")
    finally:
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()