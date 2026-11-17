# Company Payroll

Company Payroll is a Django application for managing employee records, attendance, leave, overtime, and loans. HR generates semi-monthly payroll for days 1–15 and 16 through the end of the month. Employees can view their own payslips.

## Local setup

Use Git and Python 3.13, the Python version used in CI. Django uses SQLite locally and creates `db.sqlite3` when you run migrations.

In PowerShell, run the following from the repository root. If you are starting fresh, clone the repository first with `git clone https://github.com/jopher14/company-payroll.git` and open the `company-payroll` folder.

```powershell
python -m venv .venv
$env:DEBUG = "True"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

On macOS or Linux, use `export DEBUG=True` and `.venv/bin/python` for the commands that use the virtual environment.

1. Sign in with your superuser account at [http://127.0.0.1:8000/users/login/](http://127.0.0.1:8000/users/login/).
2. Open [Register User](http://127.0.0.1:8000/users/register/) and create an account with the **Human Resources** role.
3. Sign in as HR to manage employee records and generate payroll. Use a separate employee account to check the employee payslip view.

For local development, Django generates a temporary signing key if `DJANGO_SECRET_KEY` is unset and `DEBUG=True`. Set a private local key if you want sessions to survive server restarts.

## Run backend checks

From the same PowerShell session, run:

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

## Build the React frontend

The Django screens run without a React build. To build the separate frontend, use Node.js 20, the version used in CI:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
```

The build output is written to `frontend/build`.

## Deploy to Render

The [Render Blueprint](render.yaml) builds the frontend, installs Python dependencies, collects static files, and starts Gunicorn. Apply Django migrations to the deployment database before serving traffic.

- Set `DEBUG=False` on the Render service.
- Set `DJANGO_SECRET_KEY` to a fresh, private value on an existing service. The Blueprint generates a key for new configurations. Rotating the key may invalidate existing sessions and signed tokens.
- If using the [GitHub Actions deployment workflow](.github/workflows/ci-cd.yml), set the Render deploy hook as the repository secret `RENDER_DEPLOY_HOOK`. The deploy job runs on pushes to `main`.

Payroll and loan records are stored in the configured database. If deploying with SQLite, use persistent storage for the database file.
