# Speed-Sessions-django

**Run Faster, train harder, together.**

*Deployed at: [runtrash.com](https://runtrash.com)*

Speed-Sessions-django is a web application designed specifically for run club community organizers. It simplifies the process of planning group speed sessions by organizing runners of similar abilities into appropriate training groups.

By leveraging scientific training metrics, the platform ensures that groups of runners get a workout tailored to their current fitness level—maximizing performance gains while minimizing the risk of overtraining.

## 🧠 The Methodology & Structure

The difficulty with speed sessions is that if you run too hard, you get injured; too easy, you don't improve. This platform addresses that by relying on the **VDOT system** (from Jack Daniels' *Running Formula*) and **TSS (Training Stress Score)**.

### How We Plan Sessions
* **VDOT sets the pace:** If a classic session is 12 x 400m at "Interval pace," the VDOT score dictates exactly how fast that 400m should be run.
* **TSS sets the volume:** The number of repeats (duration and distance) is controlled by TSS. We target a TSS score of around **35–43** for the main session. This typically aligns with ~30 minutes of running and ~5km distance, allowing it to fit into most training schedules and ensuring the workout is optimal without being destructive.
* **Smart Session Builder:** When building a session, the app dynamically calculates the pacing based on the group's entered VDOT score and alerts the planner if the resulting TSS is too short, too long, or too hard.

### Track Etiquette & Pacing
A typical session goes like this:
1. **Warm up:** ~10 laps easy conversational pace (e.g., in lane 5), followed by ~10 mins of drills.
2. **Break:** Short pause for everyone.
3. **The Main Session:** Run in assigned, closely matched pace groups (e.g., VDOT 55, 50, and 43).
4. **Cool down:** A two-lap cool down.

**The Role of the Pacer:**
* The pacer memorizes the splits (e.g., for a VDOT 50 runner doing 400m reps in 1:33, they hit 23 seconds every 100m).
* The pacer uses a stopwatch to check their 100m splits and call them out. **We don't rely on GPS watches for pacing**; the only distance that matters is the markings on the track.
* Everyone else in the group matches the pacer. They don't overtake; they follow along, learn to feel the pace, and encourage each other.
* The calculated paces are a limit, not a target. If an individual in the group is struggling, they should drop to a slower pace, as their personal TSS for that effort might be too high.

## ✨ Key Features

- **Scientific Pacing & Workouts:** Utilizes **VDOT** scores and **TSS** (Training Stress Score) calculations to generate dynamically paced workouts.
- **Session Validation:** Flags workouts that are too hard or too easy based on the calculated metrics.
- **Community Management:** Tailored for organizers to manage their run clubs, group runners by ability, and plan customized block sessions.
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
