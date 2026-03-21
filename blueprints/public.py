# ============================================================================
# FILE: blueprints/public.py
# ============================================================================
from flask import Blueprint, render_template, request, jsonify, current_app
from models import Project, WorkExperience, ContactMessage, PROJECT_CATEGORIES
from app import db

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    featured_projects = Project.query.filter_by(
        is_visible=True,
        is_featured=True
    ).order_by(Project.display_order).limit(6).all()

    recent_experiences = WorkExperience.query.filter_by(
        is_visible=True
    ).order_by(WorkExperience.start_date.desc()).limit(3).all()

    return render_template('home.html',
                           featured_projects=featured_projects,
                           recent_experiences=recent_experiences)


@public_bp.route('/projects')
def projects():
    category = request.args.get('category')
    query = Project.query.filter_by(is_visible=True)

    if category and category in PROJECT_CATEGORIES:
        query = query.filter_by(category=category)

    projects = query.order_by(Project.display_order, Project.created_at.desc()).all()

    projects_by_category = {}
    for project in projects:
        if project.category not in projects_by_category:
            projects_by_category[project.category] = []
        projects_by_category[project.category].append(project)

    return render_template('projects.html',
                           projects_by_category=projects_by_category,
                           categories=PROJECT_CATEGORIES,
                           selected_category=category)


@public_bp.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.filter_by(id=project_id, is_visible=True).first_or_404()

    related_projects = Project.query.filter(
        Project.category == project.category,
        Project.id != project.id,
        Project.is_visible == True
    ).order_by(Project.display_order).limit(3).all()

    return render_template('project_detail.html',
                           project=project,
                           related_projects=related_projects)


@public_bp.route('/work')
def work():
    experiences = WorkExperience.query.filter_by(
        is_visible=True
    ).order_by(WorkExperience.display_order, WorkExperience.start_date.desc()).all()

    return render_template('work.html', experiences=experiences)


@public_bp.route('/about')
def about():
    return render_template('about.html')


@public_bp.route('/contact')
def contact():
    return render_template('contact.html')


@public_bp.route('/contact/send', methods=['POST'])
def contact_send():
    """Handle contact form submission — saves message to the database."""
    name    = request.form.get('name', '').strip()
    email   = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()

    # Basic validation
    errors = []
    if not name:
        errors.append('Name is required.')
    if not email or '@' not in email:
        errors.append('A valid email address is required.')
    if not subject:
        errors.append('Subject is required.')
    if not message:
        errors.append('Message is required.')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 422

    try:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

        contact_msg = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message,
            ip_address=ip_address
        )
        db.session.add(contact_msg)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Your message has been received. I\'ll get back to you soon!'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving contact message: {e}")
        return jsonify({'success': False, 'errors': ['Something went wrong. Please try again later.']}), 500