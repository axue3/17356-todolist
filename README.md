Multiuser TODO (Django + JavaScript)
====================================

This is a Django web app with a small JavaScript frontend that lets multiple users create class TODO tasks with due dates,
select a university designation, and see a "morning reminder" for tasks due today.

Quickstart
-----------
1. Create and activate a virtualenv.
   - `python3 -m venv venv`
   - `source venv/bin/activate`
2. Install deps:
   - `pip install -r requirements.txt`
3. (Optional) Create an `.env` file for `DJANGO_SECRET_KEY` and `DJANGO_DEBUG`.
4. Initialize DB:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
5. Seed university options:
   - `python manage.py seed_universities`
6. Run:
   - `python manage.py runserver`

Notes
-----
- Authentication uses Django's built-in username/password. In the UI, "Email" is used as the username.
- Reminders are in-app: when you open the app during your configured morning window, you'll be prompted once per day.

PR Log
------
- ryan-twang 2026-03-24 Add task count summary below task list
- axue3 2026-03-24 ci: trigger workflow on PR open and merge into master
