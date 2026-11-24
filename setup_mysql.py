"""
Tech Mart - MySQL Database Setup and Migration Helper
Automates creating the MySQL database 'techmart_db' on your local MySQL Server,
updates the .env configuration file securely, runs Django migrations,
and seeds all initial categories, tech products, and accounts.
"""

import os
import sys
import getpass
from pathlib import Path
from dotenv import load_dotenv
import MySQLdb

BASE_DIR = Path(__file__).resolve().parent

def prompt_credentials():
    print("=" * 65)
    print("      TECH MART - CONNECT LOCAL MYSQL SERVER (LAPTOP)")
    print("=" * 65)
    print("MySQL Server 8.0 is running on your laptop at 127.0.0.1:3306.")
    print()

    env_file = BASE_DIR / '.env'
    load_dotenv(env_file)
    
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = int(os.getenv('DB_PORT', '3306'))
    db_name = os.getenv('DB_NAME', 'techmart_db')
    default_user = os.getenv('DB_USER', 'root')
    existing_password = os.getenv('DB_PASSWORD', '')

    user_input = input(f"Enter MySQL Username [{default_user}]: ").strip()
    db_user = user_input if user_input else default_user

    password = None
    if existing_password:
        use_existing = input(f"Use password already saved in .env? [Y/n]: ").strip().lower()
        if use_existing not in ('n', 'no'):
            password = existing_password

    if password is None:
        print("(Note: Characters will not appear on screen while typing password)")
        password = getpass.getpass("Enter MySQL Password: ")

    print(f"\n[1/4] Connecting to MySQL Server at {db_host}:{db_port} as '{db_user}'...")
    try:
        conn = MySQLdb.connect(
            host=db_host,
            port=3306,
            user=db_user,
            passwd=password
        )
        print("✓ Connected successfully!")

        cursor = conn.cursor()
        print(f"\n[2/4] Creating database '{db_name}' if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✓ Database '{db_name}' is ready.")

        print("\n[3/4] Updating .env to activate MySQL mode...")
        env_content = f"""# Tech Mart - Django & MySQL Configuration
SECRET_KEY=techmart-django-production-key-{os.urandom(12).hex()}
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,*
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# MySQL Database Settings (Installed on your laptop)
DB_ENGINE=django.db.backends.mysql
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={password}
DB_HOST={db_host}
DB_PORT={db_port}

# Set to False to run directly on MySQL Server
USE_SQLITE=False
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✓ Updated .env file with verified MySQL credentials.")

        # Run Django Migrations and Seeding
        python_exe = sys.executable
        print("\n[4/4] Applying database tables and seeding catalog on MySQL...")
        os.system(f'"{python_exe}" manage.py migrate')
        os.system(f'"{python_exe}" manage.py seed_data')

        print("\n" + "=" * 65)
        print("  SUCCESS! Tech Mart is now connected to your local MySQL Server.")
        print("=" * 65)
        print("You can start the website at any time by running:")
        print("  run_website.bat")
        print("or:")
        print("  python manage.py runserver")
        print("\nPre-configured accounts:")
        print("  • Admin Dashboard:    http://127.0.0.1:8000/admin-dashboard/")
        print("    Username: admin  | Password: admin123")
        print("  • Customer Store:     http://127.0.0.1:8000/")
        print("    Username: rahul  | Password: customer123")
        print("=" * 65)

    except MySQLdb.OperationalError as e:
        print(f"\n❌ [ERROR] Could not connect to MySQL Server: {e}")
        print("Suggestions:")
        print("  1. Verify the password you entered.")
        print("  2. Ensure the Windows 'MySQL80' service is running.")
        sys.exit(1)

if __name__ == '__main__':
    prompt_credentials()
