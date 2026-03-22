from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import bcrypt
import os
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'budgetbuddy')
        )
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create categories table (3NF - separate table for categories)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            type ENUM('income', 'expense') NOT NULL,
            UNIQUE KEY unique_category (name, type)
        )
    ''')
    
    # Create transactions table (3NF - references users and categories)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            category_id INT NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            description VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            notes TEXT,
            type ENUM('income', 'expense') NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
        )
    ''')
    
    # Create budgets table (3NF - references categories)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            category_id INT NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            month INT NOT NULL,
            year INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE KEY unique_budget (user_id, category_id, month, year)
        )
    ''')
    
    # Insert default categories
    default_expense_categories = [
        ('Food', 'expense'), ('Housing', 'expense'), ('Transport', 'expense'),
        ('Entertainment', 'expense'), ('Health', 'expense'), ('Utilities', 'expense'),
        ('Shopping', 'expense'), ('Education', 'expense'), ('Personal Care', 'expense'),
        ('Other', 'expense')
    ]
    default_income_categories = [
        ('Salary', 'income'), ('Freelance', 'income'), ('Investment', 'income'),
        ('Gift', 'income'), ('Other', 'income')
    ]
    
    all_categories = default_expense_categories + default_income_categories
    
    for name, cat_type in all_categories:
        cursor.execute('''
            INSERT IGNORE INTO categories (name, type) VALUES (%s, %s)
        ''', (name, cat_type))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully!")

# ============== Authentication Endpoints ==============

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['email', 'password', 'name']):
        return jsonify({'error': 'Email, password, and name are required'}), 400
    
    email = data['email'].lower().strip()
    password = data['password']
    name = data['name'].strip()
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Email already registered'}), 409
    
    # Hash password with bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        cursor.execute(
            'INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)',
            (email, password_hash, name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        access_token = create_access_token(identity={'user_id': user_id, 'email': email})
        
        return jsonify({
            'message': 'Registration successful',
            'access_token': access_token,
            'user': {'id': user_id, 'email': email, 'name': name}
        }), 201
    except Error as e:
        cursor.close()
        conn.close()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login and get access token."""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email'].lower().strip()
    password = data['password']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    access_token = create_access_token(identity={'user_id': user['id'], 'email': user['email']})
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {'id': user['id'], 'email': user['email'], 'name': user['name']}
    })

@app.route('/api/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user info."""
    identity = get_jwt_identity()
    return jsonify({'user': identity})

# ============== Transaction Endpoints ==============

@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    """Get all transactions for the current user with optional filters."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    search = request.args.get('search', '')
    filter_type = request.args.get('type', '')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT t.*, c.name as category_name 
        FROM transactions t 
        JOIN categories c ON t.category_id = c.id 
        WHERE t.user_id = %s
    '''
    params = [user_id]
    
    if month and year:
        query += ' AND MONTH(t.date) = %s AND YEAR(t.date) = %s'
        params.extend([month, year])
    
    if search:
        query += ' AND t.description LIKE %s'
        params.append(f'%{search}%')
    
    if filter_type in ['income', 'expense']:
        query += ' AND t.type = %s'
        params.append(filter_type)
    
    query += ' ORDER BY t.date DESC, t.created_at DESC'
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert Decimal to float for JSON serialization
    for t in transactions:
        t['amount'] = float(t['amount'])
    
    return jsonify({'transactions': transactions})

@app.route('/api/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    """Create a new transaction."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    data = request.get_json()
    
    required_fields = ['type', 'amount', 'description', 'date', 'category_id']
    if not all(k in data for k in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    # Verify category belongs to the correct type
    cursor.execute(
        'SELECT id FROM categories WHERE id = %s AND type = %s',
        (data['category_id'], data['type'])
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Invalid category for transaction type'}), 400
    
    try:
        cursor.execute('''
            INSERT INTO transactions (user_id, category_id, amount, description, date, notes, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            data['category_id'],
            data['amount'],
            data['description'],
            data['date'],
            data.get('notes', ''),
            data['type']
        ))
        conn.commit()
        transaction_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction_id': transaction_id
        }), 201
    except Error as e:
        cursor.close()
        conn.close()
        return jsonify({'error': f'Failed to create transaction: {str(e)}'}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """Delete a transaction."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute(
        'SELECT id FROM transactions WHERE id = %s AND user_id = %s',
        (transaction_id, user_id)
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Transaction not found'}), 404
    
    cursor.execute('DELETE FROM transactions WHERE id = %s AND user_id = %s', (transaction_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Transaction deleted successfully'})

# ============== Category Endpoints ==============

@app.route('/api/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories, optionally filtered by type."""
    cat_type = request.args.get('type', '')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    if cat_type in ['income', 'expense']:
        cursor.execute('SELECT * FROM categories WHERE type = %s ORDER BY name', (cat_type,))
    else:
        cursor.execute('SELECT * FROM categories ORDER BY type, name')
    
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify({'categories': categories})

# ============== Budget Endpoints ==============

@app.route('/api/budgets', methods=['GET'])
@jwt_required()
def get_budgets():
    """Get all budgets for the current user."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT b.*, c.name as category_name 
        FROM budgets b 
        JOIN categories c ON b.category_id = c.id 
        WHERE b.user_id = %s
    '''
    params = [user_id]
    
    if month and year:
        query += ' AND b.month = %s AND b.year = %s'
        params.extend([month, year])
    
    query += ' ORDER BY c.name'
    
    cursor.execute(query, params)
    budgets = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert Decimal to float
    for b in budgets:
        b['amount'] = float(b['amount'])
    
    return jsonify({'budgets': budgets})

@app.route('/api/budgets', methods=['POST'])
@jwt_required()
def create_budget():
    """Create or update a budget."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    data = request.get_json()
    
    required_fields = ['category_id', 'amount', 'month', 'year']
    if not all(k in data for k in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO budgets (user_id, category_id, amount, month, year)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE amount = VALUES(amount)
        ''', (user_id, data['category_id'], data['amount'], data['month'], data['year']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Budget saved successfully'}), 201
    except Error as e:
        cursor.close()
        conn.close()
        return jsonify({'error': f'Failed to save budget: {str(e)}'}), 500

@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@jwt_required()
def delete_budget(budget_id):
    """Delete a budget."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id FROM budgets WHERE id = %s AND user_id = %s',
        (budget_id, user_id)
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Budget not found'}), 404
    
    cursor.execute('DELETE FROM budgets WHERE id = %s AND user_id = %s', (budget_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Budget deleted successfully'})

# ============== Dashboard & Stats Endpoints ==============

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics for a specific month."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Get total income
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND type = 'income' AND MONTH(date) = %s AND YEAR(date) = %s
    ''', (user_id, month, year))
    total_income = float(cursor.fetchone()['total'])
    
    # Get total expenses
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND type = 'expense' AND MONTH(date) = %s AND YEAR(date) = %s
    ''', (user_id, month, year))
    total_expenses = float(cursor.fetchone()['total'])
    
    # Get transaction count
    cursor.execute('''
        SELECT COUNT(*) as count 
        FROM transactions 
        WHERE user_id = %s AND MONTH(date) = %s AND YEAR(date) = %s
    ''', (user_id, month, year))
    transaction_count = cursor.fetchone()['count']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_balance': total_income - total_expenses,
        'transaction_count': transaction_count
    })

@app.route('/api/dashboard/category-breakdown', methods=['GET'])
@jwt_required()
def get_category_breakdown():
    """Get expense breakdown by category for a specific month."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT c.name, COALESCE(SUM(t.amount), 0) as total 
        FROM categories c 
        LEFT JOIN transactions t ON c.id = t.category_id AND t.user_id = %s 
            AND MONTH(t.date) = %s AND YEAR(t.date) = %s AND t.type = 'expense'
        WHERE c.type = 'expense'
        GROUP BY c.id, c.name 
        ORDER BY total DESC
    ''', (user_id, month, year))
    
    breakdown = [{'category': row['name'], 'amount': float(row['total'])} for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return jsonify({'breakdown': breakdown})

@app.route('/api/dashboard/daily-spending', methods=['GET'])
@jwt_required()
def get_daily_spending():
    """Get daily spending for a specific month."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT DAY(date) as day, COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND type = 'expense' AND MONTH(date) = %s AND YEAR(date) = %s
        GROUP BY DAY(date), date 
        ORDER BY day
    ''', (user_id, month, year))
    
    daily = [{'day': row['day'], 'amount': float(row['total'])} for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return jsonify({'daily': daily})

@app.route('/api/dashboard/trends', methods=['GET'])
@jwt_required()
def get_trends():
    """Get 6-month income vs expense trends."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Get last 6 months
    cursor.execute('''
        SELECT 
            DATE_FORMAT(date, '%%Y-%%m') as month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
        FROM transactions 
        WHERE user_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(date, '%%Y-%%m')
        ORDER BY month
    ''', (user_id,))
    
    trends = [{
        'month': row['month'],
        'income': float(row['income']),
        'expenses': float(row['expenses'])
    } for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return jsonify({'trends': trends})

@app.route('/api/budgets/progress', methods=['GET'])
@jwt_required()
def get_budget_progress():
    """Get budget progress with spending vs limits for current month."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT 
            b.id,
            b.amount as budget_amount,
            b.month,
            b.year,
            c.name as category_name,
            COALESCE(SUM(t.amount), 0) as spent_amount
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON b.category_id = t.category_id 
            AND t.user_id = %s AND t.type = 'expense'
            AND MONTH(t.date) = %s AND YEAR(t.date) = %s
        WHERE b.user_id = %s AND b.month = %s AND b.year = %s
        GROUP BY b.id, b.amount, b.month, b.year, c.name
        ORDER BY c.name
    ''', (user_id, month, year, user_id, month, year))
    
    progress = []
    for row in cursor.fetchall():
        budget_amount = float(row['budget_amount'])
        spent_amount = float(row['spent_amount'])
        percentage = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
        
        progress.append({
            'id': row['id'],
            'category': row['category_name'],
            'budget_amount': budget_amount,
            'spent_amount': spent_amount,
            'percentage': min(percentage, 100),
            'status': 'over' if percentage > 100 else ('warning' if percentage >= 80 else 'normal')
        })
    
    cursor.close()
    conn.close()
    
    return jsonify({'progress': progress})

# ============== Export Endpoint ==============

@app.route('/api/export', methods=['GET'])
@jwt_required()
def export_transactions():
    """Export all transactions as JSON."""
    identity = get_jwt_identity()
    user_id = identity['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT t.*, c.name as category_name 
        FROM transactions t 
        JOIN categories c ON t.category_id = c.id 
        WHERE t.user_id = %s 
        ORDER BY t.date DESC, t.created_at DESC
    ''', (user_id,))
    
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert Decimal to float
    for t in transactions:
        t['amount'] = float(t['amount'])
        t['date'] = t['date'].isoformat() if t['date'] else None
        t['created_at'] = t['created_at'].isoformat() if t['created_at'] else None
    
    return jsonify({'transactions': transactions})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
