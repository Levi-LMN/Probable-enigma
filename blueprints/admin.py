# blueprints/admin.py - Complete Admin Blueprint
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import func

from app import db
from models import (Project, ProjectTechnology, ProjectImage, WorkExperience,
                    PageVisit, DailyStats, ContactMessage, PROJECT_CATEGORIES, TECHNOLOGIES, Admin)

admin_bp = Blueprint('admin', __name__)


# ============================================================================
# DECORATORS
# ============================================================================

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('auth.login'))

        admin = Admin.query.filter_by(email=session['user']['email']).first()
        if not admin:
            flash('You do not have admin privileges.', 'danger')
            session.pop('user', None)
            return redirect(url_for('public.index'))

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file, subfolder=''):
    """Save an uploaded file and return the relative path"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        random_filename = f"{secrets.token_hex(16)}{file_ext}"

        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)

        file_path = os.path.join(upload_path, random_filename)
        file.save(file_path)

        return os.path.join('uploads', subfolder, random_filename).replace('\\', '/')
    return None


def delete_file(filepath):
    """Delete a file from the filesystem"""
    if filepath:
        full_path = os.path.join('static', filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                current_app.logger.error(f"Error deleting file {full_path}: {e}")


# ============================================================================
# DASHBOARD & ANALYTICS
# ============================================================================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard"""
    projects = Project.query.order_by(Project.display_order, Project.created_at.desc()).all()
    experiences = WorkExperience.query.order_by(
        WorkExperience.display_order,
        WorkExperience.start_date.desc()
    ).all()

    # Get quick stats
    total_visits = DailyStats.get_total_visits()
    total_unique = DailyStats.get_total_unique_visitors()

    # Get today's stats
    from datetime import date
    today_stats = DailyStats.query.filter_by(date=date.today()).first()
    today_visits = today_stats.total_visits if today_stats else 0

    unread_messages = ContactMessage.get_unread_count()

    return render_template('admin/dashboard.html',
                           projects=projects,
                           experiences=experiences,
                           total_visits=total_visits,
                           total_unique=total_unique,
                           today_visits=today_visits,
                           unread_messages=unread_messages)


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Detailed analytics page"""
    days = int(request.args.get('days', 30))

    # Daily stats
    daily_stats = DailyStats.get_recent_stats(days=days)

    # Page visit stats
    page_stats = PageVisit.get_page_stats(days=days, limit=20)

    # Referrer stats
    referrer_stats = PageVisit.get_referrer_stats(days=days, limit=10)

    # Total stats
    total_visits = DailyStats.get_total_visits()
    total_unique = DailyStats.get_total_unique_visitors()

    # Calculate trends (last 7 days vs previous 7 days)
    from datetime import date, timedelta
    today = date.today()
    last_7_days = DailyStats.query.filter(
        DailyStats.date >= today - timedelta(days=7)
    ).all()
    prev_7_days = DailyStats.query.filter(
        DailyStats.date >= today - timedelta(days=14),
        DailyStats.date < today - timedelta(days=7)
    ).all()

    last_7_total = sum(s.total_visits for s in last_7_days)
    prev_7_total = sum(s.total_visits for s in prev_7_days)

    trend_percent = 0
    if prev_7_total > 0:
        trend_percent = ((last_7_total - prev_7_total) / prev_7_total) * 100

    return render_template('admin/analytics.html',
                           daily_stats=daily_stats,
                           page_stats=page_stats,
                           referrer_stats=referrer_stats,
                           total_visits=total_visits,
                           total_unique=total_unique,
                           days=days,
                           trend_percent=trend_percent)


@admin_bp.route('/analytics/clear', methods=['POST'])
@admin_required
def clear_analytics():
    """Clear all analytics data"""
    try:
        PageVisit.query.delete()
        DailyStats.query.delete()
        db.session.commit()

        flash('Analytics data cleared successfully!', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/analytics/clear-old', methods=['POST'])
@admin_required
def clear_old_analytics():
    """Clear analytics data older than specified days"""
    try:
        days = int(request.form.get('days', 90))
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        deleted_visits = PageVisit.query.filter(
            PageVisit.visited_at < cutoff_date
        ).delete()

        deleted_stats = DailyStats.query.filter(
            DailyStats.date < cutoff_date.date()
        ).delete()

        db.session.commit()

        flash(f'Deleted {deleted_visits} page visits and {deleted_stats} daily stats older than {days} days.',
              'success')
        return jsonify({'success': True, 'deleted_visits': deleted_visits, 'deleted_stats': deleted_stats})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing old analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CONTACT MESSAGES
# ============================================================================

@admin_bp.route('/messages')
@admin_required
def messages():
    """View all contact messages"""
    filter_read = request.args.get('filter', 'all')  # all | unread | read

    query = ContactMessage.query
    if filter_read == 'unread':
        query = query.filter_by(is_read=False)
    elif filter_read == 'read':
        query = query.filter_by(is_read=True)

    msgs = query.order_by(ContactMessage.created_at.desc()).all()
    unread_count = ContactMessage.get_unread_count()

    return render_template('admin/messages.html',
                           messages=msgs,
                           unread_count=unread_count,
                           filter_read=filter_read)


@admin_bp.route('/messages/<int:message_id>')
@admin_required
def message_detail(message_id):
    """View a single contact message and mark it as read"""
    msg = ContactMessage.query.get_or_404(message_id)

    if not msg.is_read:
        msg.mark_read()
        db.session.commit()

    return render_template('admin/message_detail.html', message=msg)


@admin_bp.route('/messages/<int:message_id>/toggle-read', methods=['POST'])
@admin_required
def toggle_message_read(message_id):
    """Toggle read/unread status via AJAX"""
    msg = ContactMessage.query.get_or_404(message_id)
    try:
        msg.is_read = not msg.is_read
        db.session.commit()
        return jsonify({'success': True, 'is_read': msg.is_read})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/messages/<int:message_id>/delete', methods=['POST'])
@admin_required
def delete_message(message_id):
    """Delete a contact message"""
    msg = ContactMessage.query.get_or_404(message_id)
    try:
        db.session.delete(msg)
        db.session.commit()
        flash('Message deleted.', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

@admin_bp.route('/project/add', methods=['GET', 'POST'])
@admin_required
def add_project():
    """Add new project"""
    if request.method == 'POST':
        try:
            project = Project(
                name=request.form['name'],
                description=request.form['description'],
                category=request.form['category'],
                github_link=request.form.get('github_link'),
                preview_link=request.form.get('preview_link'),
                display_order=int(request.form.get('display_order', 0)),
                is_visible=request.form.get('is_visible') == 'on',
                is_featured=request.form.get('is_featured') == 'on'
            )

            if request.form.get('date_started'):
                project.date_started = datetime.strptime(
                    request.form['date_started'], '%Y-%m-%d'
                ).date()

            if request.form.get('date_completed'):
                project.date_completed = datetime.strptime(
                    request.form['date_completed'], '%Y-%m-%d'
                ).date()

            # Technologies
            technologies = request.form.getlist('technologies')
            for tech in technologies:
                project.technologies.append(ProjectTechnology(technology=tech))

            # Images
            images = request.files.getlist('images')
            captions = request.form.getlist('captions')
            for i, file in enumerate(images):
                if file and file.filename:
                    filepath = save_uploaded_file(file, 'projects')
                    if filepath:
                        caption = captions[i] if i < len(captions) else ''
                        project.images.append(ProjectImage(
                            filename=filepath,
                            caption=caption,
                            display_order=i
                        ))

            db.session.add(project)
            db.session.commit()

            flash('Project added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding project: {e}")
            flash(f'Error adding project: {str(e)}', 'danger')

    return render_template('admin/project_form.html',
                           project=None,
                           categories=PROJECT_CATEGORIES,
                           technologies=TECHNOLOGIES)


@admin_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_project(project_id):
    """Edit an existing project"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        try:
            project.name = request.form['name']
            project.description = request.form['description']
            project.category = request.form['category']
            project.github_link = request.form.get('github_link')
            project.preview_link = request.form.get('preview_link')
            project.display_order = int(request.form.get('display_order', 0))
            project.is_visible = request.form.get('is_visible') == 'on'
            project.is_featured = request.form.get('is_featured') == 'on'

            if request.form.get('date_started'):
                project.date_started = datetime.strptime(
                    request.form['date_started'], '%Y-%m-%d'
                ).date()
            else:
                project.date_started = None

            if request.form.get('date_completed'):
                project.date_completed = datetime.strptime(
                    request.form['date_completed'], '%Y-%m-%d'
                ).date()
            else:
                project.date_completed = None

            # Update technologies
            ProjectTechnology.query.filter_by(project_id=project.id).delete()
            technologies = request.form.getlist('technologies')
            for tech in technologies:
                project.technologies.append(ProjectTechnology(technology=tech))

            # Handle image deletions
            delete_image_ids = request.form.getlist('delete_images')
            for image_id in delete_image_ids:
                image = ProjectImage.query.get(int(image_id))
                if image and image.project_id == project.id:
                    delete_file(image.filename)
                    db.session.delete(image)

            # Add new images
            new_images = request.files.getlist('new_images')
            new_captions = request.form.getlist('new_captions')
            current_max_order = max(
                (img.display_order for img in project.images), default=-1
            )
            for i, file in enumerate(new_images):
                if file and file.filename:
                    filepath = save_uploaded_file(file, 'projects')
                    if filepath:
                        caption = new_captions[i] if i < len(new_captions) else ''
                        project.images.append(ProjectImage(
                            filename=filepath,
                            caption=caption,
                            display_order=current_max_order + i + 1
                        ))

            db.session.commit()
            flash('Project updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating project: {e}")
            flash(f'Error updating project: {str(e)}', 'danger')

    return render_template('admin/project_form.html',
                           project=project,
                           categories=PROJECT_CATEGORIES,
                           technologies=TECHNOLOGIES)


@admin_bp.route('/project/<int:project_id>/delete', methods=['POST'])
@admin_required
def delete_project(project_id):
    """Delete a project"""
    project = Project.query.get_or_404(project_id)

    try:
        for image in project.images:
            delete_file(image.filename)

        db.session.delete(project)
        db.session.commit()

        flash('Project deleted successfully!', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/project/<int:project_id>/toggle-visibility', methods=['POST'])
@admin_required
def toggle_project_visibility(project_id):
    """Toggle project visibility"""
    project = Project.query.get_or_404(project_id)

    try:
        project.is_visible = not project.is_visible
        db.session.commit()

        return jsonify({
            'success': True,
            'is_visible': project.is_visible
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# WORK EXPERIENCE MANAGEMENT
# ============================================================================

@admin_bp.route('/experience/add', methods=['GET', 'POST'])
@admin_required
def add_experience():
    """Add new work experience"""
    if request.method == 'POST':
        try:
            experience = WorkExperience(
                company_name=request.form['company_name'],
                position=request.form['position'],
                description=request.form['description'],
                location=request.form.get('location'),
                technologies=request.form.get('technologies'),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                is_current=request.form.get('is_current') == 'on',
                display_order=int(request.form.get('display_order', 0)),
                is_visible=request.form.get('is_visible') == 'on'
            )

            if request.form.get('end_date') and not experience.is_current:
                experience.end_date = datetime.strptime(
                    request.form['end_date'], '%Y-%m-%d'
                ).date()

            if 'company_logo' in request.files:
                file = request.files['company_logo']
                filepath = save_uploaded_file(file, 'experience')
                if filepath:
                    experience.company_logo = filepath

            db.session.add(experience)
            db.session.commit()

            flash('Work experience added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding experience: {e}")
            flash(f'Error adding experience: {str(e)}', 'danger')

    return render_template('admin/experience_form.html', experience=None)


@admin_bp.route('/experience/<int:experience_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_experience(experience_id):
    """Edit work experience"""
    experience = WorkExperience.query.get_or_404(experience_id)

    if request.method == 'POST':
        try:
            experience.company_name = request.form['company_name']
            experience.position = request.form['position']
            experience.description = request.form['description']
            experience.location = request.form.get('location')
            experience.technologies = request.form.get('technologies')
            experience.start_date = datetime.strptime(
                request.form['start_date'], '%Y-%m-%d'
            ).date()
            experience.is_current = request.form.get('is_current') == 'on'
            experience.display_order = int(request.form.get('display_order', 0))
            experience.is_visible = request.form.get('is_visible') == 'on'

            if request.form.get('end_date') and not experience.is_current:
                experience.end_date = datetime.strptime(
                    request.form['end_date'], '%Y-%m-%d'
                ).date()
            else:
                experience.end_date = None

            if 'company_logo' in request.files:
                file = request.files['company_logo']
                if file and file.filename:
                    if experience.company_logo:
                        delete_file(experience.company_logo)
                    filepath = save_uploaded_file(file, 'experience')
                    if filepath:
                        experience.company_logo = filepath

            db.session.commit()
            flash('Work experience updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating experience: {e}")
            flash(f'Error updating experience: {str(e)}', 'danger')

    return render_template('admin/experience_form.html', experience=experience)


@admin_bp.route('/experience/<int:experience_id>/delete', methods=['POST'])
@admin_required
def delete_experience(experience_id):
    """Delete work experience"""
    experience = WorkExperience.query.get_or_404(experience_id)

    try:
        if experience.company_logo:
            delete_file(experience.company_logo)

        db.session.delete(experience)
        db.session.commit()

        flash('Work experience deleted successfully!', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting experience: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/experience/<int:experience_id>/toggle-visibility', methods=['POST'])
@admin_required
def toggle_experience_visibility(experience_id):
    """Toggle experience visibility"""
    experience = WorkExperience.query.get_or_404(experience_id)

    try:
        experience.is_visible = not experience.is_visible
        db.session.commit()

        return jsonify({
            'success': True,
            'is_visible': experience.is_visible
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API HELPERS
# ============================================================================

@admin_bp.route('/api/technologies/<category>')
def get_technologies(category):
    """Get technologies for a category (AJAX)"""
    return jsonify(TECHNOLOGIES.get(category, []))