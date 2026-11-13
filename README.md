# AI-Based Honeypot System (Phase 4.5)

## First-time setup
1. cd employee_app
2. python -m venv venv  (then activate it)
3. pip install -r ../requirements.txt
4. copy .env.example to .env  and set SECRET_KEY:
   python -c "import secrets; print(secrets.token_hex(32))"
5. uvicorn main:app --reload

The database already contains 300 synthetic employees.
To change the total: python seed_employees.py 500
