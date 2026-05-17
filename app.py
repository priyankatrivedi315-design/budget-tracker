# =======================
# BUDGET TRACKER (FLASK)
# =======================

from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = "secret123"

# ================= DATABASE CONFIG (RAILWAY FIXED) =================
db_url = os.getenv("DATABASE_URL")

# Fix for Railway PostgreSQL
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///budget.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

# ================= DATABASE MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    balance = db.Column(db.Float, default=35000)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    title = db.Column(db.String(100))
    amount = db.Column(db.Float)
    date = db.Column(db.String(50))

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100))
    target = db.Column(db.Float)
    saved = db.Column(db.Float, default=0)
    deadline = db.Column(db.String(50))
    category = db.Column(db.String(50))
    completed = db.Column(db.Boolean, default=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100))
    limit = db.Column(db.Float)
    color = db.Column(db.String(20), default='#a855f7')

# ================= HELPERS =================
def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

# ================= AUTH =================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/dashboard')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect('/')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# ================= DASHBOARD =================
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()

    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])

        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        user.balance -= amount

        exp = Expense(user_id=user.id, title=title, amount=amount, date=date)
        db.session.add(exp)
        db.session.commit()

        return redirect('/dashboard')

    total_spent = sum(e.amount for e in expenses)

    return render_template('dashboard.html',
                           user=user,
                           expenses=expenses,
                           total_spent=total_spent)

# ================= OTHER ROUTES =================
@app.route('/transactions')
@login_required
def transactions():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    return render_template('transactions.html', user=user, expenses=expenses)


@app.route('/wallet')
@login_required
def wallet():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    return render_template('wallet.html', user=user, expenses=expenses)


@app.route('/goals')
@login_required
def goals():
    user = current_user()
    goals = Goal.query.filter_by(user_id=user.id).all()
    return render_template('goals.html', user=user, goals=goals)


@app.route('/budget')
@login_required
def budget():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    budgets = Budget.query.filter_by(user_id=user.id).all()
    return render_template('budget.html', user=user, expenses=expenses, budgets=budgets)


@app.route('/summary')
@login_required
def summary():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()

    labels = [e.title for e in expenses]
    values = [e.amount for e in expenses]

    return render_template('analytics.html',
                           user=user,
                           labels=labels,
                           values=values,
                           expenses=expenses)

# ================= RUN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run()
