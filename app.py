# =======================
# BUDGET TRACKER (FLASK)
# =======================
# Features:
# - Register / Login (Authentication)
# - Fixed starting balance ($35000)
# - Add expenses (auto deduction)
# - Dashboard, Wallet, Transactions, Goals, Budget, Analytics, Settings

from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'

db = SQLAlchemy(app)

# ================= DATABASE =================
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

# ================= AUTH ROUTES =================
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
        new_user = User(email=email, password=password)
        db.session.add(new_user)
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
    return render_template('dashboard.html', user=user, expenses=expenses, total_spent=total_spent)

# ================= TRANSACTIONS =================
@app.route('/transactions')
@login_required
def transactions():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
    return render_template('transactions.html', user=user, expenses=expenses)

# ================= WALLET =================
@app.route('/wallet')
@login_required
def wallet():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    return render_template('wallet.html', user=user, expenses=expenses)

# ================= GOALS =================
@app.route('/goals')
@login_required
def goals():
    user = current_user()
    user_goals = Goal.query.filter_by(user_id=user.id).all()
    return render_template('goals.html', user=user, goals=user_goals)

@app.route('/add_goal', methods=['POST'])
@login_required
def add_goal():
    user = current_user()
    goal = Goal(
        user_id=user.id,
        name=request.form['name'],
        target=float(request.form['target']),
        saved=float(request.form.get('saved', 0)),
        deadline=request.form.get('deadline', ''),
        category=request.form.get('category', 'Other')
    )
    db.session.add(goal)
    db.session.commit()
    return redirect('/goals')

@app.route('/contribute_goal/<int:goal_id>', methods=['POST'])
@login_required
def contribute_goal(goal_id):
    user = current_user()
    goal = Goal.query.get(goal_id)
    if goal and goal.user_id == user.id:
        amount = float(request.form['amount'])
        goal.saved += amount
        if goal.saved >= goal.target:
            goal.completed = True
        db.session.commit()
    return redirect('/goals')

# ================= BUDGET =================
@app.route('/budget')
@login_required
def budget():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    budgets = Budget.query.filter_by(user_id=user.id).all()
    return render_template('budget.html', user=user, expenses=expenses, budgets=budgets)

@app.route('/add_budget', methods=['POST'])
@login_required
def add_budget():
    user = current_user()
    b = Budget(
        user_id=user.id,
        name=request.form['name'],
        limit=float(request.form['limit']),
        color=request.form.get('color', '#a855f7')
    )
    db.session.add(b)
    db.session.commit()
    return redirect('/budget')

# ================= ANALYTICS / SUMMARY =================
@app.route('/summary')
@login_required
def summary():
    user = current_user()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    labels = [e.title for e in expenses]
    values = [e.amount for e in expenses]
    return render_template('analytics.html', user=user, labels=labels, values=values, expenses=expenses)

# ================= SETTINGS =================
@app.route('/settings', methods=['GET'])
@login_required
def settings():
    user = current_user()
    return render_template('settings.html', user=user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = current_user()
    new_email = request.form.get('email')
    if new_email:
        user.email = new_email
    db.session.commit()
    return redirect('/settings')

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    user = current_user()
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')
    if check_password_hash(user.password, current_pw) and new_pw == confirm_pw:
        user.password = generate_password_hash(new_pw)
        db.session.commit()
    return redirect('/settings')

@app.route('/clear_expenses')
@login_required
def clear_expenses():
    user = current_user()
    Expense.query.filter_by(user_id=user.id).delete()
    user.balance = 35000
    db.session.commit()
    return redirect('/dashboard')

@app.route('/reset_balance')
@login_required
def reset_balance():
    user = current_user()
    user.balance = 35000
    db.session.commit()
    return redirect('/dashboard')

@app.route('/delete_account')
@login_required
def delete_account():
    user = current_user()
    Expense.query.filter_by(user_id=user.id).delete()
    Goal.query.filter_by(user_id=user.id).delete()
    Budget.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    session.pop('user_id', None)
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
   with app.app_context():
    db.create_all()
    app.run(debug=True)
