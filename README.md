# Speed-Sessions_django

**Run Faster, train harder, together.**

*Deployed at: [runtrash.com](https://runtrash.com)*

Speed-Sessions_django is a web application designed specifically for run club community organizers. It simplifies the process of planning group speed sessions by organizing runners of similar abilities into appropriate training groups.

By leveraging scientific training metrics, the platform ensures that every runner gets a workout tailored to their current fitness level—maximizing performance gains while minimizing the risk of overtraining.

## ✨ Key Features

- **Scientific Pacing & Workouts:** Utilizes **VDOT** scores and **TSS** (Training Stress Score) calculations to generate dynamically paced workouts. This ensures sessions have sufficient intensity and duration for each individual's ability level without leading to overtraining.
- **Community Management:** Tailored for organizers to manage their run clubs, group runners, and plan customized block sessions.
- **Dynamic User Interface:** Built with HTMX and Tailwind CSS (via DaisyUI) for a snappy, modern, and responsive user experience.
- **Merchandise & Payments:** Integrated with Stripe and dj-stripe for handling run club merchandise sales directly through the platform.
- **Authentication & Profiles:** Powered by `django-allauth` for seamless user registration, profile management, and community assignments.

## 🚀 Tech Stack

- **Backend:** Django (Python 3.13), PostgreSQL/SQLite
- **Frontend:** HTMX, Tailwind CSS, DaisyUI
- **Testing:** Pytest, Pytest-Django, FactoryBoy
- **Payments:** Stripe, dj-stripe
- **Emails:** django-anymail (Resend)
- **Deployment:** Docker, Vercel ready

---

## 💻 Local Development Setup

To get the project running locally on your machine, follow these steps:

### 1. Prerequisites
- Python 3.13 (Target version. Check using `python --version`)
- Node.js & npm (for Tailwind CSS compilation)
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/hackneychap/speed-sessions-django.git
cd speed-sessions-django
```

### 3. Set up the Python Environment
Create and activate a virtual environment:
```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

### 4. Set up the Frontend (Tailwind CSS)
Install the Node dependencies for the frontend:
```bash
npm install
```

Build the CSS (you can run `npm run watch:css` in a separate terminal during development to auto-recompile CSS changes):
```bash
npm run build:css
```

### 5. Environment Variables
Create a `.env` file in the root directory and configure your environment variables. You can start with the following essentials for local development:
```env
DEBUG=True
SECRET_KEY=your-local-secret-key
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_ENGINE=sqlite3
DATABASE_NAME=db.sqlite3
```
*(Note: For Stripe and Resend functionality, you will need to add your respective API keys.)*

### 6. Database Setup
Apply the migrations to set up your local database:
```bash
python manage.py migrate
```

*(Optional)* Create a superuser for accessing the Django admin:
```bash
python manage.py createsuperuser
```

### 7. Run the Development Server
Start the Django development server:
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your browser.

---

## 🐳 Running with Docker

For an easier setup or testing production-like environments, you can use Docker Compose. The `compose.yml` is configured to spin up both the Django web application and a PostgreSQL database.

1. Ensure Docker and Docker Compose are installed.
2. Ensure you have a `.env` file configured (see above).
3. Run the following command:
```bash
docker-compose up --build
```
This will automatically build the images, collect static files, apply database migrations, and start the app on `http://localhost:8000`.

---

## ☁️ Deployment

### Vercel Deployment
The project is configured for serverless deployment on Vercel (`vercel.json` is included).
- The `build.sh` script handles upgrading pip, installing requirements, migrating the database, and building the Tailwind CSS before deployment.
- Ensure all environment variables (e.g., `DATABASE_URL`, `SECRET_KEY`, `VERCEL=1`) are set in your Vercel project settings.

### Docker Deployment
The provided `Dockerfile` and `compose.yml` can be used to deploy the application to any container-hosting platform (e.g., AWS ECS, DigitalOcean App Platform, Fly.io).

## 🧪 Testing

The project uses `pytest` for testing. To run the test suite locally:
```bash
export SECRET_KEY='test-secret-key'
export DATABASE_URL='sqlite:///:memory:'
export PYTHONPATH='.'
export DJANGO_SETTINGS_MODULE=speed_sessions.settings

python -m pytest
```
