# BudgetBuddy - Personal Finance Tracker

A full-stack personal finance tracking application that helps you log income and expenses, set monthly budget goals, and visualize your financial habits through interactive charts.

## Features

- **Dashboard**: View total income, expenses, net balance, and transaction count for any month
- **Interactive Charts**: 
  - Bar chart comparing income vs expenses
  - Donut chart breaking down spending by category
  - Daily spending trend line
- **Transactions**: Search, filter, and manage all your transactions
- **Budgets**: Set monthly spending limits per category with visual progress bars
- **Budget Alerts**: Yellow warning at 80%, red alert when over budget
- **Trends**: 6-month overview of income vs expenses
- **Export**: Download transactions as CSV or JSON

## Tech Stack

### Backend
- **Flask** - Python web framework
- **MySQL** - Database (3rd normal form)
- **JWT** - Stateless authentication
- **bcrypt** - Password hashing
- **Flask-CORS** - Cross-origin requests

### Frontend
- **Vanilla JavaScript** - No framework, pure JS
- **Chart.js** - Interactive charts
- **CSS3** - Modern, responsive styling
- **localStorage** - Token persistence

## Database Schema (3NF)

```
users
├── id (PK)
├── email (unique)
├── password_hash
├── name
└── created_at

categories
├── id (PK)
├── name
└── type (income/expense)

transactions
├── id (PK)
├── user_id (FK → users)
├── category_id (FK → categories)
├── amount
├── description
├── date
├── notes
├── type (income/expense)
└── created_at

budgets
├── id (PK)
├── user_id (FK → users)
├── category_id (FK → categories)
├── amount
├── month
├── year
├── created_at
└── updated_at
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- Node.js (optional, for any frontend tooling)

### 1. Clone and Setup

```bash
cd BudgetBuddy/BudgetBuddy
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the `BudgetBuddy` directory:

```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials:

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=budgetbuddy
```

### 4. Create MySQL Database

```sql
CREATE DATABASE budgetbuddy;
```

### 5. Run the Backend

```bash
python app.py
```

The server will start on `http://localhost:5000`.

### 6. Open the Frontend

Open `index.html` in your browser (from the root `BudgetBuddy` directory), or serve it with a simple HTTP server:

```bash
# From the BudgetBuddy root directory (not BudgetBuddy/BudgetBuddy)
python -m http.server 8080
```

Then visit `http://localhost:8080`.

## API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - Login and get JWT token
- `GET /api/me` - Get current user (requires auth)

### Transactions
- `GET /api/transactions` - Get all transactions (filterable by month, year, search, type)
- `POST /api/transactions` - Create new transaction
- `DELETE /api/transactions/:id` - Delete transaction

### Categories
- `GET /api/categories` - Get all categories (filterable by type)

### Budgets
- `GET /api/budgets` - Get all budgets for current month
- `POST /api/budgets` - Create or update budget
- `DELETE /api/budgets/:id` - Delete budget
- `GET /api/budgets/progress` - Get budget progress with spending vs limits

### Dashboard
- `GET /api/dashboard/stats` - Get total income, expenses, balance, transaction count
- `GET /api/dashboard/category-breakdown` - Get expense breakdown by category
- `GET /api/dashboard/daily-spending` - Get daily spending for month
- `GET /api/dashboard/trends` - Get 6-month income vs expense trends

### Export
- `GET /api/export` - Get all transactions as JSON

## Usage

1. **Register**: Create an account with your email and password
2. **Add Transactions**: Go to "Add Transaction" and log your income/expenses
3. **Set Budgets**: Navigate to "Budgets" and set monthly limits for expense categories
4. **Monitor**: Check the dashboard for real-time insights and budget alerts
5. **Analyze**: Use the Trends page to spot patterns over time
6. **Export**: Download your data anytime as CSV or JSON

## Budget Alert System

- **Normal** (0-79%): Green progress bar
- **Warning** (80-99%): Yellow progress bar + dashboard alert
- **Over** (100%+): Red progress bar + dashboard alert

## Security Features

- Passwords hashed with bcrypt before storage
- JWT tokens for stateless authentication
- Token expires after 24 hours
- All API endpoints (except login/register) require authentication
- User data isolation - users can only access their own data

## Project Structure

```
BudgetBuddy/
├── index.html              # Main HTML file (SPA)
├── assets/
│   ├── css/
│   │   └── style.css       # All styles
│   └── js/
│       └── app.js          # Frontend logic
└── BudgetBuddy/
    ├── app.py              # Flask backend
    ├── requirements.txt    # Python dependencies
    ├── .env.example        # Environment template
    └── .env                # Your configuration (create from example)
```

## License

MIT License - Feel free to use this for your personal finance tracking!
