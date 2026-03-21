# ============================================================================
# FILE: blueprints/auth.py
# ============================================================================
from datetime import datetime
from flask import Blueprint, redirect, url_for, session, flash, current_app
from app import db, oauth
from models import Admin

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('admin.dashboard'))
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/callback')
def callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user information from Google.', 'danger')
            return redirect(url_for('public.index'))

        if user_info['email'] != current_app.config['ADMIN_EMAIL']:
            flash('You are not authorized to access the admin panel.', 'danger')
            return redirect(url_for('public.index'))

        session['user'] = {
            'email': user_info['email'],
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }
        session.permanent = True

        admin = Admin.query.filter_by(email=user_info['email']).first()
        if not admin:
            admin = Admin(
                email=user_info['email'],
                name=user_info.get('name'),
                picture=user_info.get('picture')
            )
            db.session.add(admin)
        else:
            admin.name = user_info.get('name')
            admin.picture = user_info.get('picture')

        admin.last_login = datetime.utcnow()
        db.session.commit()

        flash(f'Welcome, {user_info.get("name")}!', 'success')
        return redirect(url_for('admin.dashboard'))

    except Exception as e:
        current_app.logger.error(f"Authentication error: {e}")
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('public.index'))


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('public.index'))


