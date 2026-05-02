# ============================================================================
# FILE: models.py - Database Models
# ============================================================================
from datetime import datetime
import re
from app import db
from sqlalchemy import func

# Constants
PROJECT_CATEGORIES = [
    'Web Development',
    'Mobile Development',
    'AI & Automation',
    'Enterprise & Power Platform',
    'Cybersecurity',
    'Cloud & DevOps',
    'Penetration Testing',
    'Low-Code Development',
    'Open Source Contributions',
    'Data Science',
    'DevOps',
    'Other'
]

TECHNOLOGIES = {
    'Web Development': [
        'Flask', 'Django', 'FastAPI', 'ASP.NET MVC', 'Spring Boot', 'PHP', 'Node.js', 'Express.js',
        'HTML5', 'CSS3', 'JavaScript', 'TypeScript',
        'React', 'Angular', 'Vue.js', 'Svelte', 'Next.js',
        'SQL Server', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis',
        'Bootstrap', 'Tailwind CSS', 'Material UI', 'jQuery'
    ],
    'Mobile Development': [
        'Java', 'Kotlin', 'Android SDK', 'Swift', 'iOS',
        'React Native', 'Flutter', 'Dart',
        'Firebase', 'SQLite', 'Realm'
    ],
    'Penetration Testing': [
        'Burp Suite', 'Metasploit', 'Wireshark', 'Nmap',
        'Python', 'Bash', 'PowerShell',
        'OWASP ZAP', 'Kali Linux', 'SQLMap', 'Nikto'
    ],
    'AI & Automation': [
        'Azure OpenAI', 'IBM Granite', 'Microsoft Copilot', 'AI Builder',
        'Python', 'Azure Cognitive Services', 'Azure Functions',
        'Microsoft Graph API', 'Playwright', 'LangChain',
        'Power Automate', 'Dataverse'
    ],
    'Enterprise & Power Platform': [
        'Power Apps', 'Power Pages', 'Power Automate', 'Power BI',
        'Dataverse', 'Model-Driven App', 'AI Builder',
        'SharePoint', 'Microsoft 365', 'Power Platform Connectors',
        '.NET', 'C#', 'AL', 'Business Central', 'Microsoft Graph API'
    ],
    'Cybersecurity': [
        'Kali Linux', 'Metasploit', 'Burp Suite', 'Nmap', 'Wireshark',
        'OWASP ZAP', 'SQLMap', 'Nikto', 'Python', 'Bash', 'PowerShell'
    ],
    'Cloud & DevOps': [
        'Microsoft Azure', 'Azure Functions', 'Azure DevOps',
        'Azure Active Directory', 'Azure Cognitive Services',
        'AWS', 'GCP', 'Docker', 'Kubernetes',
        'Terraform', 'Ansible', 'GitHub Actions',
        'Python', 'Bash', 'Microsoft Graph API', 'Dataverse'
    ],
    'Low-Code Development': [
        'Power Apps', 'Power Automate', 'Power BI',
        'SharePoint', 'Microsoft 365',
        'Power Platform Connectors', 'Dataverse'
    ],
    'Open Source Contributions': [
        'Git', 'GitHub', 'GitLab', 'Bitbucket',
        'Documentation', 'Code Review',
        'Unit Testing', 'CI/CD', 'GitHub Actions'
    ],
    'Data Science': [
        'Python', 'R', 'Jupyter', 'Pandas', 'NumPy',
        'Scikit-learn', 'TensorFlow', 'PyTorch',
        'Matplotlib', 'Seaborn', 'Plotly'
    ],
    'DevOps': [
        'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI',
        'AWS', 'Azure', 'GCP', 'Terraform',
        'Ansible', 'Nginx', 'Apache'
    ]
}


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    picture = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    github_link = db.Column(db.String(500))
    preview_link = db.Column(db.String(500))
    date_started = db.Column(db.Date)
    date_completed = db.Column(db.Date)
    display_order = db.Column(db.Integer, default=0, index=True)
    is_visible = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    technologies = db.relationship('ProjectTechnology', back_populates='project', cascade='all, delete-orphan')
    images = db.relationship('ProjectImage', back_populates='project', cascade='all, delete-orphan',
                             order_by='ProjectImage.display_order')

    @property
    def technologies_list(self):
        return [tech.technology for tech in self.technologies]

    @property
    def slug(self):
        """URL-friendly version of project name for SEO."""
        s = self.name.lower()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'[\s_]+', '-', s)
        s = re.sub(r'-+', '-', s)
        return s.strip('-')

    @property
    def primary_image(self):
        return self.images[0] if self.images else None


class ProjectTechnology(db.Model):
    __tablename__ = 'project_technologies'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    technology = db.Column(db.String(100), nullable=False)
    project = db.relationship('Project', back_populates='technologies')


class ProjectImage(db.Model):
    __tablename__ = 'project_images'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(500))
    display_order = db.Column(db.Integer, default=0)
    project = db.relationship('Project', back_populates='images')


class WorkExperience(db.Model):
    __tablename__ = 'work_experience'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    technologies = db.Column(db.String(500))
    company_logo = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=0, index=True)
    is_visible = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45))
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def mark_read(self):
        self.is_read = True

    @staticmethod
    def get_unread_count():
        return ContactMessage.query.filter_by(is_read=False).count()


class PageVisit(db.Model):
    __tablename__ = 'page_visits'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    referrer = db.Column(db.String(500))
    query_string = db.Column(db.String(500))
    visited_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def get_page_stats(days=30, limit=10):
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        results = db.session.query(
            PageVisit.path,
            func.count(PageVisit.id).label('visit_count')
        ).filter(
            PageVisit.visited_at >= cutoff_date
        ).group_by(
            PageVisit.path
        ).order_by(
            func.count(PageVisit.id).desc()
        ).limit(limit).all()
        return results

    @staticmethod
    def get_referrer_stats(days=30, limit=10):
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        results = db.session.query(
            PageVisit.referrer,
            func.count(PageVisit.id).label('visit_count')
        ).filter(
            PageVisit.visited_at >= cutoff_date,
            PageVisit.referrer != '',
            PageVisit.referrer.isnot(None)
        ).group_by(
            PageVisit.referrer
        ).order_by(
            func.count(PageVisit.id).desc()
        ).limit(limit).all()
        return results


class DailyStats(db.Model):
    __tablename__ = 'daily_stats'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    total_visits = db.Column(db.Integer, default=0)
    unique_visitors = db.Column(db.Integer, default=0)

    @staticmethod
    def get_recent_stats(days=30):
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow().date() - timedelta(days=days)
        return DailyStats.query.filter(DailyStats.date >= cutoff_date).order_by(DailyStats.date.desc()).all()

    @staticmethod
    def get_total_visits():
        result = db.session.query(func.sum(DailyStats.total_visits)).scalar()
        return result or 0

    @staticmethod
    def get_total_unique_visitors():
        result = db.session.query(func.sum(DailyStats.unique_visitors)).scalar()
        return result or 0


class BrowserStats(db.Model):
    __tablename__ = 'browser_stats'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    browser = db.Column(db.String(100))
    device_type = db.Column(db.String(50))
    os = db.Column(db.String(100))
    visit_count = db.Column(db.Integer, default=1)
    __table_args__ = (db.Index('idx_date_browser', 'date', 'browser'),)