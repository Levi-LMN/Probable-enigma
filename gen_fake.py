import os
import random
import secrets
from datetime import datetime, timedelta
from faker import Faker
from app import db, Project, ProjectTechnology, ProjectScreenshot, WorkExperience, PROJECT_CATEGORIES, TECHNOLOGIES, app

fake = Faker()

# Path to existing screenshots
SCREENSHOTS_FOLDER = app.config['UPLOAD_FOLDER']

def get_random_screenshots():
    """Get random existing screenshots from the folder."""
    files = [f for f in os.listdir(SCREENSHOTS_FOLDER) if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
    return random.sample(files, min(len(files), random.randint(1, 5)))  # Pick up to 5 screenshots

def create_fake_projects(num_projects=10):
    with app.app_context():
        for _ in range(num_projects):
            category = random.choice(PROJECT_CATEGORIES)
            technologies = random.sample(TECHNOLOGIES[category], min(3, len(TECHNOLOGIES[category])))
            start_date = fake.date_between(start_date='-2y', end_date='today')
            end_date = start_date + timedelta(days=random.randint(30, 300))

            project = Project(
                ProjectName=fake.sentence(nb_words=4),
                Description=fake.paragraph(nb_sentences=5),
                GitHubLink=fake.url(),
                PreviewLink=fake.url(),
                DateStarted=start_date,
                DateCompleted=end_date if random.choice([True, False]) else None,
                Category=category
            )
            db.session.add(project)
            db.session.flush()  # Get project ID

            for tech in technologies:
                db.session.add(ProjectTechnology(project_id=project.ProjectID, technology=tech))

            for index, screenshot in enumerate(get_random_screenshots()):
                db.session.add(ProjectScreenshot(
                    project_id=project.ProjectID,
                    filename=f"screenshots/{screenshot}",
                    caption=fake.sentence(nb_words=6),
                    order=index
                ))

        db.session.commit()
        print(f"{num_projects} fake projects added successfully.")

def create_fake_work_experiences(num_experiences=5):
    with app.app_context():
        for _ in range(num_experiences):
            start_date = fake.date_between(start_date='-5y', end_date='-1y')
            end_date = start_date + timedelta(days=random.randint(365, 1000)) if random.choice([True, False]) else None
            is_current = end_date is None

            work_experience = WorkExperience(
                CompanyName=fake.company(),
                Position=fake.job(),
                Description=fake.paragraph(nb_sentences=5),
                StartDate=start_date,
                EndDate=end_date,
                Technologies=', '.join(fake.words(nb=5, unique=True)),
                CompanyLogo=f"screenshots/{random.choice(get_random_screenshots())}" if random.choice([True, False]) else None,
                Location=fake.city(),
                IsCurrentJob=is_current
            )
            db.session.add(work_experience)

        db.session.commit()
        print(f"{num_experiences} fake work experiences added successfully.")

if __name__ == "__main__":
    create_fake_projects(10)
    create_fake_work_experiences(5)