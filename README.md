# Tech Mart - Indian Consumer Electronics E-Commerce Platform

A responsive e-commerce web platform built with **Python (Django)**, **HTML5/CSS3/Bootstrap 5**, and **MySQL Server**. Designed with localized Indian consumer electronics cues (₹ INR formatting, GST invoices, EMI calculators, Pincode express delivery estimators, and doorstep delivery OTP PIN verification).

---

## 🌟 Key Features & Role-Based Permissions

### 👤 1. Customer Role
- **Account Registration & Authentication:** Secure registration and login with session management.
- **Product Catalog & Browsing:** Browse electronics with multi-tier filters (Categories, Brand, Price Range, In-Stock) and sorting (Featured, Price Low-High, Price High-Low, Rating, Newest).
- **Product Details Page:** High-resolution product images, MRP strikethrough, savings calculation, live Pincode delivery estimator, EMI & bank offer breakdowns, key technical specifications, and customer review scores.
- **Shopping Cart:** Add products, update quantities, real-time recalculation, 18% GST calculation, and free delivery thresholds.
- **Checkout & Address Management:** Select from saved addresses or add a new delivery address with Indian state and 6-digit PIN code. Multiple payment options (UPI, Credit/Debit Cards, Net Banking, Cash on Delivery).
- **Order Tracking & Deliveries:**
  - Real-time 4-step tracking timeline: *Order Confirmed → Packed & Sealed → In Transit → Out for Delivery*.
  - 4-digit doorstep delivery PIN verification.
  - Active in-flight deliveries vs. delivered orders separation.
  - Printable/downloadable official **GST Tax Invoice**.

### 🛠️ 2. Admin Role (Role-Based Permissions)
- **Protected Admin Dashboard:** Only accessible to users with `ADMIN` role (`@admin_required` decorator prevents customers from accessing any admin pages or actions).
- **Executive Analytics:** Real-time metrics for Total Revenue (₹), Total Orders, In-Flight Deliveries, Total SKUs, Customer Count, and Low Stock Alerts.
- **Product Management:** Full CRUD operations (Add, Edit, Delete, Restock, Pricing, MRP, Specs, Image Uploads, and Spotlight Deal tags).
- **Category Management:** Create, edit, and organize product categories with Material Symbol icons.
- **Order Management & Logistics:** Update fulfillment status (*Confirmed, Packed, In Transit, Out for Delivery, Delivered, Cancelled*), assign courier partners (Bluedart, Ekart, etc.), tracking AWB numbers, and update location milestones.
- **Customer Account Management:** Monitor registered customer accounts, view order activity, and activate or suspend accounts.

---

## 🔑 Pre-Configured Demo Accounts

| Role | Username | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Admin Dashboard, Product Management, Category CRUD, Order Logistics & Status Updates, Customer Accounts |
| **Customer** | `rahul` | `customer123` | Browsing, Cart, Checkout, Order Tracking, Handover PIN, Order History & GST Invoices |

---

## 💻 Technology Stack

- **Backend:** Python 3, Django 6.1
- **Database:** MySQL Server 8.0 (with `mysqlclient` and environment-based configuration)
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Material Symbols Outlined, Google Fonts (*Plus Jakarta Sans* & *Inter*)
- **Security:** Credentials stored securely in `.env` (kept out of source code), CSRF tokens, password hashing, and role verification decorators.

---

## 🚀 Setting Up the MySQL Database & Running the Website

### Step 1: Ensure MySQL Server is Running
Make sure **MySQL Server 8.0** is running on your PC (port `3306`).
You can check or start MySQL via Windows Services (`services.msc` -> `MySQL80`) or by running:
```cmd
net start MySQL80
```

### Step 2: Automated MySQL Setup (Recommended)
Run the automated setup helper which connects to your MySQL Server, creates the `techmart_db` database, updates `.env`, applies migrations, and seeds initial data:

**Option A - Double click:**
Double-click `setup_database.bat` in the project root.

**Option B - Via Command Prompt / PowerShell:**
```cmd
python setup_mysql.py
```
*It will ask for your MySQL root password, test the connection, create `techmart_db`, write `.env`, and populate all initial demo data automatically.*

---

### Alternative: Manual Setup (If preferred)

1. **Create the Database in MySQL:**
   Open MySQL Command Line Client or MySQL Workbench and run:
   ```sql
   CREATE DATABASE techmart_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Configure `.env` File:**
   Open `.env` in the project root directory and update your MySQL password:
   ```env
   SECRET_KEY=techmart-django-secret-key-production-change-this-string
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost

   # MySQL Database Configuration
   DB_ENGINE=django.db.backends.mysql
   DB_NAME=techmart_db
   DB_USER=root
   DB_PASSWORD=your_mysql_password_here
   DB_HOST=127.0.0.1
   DB_PORT=3306

   # Set USE_SQLITE=False to connect directly to MySQL
   USE_SQLITE=False
   ```

3. **Apply Migrations and Seed Initial Data:**
   ```cmd
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_data
   ```

---

### Step 3: Run the Development Web Server

Run:
```cmd
python manage.py runserver
```
*(Or double-click `run_website.bat`)*

Then open your browser at:
- **Storefront (Customer):** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Dashboard:** [http://127.0.0.1:8000/admin-dashboard/](http://127.0.0.1:8000/admin-dashboard/)
- **Django Built-in Admin:** [http://127.0.0.1:8000/django-admin/](http://127.0.0.1:8000/django-admin/)

---

## 🧪 Running Automated Tests

Run the test suite to verify role-based permissions and checkout workflows:
```cmd
python manage.py test
```
All 4 test cases verify:
- Public catalog pages load properly (HTTP 200).
- Customers are strictly denied access to the Admin Dashboard (HTTP 302 redirect with warning).
- Administrators can access all administrative pages.
- End-to-end shopping cart and checkout order creation flow.
