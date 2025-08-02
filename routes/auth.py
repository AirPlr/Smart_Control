from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User, db
from datetime import datetime

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        language = request.form.get('language', 'it')
        license_code = request.form.get('license_code', '')
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username o email già esistenti')
            return redirect(url_for('auth.register'))
            
        user = User(username=username, email=email, language=language, license_code=license_code)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        
        return redirect(url_for('main.onboarding'))
        
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Aggiorna ultimo login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect basato sul ruolo
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_dealer():
                return redirect(url_for('dealer.dashboard'))
            else:
                return redirect(url_for('main.index'))
                
        flash('Credenziali non valide')
        
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
