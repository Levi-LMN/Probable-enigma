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


# ============================================================================
# BACKUP & IMPORT
# ============================================================================

@admin_bp.route('/export-json')
@admin_required
def export_json():
    """Download all projects and experiences as a single JSON file."""
    import json
    from flask import Response

    projects_data = []
    for p in Project.query.order_by(Project.display_order, Project.created_at).all():
        projects_data.append({
            'id':             p.id,
            'name':           p.name,
            'description':    p.description,
            'category':       p.category,
            'technologies':   p.technologies_list,
            'github_link':    p.github_link,
            'preview_link':   p.preview_link,
            'date_started':   str(p.date_started)   if p.date_started   else None,
            'date_completed': str(p.date_completed) if p.date_completed else None,
            'display_order':  p.display_order,
            'is_visible':     p.is_visible,
            'is_featured':    p.is_featured,
            'images': [
                {
                    'filename':      img.filename,
                    'caption':       img.caption,
                    'display_order': img.display_order
                }
                for img in p.images
            ],
            'created_at':  p.created_at.isoformat()  if p.created_at  else None,
            'updated_at':  p.updated_at.isoformat()  if p.updated_at  else None,
        })

    experiences_data = []
    for e in WorkExperience.query.order_by(WorkExperience.display_order, WorkExperience.start_date.desc()).all():
        experiences_data.append({
            'id':           e.id,
            'company_name': e.company_name,
            'position':     e.position,
            'description':  e.description,
            'location':     e.location,
            'start_date':   str(e.start_date) if e.start_date else None,
            'end_date':     str(e.end_date)   if e.end_date   else None,
            'is_current':   e.is_current,
            'technologies': e.technologies,
            'display_order': e.display_order,
            'is_visible':   e.is_visible,
            'created_at':   e.created_at.isoformat() if e.created_at else None,
            'updated_at':   e.updated_at.isoformat() if e.updated_at else None,
        })

    payload = {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'projects':    projects_data,
        'experiences': experiences_data,
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename  = f'portfolio_data_{timestamp}.json'

    return Response(
        json.dumps(payload, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@admin_bp.route('/data-editor')
@admin_required
def data_editor():
    """JSON data editor page — export/import projects and experiences as separate JSON files for mass editing."""
    project_count = Project.query.count()
    experience_count = WorkExperience.query.count()
    return render_template('admin/data_editor.html',
                           project_count=project_count,
                           experience_count=experience_count)


@admin_bp.route('/data-editor/export/projects')
@admin_required
def export_projects_json():
    """Download all projects as a standalone JSON file (includes IDs for re-import)."""
    import json
    from flask import Response

    projects_data = []
    for p in Project.query.order_by(Project.display_order, Project.created_at).all():
        projects_data.append({
            'id':             p.id,
            'name':           p.name,
            'description':    p.description,
            'category':       p.category,
            'technologies':   p.technologies_list,
            'github_link':    p.github_link,
            'preview_link':   p.preview_link,
            'date_started':   str(p.date_started)   if p.date_started   else None,
            'date_completed': str(p.date_completed) if p.date_completed else None,
            'display_order':  p.display_order,
            'is_visible':     p.is_visible,
            'is_featured':    p.is_featured,
            'images': [
                {
                    'id':            img.id,
                    'filename':      img.filename,
                    'caption':       img.caption,
                    'display_order': img.display_order
                }
                for img in p.images
            ],
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        })

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        json.dumps(projects_data, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="projects_{timestamp}.json"'}
    )


@admin_bp.route('/data-editor/export/experiences')
@admin_required
def export_experiences_json():
    """Download all experiences as a standalone JSON file (includes IDs for re-import)."""
    import json
    from flask import Response

    experiences_data = []
    for e in WorkExperience.query.order_by(WorkExperience.display_order, WorkExperience.start_date.desc()).all():
        experiences_data.append({
            'id':            e.id,
            'company_name':  e.company_name,
            'position':      e.position,
            'description':   e.description,
            'location':      e.location,
            'start_date':    str(e.start_date) if e.start_date else None,
            'end_date':      str(e.end_date)   if e.end_date   else None,
            'is_current':    e.is_current,
            'technologies':  e.technologies,
            'company_logo':  e.company_logo,
            'display_order': e.display_order,
            'is_visible':    e.is_visible,
            'created_at':    e.created_at.isoformat() if e.created_at else None,
            'updated_at':    e.updated_at.isoformat() if e.updated_at else None,
        })

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        json.dumps(experiences_data, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="experiences_{timestamp}.json"'}
    )


@admin_bp.route('/data-editor/import/projects', methods=['POST'])
@admin_required
def import_projects_json():
    """
    Apply mass edits from an uploaded projects JSON file.
    Matches records by 'id'. Updates all editable fields; image captions/order
    can also be updated (but no new files are added — use the edit form for that).
    Records with no matching ID in the database are skipped.
    """
    import json

    if 'projects_file' not in request.files or not request.files['projects_file'].filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.data_editor'))

    f = request.files['projects_file']
    if not f.filename.lower().endswith('.json'):
        flash('Please upload a .json file.', 'danger')
        return redirect(url_for('admin.data_editor'))

    try:
        data = json.loads(f.read().decode('utf-8'))
        if not isinstance(data, list):
            flash('Invalid format: the JSON must be a list (array) of project objects.', 'danger')
            return redirect(url_for('admin.data_editor'))

        updated = created = skipped = 0
        warnings = []

        for item in data:
            try:
                project_id = item.get('id')
                is_new = not project_id  # no id / null id means create new

                if is_new:
                    # Require at minimum a name to create a record
                    name = str(item.get('name', '')).strip()
                    if not name:
                        warnings.append('Skipped a record with no "id" and no "name" — cannot create it.')
                        skipped += 1
                        continue
                    project = Project(
                        name=name,
                        description=str(item.get('description', '')),
                        category=str(item.get('category', 'Other')).strip(),
                        github_link=item.get('github_link') or None,
                        preview_link=item.get('preview_link') or None,
                        display_order=int(item.get('display_order', 0)),
                        is_visible=bool(item.get('is_visible', True)),
                        is_featured=bool(item.get('is_featured', False)),
                    )
                    try:
                        if item.get('date_started'):
                            project.date_started = datetime.strptime(item['date_started'], '%Y-%m-%d').date()
                        if item.get('date_completed'):
                            project.date_completed = datetime.strptime(item['date_completed'], '%Y-%m-%d').date()
                    except ValueError as ve:
                        warnings.append(f'New project "{name}": bad date value — {ve}. Dates left blank.')
                    for tech in item.get('technologies', []):
                        if tech and str(tech).strip():
                            project.technologies.append(ProjectTechnology(technology=str(tech).strip()))
                    db.session.add(project)
                    created += 1
                    continue  # images need uploaded files; skip for new records

                # ── Existing record: match by id and update ──────────────────
                project = Project.query.get(project_id)
                if not project:
                    # ID not found in DB — create a new record instead of skipping
                    name = str(item.get('name', '')).strip()
                    if not name:
                        warnings.append(f'Skipped id={project_id}: no matching record and no "name" to create one.')
                        skipped += 1
                        continue
                    project = Project(
                        name=name,
                        description=str(item.get('description', '')),
                        category=str(item.get('category', 'Other')).strip(),
                        github_link=item.get('github_link') or None,
                        preview_link=item.get('preview_link') or None,
                        display_order=int(item.get('display_order', 0)),
                        is_visible=bool(item.get('is_visible', True)),
                        is_featured=bool(item.get('is_featured', False)),
                    )
                    try:
                        if item.get('date_started'):
                            project.date_started = datetime.strptime(item['date_started'], '%Y-%m-%d').date()
                        if item.get('date_completed'):
                            project.date_completed = datetime.strptime(item['date_completed'], '%Y-%m-%d').date()
                    except ValueError as ve:
                        warnings.append(f'New project "{name}" (id={project_id}): bad date — {ve}. Dates left blank.')
                    for tech in item.get('technologies', []):
                        if tech and str(tech).strip():
                            project.technologies.append(ProjectTechnology(technology=str(tech).strip()))
                    db.session.add(project)
                    created += 1
                    continue  # no image files to process for newly created records

                if 'name' in item and item['name']:
                    project.name = str(item['name']).strip()
                if 'description' in item:
                    project.description = str(item['description'])
                if 'category' in item and item['category']:
                    project.category = str(item['category'])
                if 'github_link' in item:
                    project.github_link = item['github_link'] or None
                if 'preview_link' in item:
                    project.preview_link = item['preview_link'] or None
                if 'display_order' in item:
                    project.display_order = int(item['display_order'])
                if 'is_visible' in item:
                    project.is_visible = bool(item['is_visible'])
                if 'is_featured' in item:
                    project.is_featured = bool(item['is_featured'])
                if 'date_started' in item:
                    try:
                        project.date_started = datetime.strptime(item['date_started'], '%Y-%m-%d').date() if item['date_started'] else None
                    except ValueError:
                        warnings.append(f'id={project_id}: bad date_started value "{item["date_started"]}" — kept original.')
                if 'date_completed' in item:
                    try:
                        project.date_completed = datetime.strptime(item['date_completed'], '%Y-%m-%d').date() if item['date_completed'] else None
                    except ValueError:
                        warnings.append(f'id={project_id}: bad date_completed value "{item["date_completed"]}" — kept original.')

                if 'technologies' in item and isinstance(item['technologies'], list):
                    ProjectTechnology.query.filter_by(project_id=project.id).delete()
                    for tech in item['technologies']:
                        if tech and str(tech).strip():
                            project.technologies.append(ProjectTechnology(technology=str(tech).strip()))

                if 'images' in item and isinstance(item['images'], list):
                    for img_data in item['images']:
                        img_id = img_data.get('id')
                        if not img_id:
                            continue
                        img = ProjectImage.query.get(img_id)
                        if img and img.project_id == project.id:
                            if 'caption' in img_data:
                                img.caption = img_data['caption'] or ''
                            if 'display_order' in img_data:
                                img.display_order = int(img_data['display_order'])

                project.updated_at = datetime.utcnow()
                updated += 1

            except Exception as e:
                warnings.append(f'Error on id={item.get("id", "?")} ("{item.get("name", "?")}"): {e}')
                skipped += 1

        db.session.commit()

        parts = []
        if updated: parts.append(f'{updated} updated')
        if created: parts.append(f'{created} created')
        if skipped: parts.append(f'{skipped} skipped')
        msg = 'Projects: ' + ', '.join(parts) + '.' if parts else 'No changes made.'
        flash(msg, 'success' if not warnings else 'warning')
        for w in warnings[:6]:
            flash(w, 'warning')

    except json.JSONDecodeError as e:
        flash(f'Could not parse the JSON file: {e}', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'import_projects_json error: {e}')
        flash(f'Import failed: {e}', 'danger')

    return redirect(url_for('admin.data_editor'))


@admin_bp.route('/data-editor/import/experiences', methods=['POST'])
@admin_required
def import_experiences_json():
    """
    Apply mass edits from an uploaded experiences JSON file.
    Matches records by 'id'. Records with no matching ID are skipped.
    Company logos are file-based — use the edit form to change them.
    """
    import json

    if 'experiences_file' not in request.files or not request.files['experiences_file'].filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.data_editor'))

    f = request.files['experiences_file']
    if not f.filename.lower().endswith('.json'):
        flash('Please upload a .json file.', 'danger')
        return redirect(url_for('admin.data_editor'))

    try:
        data = json.loads(f.read().decode('utf-8'))
        if not isinstance(data, list):
            flash('Invalid format: the JSON must be a list (array) of experience objects.', 'danger')
            return redirect(url_for('admin.data_editor'))

        updated = created = skipped = 0
        warnings = []

        for item in data:
            try:
                exp_id = item.get('id')
                is_new = not exp_id

                if is_new:
                    # Require company_name, position, and start_date to create
                    company  = str(item.get('company_name', '')).strip()
                    position = str(item.get('position', '')).strip()
                    start_date_raw = item.get('start_date')
                    if not company or not position or not start_date_raw:
                        warnings.append(f'Skipped new record "{company or "?"}" — company_name, position, and start_date are all required to create.')
                        skipped += 1
                        continue
                    try:
                        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
                    except ValueError:
                        warnings.append(f'Skipped new record "{company}": bad start_date "{start_date_raw}".')
                        skipped += 1
                        continue
                    is_current = bool(item.get('is_current', False))
                    end_date = None
                    if not is_current and item.get('end_date'):
                        try:
                            end_date = datetime.strptime(item['end_date'], '%Y-%m-%d').date()
                        except ValueError:
                            warnings.append(f'New experience "{company}": bad end_date — left blank.')
                    exp = WorkExperience(
                        company_name=company,
                        position=position,
                        description=str(item.get('description', '')),
                        location=item.get('location') or None,
                        technologies=item.get('technologies') or None,
                        start_date=start_date,
                        end_date=end_date,
                        is_current=is_current,
                        display_order=int(item.get('display_order', 0)),
                        is_visible=bool(item.get('is_visible', True)),
                    )
                    db.session.add(exp)
                    created += 1
                    continue

                # ── Existing record: match by id and update ──────────────────
                exp = WorkExperience.query.get(exp_id)
                if not exp:
                    warnings.append(f'Skipped: no experience with id={exp_id} exists in the database.')
                    skipped += 1
                    continue

                if 'company_name' in item and item['company_name']:
                    exp.company_name = str(item['company_name']).strip()
                if 'position' in item and item['position']:
                    exp.position = str(item['position']).strip()
                if 'description' in item:
                    exp.description = str(item['description'])
                if 'location' in item:
                    exp.location = item['location'] or None
                if 'technologies' in item:
                    exp.technologies = item['technologies'] or None
                if 'is_current' in item:
                    exp.is_current = bool(item['is_current'])
                if 'display_order' in item:
                    exp.display_order = int(item['display_order'])
                if 'is_visible' in item:
                    exp.is_visible = bool(item['is_visible'])
                if 'start_date' in item:
                    try:
                        if item['start_date']:
                            exp.start_date = datetime.strptime(item['start_date'], '%Y-%m-%d').date()
                    except ValueError:
                        warnings.append(f'id={exp_id}: bad start_date "{item["start_date"]}" — kept original.')
                if 'end_date' in item:
                    try:
                        exp.end_date = datetime.strptime(item['end_date'], '%Y-%m-%d').date() if item['end_date'] else None
                    except ValueError:
                        warnings.append(f'id={exp_id}: bad end_date "{item["end_date"]}" — kept original.')

                exp.updated_at = datetime.utcnow()
                updated += 1

            except Exception as e:
                warnings.append(f'Error on id={item.get("id", "?")} ("{item.get("company_name", "?")}"): {e}')
                skipped += 1

        db.session.commit()

        parts = []
        if updated: parts.append(f'{updated} updated')
        if created: parts.append(f'{created} created')
        if skipped: parts.append(f'{skipped} skipped')
        msg = 'Experiences: ' + ', '.join(parts) + '.' if parts else 'No changes made.'
        flash(msg, 'success' if not warnings else 'warning')
        for w in warnings[:6]:
            flash(w, 'warning')

    except json.JSONDecodeError as e:
        flash(f'Could not parse the JSON file: {e}', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'import_experiences_json error: {e}')
        flash(f'Import failed: {e}', 'danger')

    return redirect(url_for('admin.data_editor'))


@admin_bp.route('/backup')
@admin_required
def download_backup():
    """Download a full ZIP backup of all data and images."""
    import zipfile, io, json
    from flask import send_file

    projects_data = []
    for p in Project.query.all():
        projects_data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'github_link': p.github_link,
            'preview_link': p.preview_link,
            'date_started': str(p.date_started) if p.date_started else None,
            'date_completed': str(p.date_completed) if p.date_completed else None,
            'category': p.category,
            'display_order': p.display_order,
            'is_visible': p.is_visible,
            'is_featured': p.is_featured,
            'technologies': p.technologies_list,
            'images': [
                {'filename': img.filename, 'caption': img.caption, 'display_order': img.display_order}
                for img in p.images
            ]
        })

    experiences_data = []
    for e in WorkExperience.query.all():
        experiences_data.append({
            'id': e.id,
            'company_name': e.company_name,
            'position': e.position,
            'description': e.description,
            'location': e.location,
            'start_date': str(e.start_date) if e.start_date else None,
            'end_date': str(e.end_date) if e.end_date else None,
            'is_current': e.is_current,
            'technologies': e.technologies,
            'company_logo': e.company_logo,
            'display_order': e.display_order,
            'is_visible': e.is_visible
        })

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('data/projects.json', json.dumps(projects_data, indent=2))
        zf.writestr('data/experiences.json', json.dumps(experiences_data, indent=2))

        upload_folder = os.path.join('static', current_app.config['UPLOAD_FOLDER'])
        if not os.path.isabs(upload_folder):
            upload_folder = current_app.config['UPLOAD_FOLDER']
        # Walk the whole uploads tree
        base = os.path.join('static', 'uploads')
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, 'static')  # e.g. uploads/projects/abc.jpg
                    zf.write(fpath, f'images/{arcname}')

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'portfolio_backup_{timestamp}.zip'
    )


@admin_bp.route('/import', methods=['GET', 'POST'])
@admin_required
def import_backup():
    """Import data from an old or new system backup ZIP."""
    import zipfile, io, json
    from datetime import date as date_type

    if request.method == 'GET':
        return render_template('admin/import.html')

    # ── POST: process the uploaded ZIP ──────────────────────────────────────
    if 'backup_file' not in request.files or not request.files['backup_file'].filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.import_backup'))

    zip_file = request.files['backup_file']
    if not zip_file.filename.endswith('.zip'):
        flash('Please upload a .zip file.', 'danger')
        return redirect(url_for('admin.import_backup'))

    skip_existing = request.form.get('skip_existing') == 'on'

    try:
        zip_bytes = io.BytesIO(zip_file.read())

        with zipfile.ZipFile(zip_bytes, 'r') as zf:
            namelist = zf.namelist()

            # ── Helper: parse a date string safely ──────────────────────────
            def parse_date(val):
                if not val:
                    return None
                try:
                    return datetime.strptime(val, '%Y-%m-%d').date()
                except Exception:
                    return None

            # ── Helper: copy an image from the ZIP to the filesystem ─────────
            def extract_image(zip_filename_in_archive, dest_subfolder):
                """
                zip_filename_in_archive: path inside the zip  e.g. 'images/abc.jpg'
                dest_subfolder: 'projects' or 'experience'
                Returns the new relative path stored in DB, e.g. 'uploads/projects/abc.jpg'
                """
                if not zip_filename_in_archive or zip_filename_in_archive not in namelist:
                    return None
                try:
                    basename = os.path.basename(zip_filename_in_archive)
                    dest_dir = os.path.join('static', 'uploads', dest_subfolder)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, basename)
                    with zf.open(zip_filename_in_archive) as src, open(dest_path, 'wb') as dst:
                        dst.write(src.read())
                    return f'uploads/{dest_subfolder}/{basename}'
                except Exception as e:
                    current_app.logger.warning(f"Could not extract image {zip_filename_in_archive}: {e}")
                    return None

            # ── Detect which backup format the ZIP contains ──────────────────
            # New system stores 'data/projects.json' with key 'name'
            # Old system stores 'data/projects.json' with key 'ProjectName'
            # Images in new backups: 'images/uploads/projects/...'
            # Images in old backups: 'images/abc.jpg'

            def read_json(path):
                if path in namelist:
                    return json.loads(zf.read(path).decode('utf-8'))
                return None

            raw_projects = read_json('data/projects.json') or []
            raw_experiences = read_json('data/experiences.json') or []

            # Detect format by checking first project record
            is_old_format = (
                raw_projects and 'ProjectName' in raw_projects[0]
            ) or (
                raw_experiences and 'CompanyName' in raw_experiences[0]
            )

            # ── Normalise records to new-system field names ──────────────────
            def normalise_project(p):
                if is_old_format:
                    return {
                        'name':          p.get('ProjectName', ''),
                        'description':   p.get('Description', ''),
                        'github_link':   p.get('GitHubLink'),
                        'preview_link':  p.get('PreviewLink'),
                        'date_started':  p.get('DateStarted'),
                        'date_completed':p.get('DateCompleted'),
                        'category':      p.get('Category', 'Other'),
                        'display_order': 0,
                        'is_visible':    True,
                        'is_featured':   False,
                        'technologies':  p.get('Technologies', []),
                        # Old screenshots list: [{filename:'screenshots/abc.jpg', caption:'', order:0}]
                        'images': [
                            {
                                'filename':      f"images/{os.path.basename(s.get('filename', ''))}",
                                'caption':       s.get('caption', ''),
                                'display_order': s.get('order', i)
                            }
                            for i, s in enumerate(p.get('Screenshots', []))
                        ]
                    }
                else:
                    imgs = []
                    for img in p.get('images', []):
                        fn = img.get('filename', '')  # e.g. 'uploads/projects/abc.jpg'
                        imgs.append({
                            'filename':      f"images/{fn}",
                            'caption':       img.get('caption', ''),
                            'display_order': img.get('display_order', 0)
                        })
                    return {
                        'name':          p.get('name', ''),
                        'description':   p.get('description', ''),
                        'github_link':   p.get('github_link'),
                        'preview_link':  p.get('preview_link'),
                        'date_started':  p.get('date_started'),
                        'date_completed':p.get('date_completed'),
                        'category':      p.get('category', 'Other'),
                        'display_order': p.get('display_order', 0),
                        'is_visible':    p.get('is_visible', True),
                        'is_featured':   p.get('is_featured', False),
                        'technologies':  p.get('technologies', []),
                        'images':        imgs
                    }

            def normalise_experience(e):
                if is_old_format:
                    logo = e.get('CompanyLogo')
                    logo_in_zip = f"images/{os.path.basename(logo)}" if logo else None
                    return {
                        'company_name':  e.get('CompanyName', ''),
                        'position':      e.get('Position', ''),
                        'description':   e.get('Description', ''),
                        'location':      e.get('Location'),
                        'start_date':    e.get('StartDate'),
                        'end_date':      e.get('EndDate'),
                        'is_current':    e.get('IsCurrentJob', False),
                        'technologies':  e.get('Technologies'),
                        'company_logo_in_zip': logo_in_zip,
                        'display_order': 0,
                        'is_visible':    True
                    }
                else:
                    logo = e.get('company_logo')
                    logo_in_zip = f"images/{logo}" if logo else None
                    return {
                        'company_name':  e.get('company_name', ''),
                        'position':      e.get('position', ''),
                        'description':   e.get('description', ''),
                        'location':      e.get('location'),
                        'start_date':    e.get('start_date'),
                        'end_date':      e.get('end_date'),
                        'is_current':    e.get('is_current', False),
                        'technologies':  e.get('technologies'),
                        'company_logo_in_zip': logo_in_zip,
                        'display_order': e.get('display_order', 0),
                        'is_visible':    e.get('is_visible', True)
                    }

            # ── Import projects ──────────────────────────────────────────────
            imported_projects = 0
            skipped_projects = 0

            for raw in raw_projects:
                p = normalise_project(raw)

                if not p['name']:
                    continue

                if skip_existing and Project.query.filter_by(name=p['name']).first():
                    skipped_projects += 1
                    continue

                project = Project(
                    name=p['name'],
                    description=p['description'] or '',
                    github_link=p['github_link'],
                    preview_link=p['preview_link'],
                    date_started=parse_date(p['date_started']),
                    date_completed=parse_date(p['date_completed']),
                    category=p['category'],
                    display_order=p['display_order'],
                    is_visible=p['is_visible'],
                    is_featured=p['is_featured']
                )

                for tech in p['technologies']:
                    if tech:
                        project.technologies.append(ProjectTechnology(technology=tech))

                for img_data in p['images']:
                    new_path = extract_image(img_data['filename'], 'projects')
                    if new_path:
                        project.images.append(ProjectImage(
                            filename=new_path,
                            caption=img_data['caption'],
                            display_order=img_data['display_order']
                        ))

                db.session.add(project)
                imported_projects += 1

            # ── Import work experiences ──────────────────────────────────────
            imported_experiences = 0
            skipped_experiences = 0

            for raw in raw_experiences:
                e = normalise_experience(raw)

                if not e['company_name'] or not e['start_date']:
                    continue

                if skip_existing and WorkExperience.query.filter_by(
                    company_name=e['company_name'],
                    position=e['position']
                ).first():
                    skipped_experiences += 1
                    continue

                logo_path = extract_image(e['company_logo_in_zip'], 'experience')

                exp = WorkExperience(
                    company_name=e['company_name'],
                    position=e['position'],
                    description=e['description'] or '',
                    location=e['location'],
                    start_date=parse_date(e['start_date']),
                    end_date=parse_date(e['end_date']),
                    is_current=e['is_current'],
                    technologies=e['technologies'],
                    company_logo=logo_path,
                    display_order=e['display_order'],
                    is_visible=e['is_visible']
                )
                db.session.add(exp)
                imported_experiences += 1

            db.session.commit()

        fmt_label = 'old system' if is_old_format else 'new system'
        parts = []
        if imported_projects:
            parts.append(f'{imported_projects} project(s)')
        if imported_experiences:
            parts.append(f'{imported_experiences} experience(s)')
        skipped_total = skipped_projects + skipped_experiences

        if parts:
            msg = f'Successfully imported {" and ".join(parts)} from {fmt_label} backup.'
            if skipped_total:
                msg += f' Skipped {skipped_total} duplicate(s).'
            flash(msg, 'success')
        else:
            flash(f'Nothing imported — no new records found in {fmt_label} backup.', 'warning')

        return redirect(url_for('admin.dashboard'))

    except zipfile.BadZipFile:
        flash('The uploaded file is not a valid ZIP archive.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Import error: {e}")
        flash(f'Import failed: {str(e)}', 'danger')

    return redirect(url_for('admin.import_backup'))