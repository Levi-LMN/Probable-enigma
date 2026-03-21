# Portfolio Management System

A Flask-based portfolio website with Google OAuth authentication, advanced analytics, and content management.

## ✨ Features

### Content Management
- **Projects**: Add, edit, delete with multiple images, technologies, and ordering
- **Work Experience**: Manage employment history with company logos
- **Visibility Controls**: Toggle visibility and set display order for projects/experiences
- **Featured Projects**: Highlight specific projects on homepage

### Advanced Analytics
- **Detailed Tracking**: Page visits, unique visitors, referrers
- **Daily Statistics**: Aggregated daily metrics
- **Visual Reports**: Charts and graphs for insights
- **Data Management**: Clear all data or data older than X days
- **Clean Filtering**: Ignores `/static`, `/robots.txt`, admin routes

### Security
- **Google OAuth**: Secure authentication (no passwords to manage)
- **Email Whitelisting**: Only specified email can access admin
- **Session Management**: Secure session handling

## 📁 Project Structure

```
portfolio/
├── app.py                      # Application factory
├── models.py                   # Database models
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── blueprints/
│   ├── __init__.py
│   ├── auth.py                # Authentication routes
│   ├── public.py              # Public-facing routes
│   └── admin.py               # Admin panel routes
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── projects.html
│   ├── project_detail.html
│   ├── work.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── analytics.html     # NEW: Detailed analytics page
│   │   ├── project_form.html
│   │   └── experience_form.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
└── static/
    ├── uploads/
    │   ├── projects/
    │   └── experience/
    └── css/
```

## 🚀 Setup Instructions

### 1. Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd portfolio

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google+ API**
4. Navigate to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure OAuth consent screen:
   - User Type: External
   - Add your email as test user
6. Create OAuth Client ID:
   - Application type: Web application
   - Authorized redirect URIs: 
     - `http://localhost:5000/auth/callback`
     - `https://yourdomain.com/auth/callback` (for production)
7. Copy **Client ID** and **Client Secret**

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
```

Edit `.env`:
```bash
SECRET_KEY=your-random-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
ADMIN_EMAIL=your-email@gmail.com
```

### 4. Initialize Database

```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 5. Run the Application

```bash
python app.py
```

Visit: `http://localhost:5000`

Admin login: `http://localhost:5000/auth/login`

## 📊 Analytics Features

### What's Tracked
- ✅ Total page visits
- ✅ Unique daily visitors (session-based)
- ✅ Individual page popularity
- ✅ Referrer sources
- ✅ Visit timestamps
- ✅ User agents (for future device/browser stats)

### What's NOT Tracked
- ❌ Static files (`/static/*`)
- ❌ Favicon requests
- ❌ robots.txt
- ❌ Admin panel pages
- ❌ Non-GET requests

### Analytics Management

**View Analytics**: `/admin/analytics`

**Clear All Data**: 
- Button in analytics page
- Deletes ALL analytics data

**Clear Old Data**:
- Specify number of days to keep
- Removes data older than threshold

### Analytics Details

The analytics page shows:

1. **Overview Stats**
   - Total visits all-time
   - Total unique visitors
   - 7-day trend (% change)

2. **Daily Breakdown**
   - Date
   - Total visits that day
   - Unique visitors that day

3. **Most Visited Pages**
   - Page path
   - Visit count
   - Percentage of total

4. **Top Referrers**
   - Referrer URL
   - Visit count
   - Shows where traffic comes from

## 🎨 Display Order & Visibility

### Projects
- **Display Order**: Lower numbers appear first (0, 1, 2, ...)
- **Visibility**: Hide projects without deleting them
- **Featured**: Mark projects to show on homepage

### Work Experience
- **Display Order**: Control order independent of dates
- **Visibility**: Hide entries from public view

## 🔧 Admin Features

### Dashboard (`/admin/dashboard`)
- Quick overview of all content
- Today's visit count
- Total statistics
- Quick toggles for visibility

### Project Management
- Add/Edit with multiple images
- Drag-and-drop image ordering
- Multi-select technologies
- Category-based organization

### Work Experience Management
- Company logo upload
- Current job checkbox (auto-hides end date)
- Rich text descriptions

### Analytics (`/admin/analytics`)
- Comprehensive visitor insights
- Date range selector (7, 30, 90 days)
- Data export capabilities
- Manual data cleanup

## 🌐 Deployment

### Using Gunicorn (Production)

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### Environment Variables for Production

Update authorized redirect URIs in Google Console:
```
https://yourdomain.com/auth/callback
```

Set production environment variables:
```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@host/db  # If using PostgreSQL
```

## 🛠️ Customization

### Adding New Project Categories

Edit `models.py`:
```python
PROJECT_CATEGORIES = [
    'Web Development',
    'Your New Category',
    # ...
]
```

### Adding Technologies for New Category

Edit `models.py`:
```python
TECHNOLOGIES = {
    'Your New Category': [
        'Technology 1',
        'Technology 2',
    ],
}
```

## 📝 Notes

- Analytics are stored in database (not JSON files)
- Session-based unique visitor tracking (cookie-free)
- All uploads stored in `static/uploads/`
- Images auto-deleted when removing content
- Supports multiple admins (add to `Admin` table)

## 🐛 Troubleshooting

**Issue**: Can't log in
- Check `ADMIN_EMAIL` matches your Google account
- Verify OAuth credentials are correct
- Check redirect URI is authorized in Google Console

**Issue**: Analytics not tracking
- Check `TRACK_VISITS` is `True` in config
- Verify database has write permissions
- Check browser console for errors

**Issue**: Images not uploading
- Check `UPLOAD_FOLDER` directory exists and is writable
- Verify file type is in `ALLOWED_EXTENSIONS`
- Check `MAX_CONTENT_LENGTH` setting

## 📄 License

MIT License - Feel free to use for your portfolio!