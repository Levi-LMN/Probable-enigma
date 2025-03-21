from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import flash
import secrets
import os
from werkzeug.utils import secure_filename
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'huqweitfiqv676%^$ ^%E% E@F#EIJ%REIQ&^REC I&'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/screenshots'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in as admin first.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


# Constants for categories and technologies
PROJECT_CATEGORIES = [
    'Web Development',
    'Mobile Development',
    'Penetration Testing',
    'Low-Code Development',
    'Open Source Contributions'
]

TECHNOLOGIES = {
    'Web Development': [
        'Flask', 'Django', 'ASP.NET MVC', 'Spring Boot', 'PHP',
        'HTML5', 'CSS3', 'JavaScript', 'TypeScript',
        'React', 'Angular', 'Vue.js',
        'SQL Server', 'MySQL', 'PostgreSQL', 'MongoDB',
        'Bootstrap', 'Tailwind CSS', 'jQuery'
    ],
    'Mobile Development': [
        'Java', 'Kotlin', 'Android SDK',
        'React Native', 'Flutter',
        'Firebase', 'SQLite'
    ],
    'Penetration Testing': [
        'Burp Suite', 'Metasploit', 'Wireshark',
        'Nmap', 'Python', 'Bash',
        'OWASP ZAP', 'Kali Linux'
    ],
    'Low-Code Development': [
        'Power Apps', 'Power Automate', 'Power BI',
        'SharePoint', 'Microsoft 365',
        'Power Platform Connectors'
    ],
    'Open Source Contributions': [
        'Git', 'GitHub', 'GitLab',
        'Documentation', 'Code Review',
        'Unit Testing', 'CI/CD'
    ]
}


# Add these new models and update existing Project model

class ProjectScreenshot(db.Model):
    __tablename__ = 'project_screenshots'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.ProjectID'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)  # For controlling display order

    project = db.relationship('Project', back_populates='screenshots')


class ProjectTechnology(db.Model):
    __tablename__ = 'project_technologies'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.ProjectID'), nullable=False)
    technology = db.Column(db.String(100), nullable=False)

    project = db.relationship('Project', back_populates='technologies')


# Update the Project model
class Project(db.Model):
    __tablename__ = 'projects'

    ProjectID = db.Column(db.Integer, primary_key=True)
    ProjectName = db.Column(db.String(255), nullable=False)
    Description = db.Column(db.Text, nullable=False)
    GitHubLink = db.Column(db.String(255))
    PreviewLink = db.Column(db.String(255))
    DateStarted = db.Column(db.Date)
    DateCompleted = db.Column(db.Date)
    Category = db.Column(db.String(100))

    # Remove the old LanguagesUsed and Screenshot columns
    # Add relationships for technologies and screenshots
    technologies = db.relationship('ProjectTechnology', back_populates='project', cascade='all, delete-orphan')
    screenshots = db.relationship('ProjectScreenshot', back_populates='project', cascade='all, delete-orphan',
                                  order_by='ProjectScreenshot.order')

    @property
    def technologies_list(self):
        return [tech.technology for tech in self.technologies]

    @staticmethod
    def get_categories():
        return PROJECT_CATEGORIES

    @staticmethod
    def get_technologies(category=None):
        if category:
            return TECHNOLOGIES.get(category, [])
        return [tech for techs in TECHNOLOGIES.values() for tech in techs]

class WorkExperience(db.Model):
    __tablename__ = 'work_experience'

    ExperienceID = db.Column(db.Integer, primary_key=True)
    CompanyName = db.Column(db.String(255), nullable=False)
    Position = db.Column(db.String(255), nullable=False)
    Description = db.Column(db.Text, nullable=False)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date)
    Technologies = db.Column(db.String(255))
    CompanyLogo = db.Column(db.String(255))
    Location = db.Column(db.String(255))
    IsCurrentJob = db.Column(db.Boolean, default=False)


# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials!', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    projects = Project.query.all()
    experiences = WorkExperience.query.all()
    return render_template('admin/dashboard.html', projects=projects, experiences=experiences)


@app.route('/admin/add_work', methods=['GET', 'POST'])
@admin_required
def add_work_experience():
    if request.method == 'POST':
        company_name = request.form['company_name']
        position = request.form['position']
        description = request.form['description']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None
        technologies = request.form['technologies']
        location = request.form['location']
        is_current = 'is_current' in request.form

        # Handle company logo upload
        logo_path = None
        if 'company_logo' in request.files:
            file = request.files['company_logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1]
                random_filename = f"logo_{secrets.token_hex(8)}{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
                file.save(file_path)
                logo_path = f"screenshots/{random_filename}"

        new_experience = WorkExperience(
            CompanyName=company_name,
            Position=position,
            Description=description,
            StartDate=start_date,
            EndDate=end_date,
            Technologies=technologies,
            CompanyLogo=logo_path,
            Location=location,
            IsCurrentJob=is_current
        )

        try:
            db.session.add(new_experience)
            db.session.commit()
            flash('Work experience added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding work experience: {str(e)}', 'danger')

    return render_template('admin/add_work.html')




# Public routes
@app.route('/')
def index():
    return render_template('home.html')


@app.route('/projects')
def projects():
    categories = db.session.query(Project.Category.distinct()).all()
    projects_by_category = {category[0]: Project.query.filter_by(Category=category[0]).all() for category in categories}
    return render_template('projects.html', projects_by_category=projects_by_category)


@app.route('/work')
def work():
    experiences = WorkExperience.query.order_by(WorkExperience.StartDate.desc()).all()
    return render_template('work.html', experiences=experiences)


# Initialize admin account
def create_admin(username, password):
    with app.app_context():
        if not Admin.query.filter_by(username=username).first():
            admin = Admin(
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(admin)
            db.session.commit()


# Add these routes to your main Flask application

from flask import jsonify


# Update these routes in your main Flask application

# Update the project routes to handle multiple technologies and screenshots

@app.route('/admin/add_project', methods=['GET', 'POST'])
@admin_required
def add_project():
    if request.method == 'POST':
        new_project = Project(
            ProjectName=request.form['project_name'],
            Description=request.form['description'],
            GitHubLink=request.form['github_link'],
            PreviewLink=request.form['preview_link'],
            Category=request.form['category']
        )

        if request.form['date_started']:
            new_project.DateStarted = datetime.strptime(request.form['date_started'], '%Y-%m-%d').date()
        if request.form['date_completed']:
            new_project.DateCompleted = datetime.strptime(request.form['date_completed'], '%Y-%m-%d').date()

        # Handle technologies
        technologies = request.form.getlist('technologies')
        for tech in technologies:
            new_technology = ProjectTechnology(technology=tech)
            new_project.technologies.append(new_technology)

        # Handle screenshots
        screenshots = request.files.getlist('screenshots')
        captions = request.form.getlist('captions')

        for i, file in enumerate(screenshots):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1]
                random_filename = f"{secrets.token_hex(8)}{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
                file.save(file_path)

                caption = captions[i] if i < len(captions) else ""
                new_screenshot = ProjectScreenshot(
                    filename=f"screenshots/{random_filename}",
                    caption=caption,
                    order=i
                )
                new_project.screenshots.append(new_screenshot)

        try:
            db.session.add(new_project)
            db.session.commit()
            flash('Project added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding project: {str(e)}', 'danger')

    return render_template('admin/add_project.html', Project=Project, TECHNOLOGIES=TECHNOLOGIES)


@app.route('/admin/project/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.ProjectName = request.form['project_name']
        project.Description = request.form['description']
        project.GitHubLink = request.form['github_link']
        project.PreviewLink = request.form['preview_link']
        project.Category = request.form['category']

        if request.form['date_started']:
            project.DateStarted = datetime.strptime(request.form['date_started'], '%Y-%m-%d').date()
        if request.form['date_completed']:
            project.DateCompleted = datetime.strptime(request.form['date_completed'], '%Y-%m-%d').date()

        # Update technologies
        # Remove existing technologies
        for tech in project.technologies[:]:
            db.session.delete(tech)

        # Add new technologies
        technologies = request.form.getlist('technologies')
        for tech in technologies:
            new_technology = ProjectTechnology(technology=tech)
            project.technologies.append(new_technology)

        # Handle new screenshots
        screenshots = request.files.getlist('new_screenshots')
        captions = request.form.getlist('new_captions')

        # Handle existing screenshots
        kept_screenshots = request.form.getlist('keep_screenshot')
        for screenshot in project.screenshots[:]:
            if str(screenshot.id) not in kept_screenshots:
                # Delete file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], screenshot.filename.split('/')[-1])
                if os.path.exists(file_path):
                    os.remove(file_path)
                db.session.delete(screenshot)

        # Add new screenshots
        current_max_order = max([s.order for s in project.screenshots], default=-1)
        for i, file in enumerate(screenshots):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1]
                random_filename = f"{secrets.token_hex(8)}{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
                file.save(file_path)

                caption = captions[i] if i < len(captions) else ""
                new_screenshot = ProjectScreenshot(
                    filename=f"screenshots/{random_filename}",
                    caption=caption,
                    order=current_max_order + i + 1
                )
                project.screenshots.append(new_screenshot)

        try:
            db.session.commit()
            flash('Project updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating project: {str(e)}', 'danger')

    return render_template('admin/edit_project.html',
                           project=project,
                           Project=Project,
                           TECHNOLOGIES=TECHNOLOGIES)


# Add route to handle screenshot reordering if needed
@app.route('/admin/project/<int:project_id>/reorder_screenshots', methods=['POST'])
@admin_required
def reorder_screenshots(project_id):
    project = Project.query.get_or_404(project_id)
    new_order = request.json.get('order', [])

    try:
        for screenshot_id, order in new_order.items():
            screenshot = ProjectScreenshot.query.get(screenshot_id)
            if screenshot and screenshot.project_id == project_id:
                screenshot.order = order

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    try:
        # Delete all screenshot files associated with the project
        for screenshot in project.screenshots:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], screenshot.filename.split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)

        # The project and its associated screenshots and technologies will be deleted
        # automatically due to the cascade relationship
        db.session.delete(project)
        db.session.commit()
        flash('Project deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))  # Redirect to the admin dashboard or relevant page


@app.route('/admin/experience/<int:experience_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_experience(experience_id):
    experience = WorkExperience.query.get_or_404(experience_id)

    if request.method == 'POST':
        experience.CompanyName = request.form['company_name']
        experience.Position = request.form['position']
        experience.Description = request.form['description']
        experience.Location = request.form['location']
        experience.Technologies = request.form['technologies']
        experience.IsCurrentJob = 'is_current' in request.form

        if 'start_date' in request.form and request.form['start_date']:
            experience.StartDate = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        if 'end_date' in request.form and request.form['end_date']:
            experience.EndDate = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()

        if 'company_logo' in request.files:
            file = request.files['company_logo']
            if file and allowed_file(file.filename):
                # Delete old logo if it exists
                if experience.CompanyLogo:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], experience.CompanyLogo.split('/')[-1])
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                # Save new logo
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1]
                random_filename = f"logo_{secrets.token_hex(8)}{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
                file.save(file_path)
                experience.CompanyLogo = f"screenshots/{random_filename}"

        try:
            db.session.commit()
            flash('Work experience updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating work experience: {str(e)}', 'danger')

    return render_template('admin/edit_experience.html', experience=experience)


@app.route('/admin/experience/<int:experience_id>/delete', methods=['POST'])
@admin_required
def delete_experience(experience_id):
    experience = WorkExperience.query.get_or_404(experience_id)

    try:
        # Delete logo file if it exists
        if experience.CompanyLogo:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], experience.CompanyLogo.split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(experience)
        db.session.commit()
        flash('Work experience deleted successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

from datetime import datetime

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}


@app.context_processor
def inject_stats():
    """Make stats available to all templates."""

    # Query the database for counts
    projects_count = Project.query.count()
    experiences_count = WorkExperience.query.count()

    # Return a dictionary that will be available in all templates
    return {
        'projects_count': projects_count,
        'experiences_count': experiences_count
    }


import os
import json
from datetime import datetime

# Path for stats file
STATS_DIR = 'visitor_stats'
STATS_FILE = os.path.join(STATS_DIR, 'visitor_stats.json')

# Create directory if it doesn't exist
os.makedirs(STATS_DIR, exist_ok=True)


# Initialize or load stats
def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'total_visits': 0, 'daily_visits': {}, 'page_visits': {}}
    else:
        return {'total_visits': 0, 'daily_visits': {}, 'page_visits': {}}


def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)


@app.before_request
def track_visit():
    # Skip static files, admin routes, and non-GET requests
    if (not request.path.startswith('/static') and
            not request.path.startswith('/admin') and
            request.method == 'GET'):

        # Load current stats
        stats = load_stats()

        # Increment total visits
        stats['total_visits'] += 1

        # Track daily visits
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in stats['daily_visits']:
            stats['daily_visits'][today] = 0
        stats['daily_visits'][today] += 1

        # Track page visits
        if request.path not in stats['page_visits']:
            stats['page_visits'][request.path] = 0
        stats['page_visits'][request.path] += 1

        # Save updated stats
        save_stats(stats)


@app.route('/admin/visit_stats')
@admin_required
def visit_stats():
    stats = load_stats()

    # Sort daily visits by date (most recent first)
    sorted_daily_visits = sorted(
        [(date, count) for date, count in stats['daily_visits'].items()],
        key=lambda x: x[0],
        reverse=True
    )

    # Sort page visits by count (highest first)
    sorted_page_visits = sorted(
        [(page, count) for page, count in stats['page_visits'].items()],
        key=lambda x: x[1],
        reverse=True
    )

    return render_template(
        'admin/visit_stats.html',
        total_visits=stats['total_visits'],
        daily_visits=sorted_daily_visits[:30],  # Last 30 days
        page_visits=sorted_page_visits[:10]  # Top 10 pages
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin account
        create_admin('admin', 'change_this_password')
    app.run(debug=True)