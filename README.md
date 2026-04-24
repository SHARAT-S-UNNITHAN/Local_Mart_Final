# LocalMart – E-Commerce Platform 🛒

LocalMart is a full-stack e-commerce web application designed to connect local sellers with buyers through a simple and user-friendly platform.

---

## 🚀 Features

* User authentication (Admin, Seller, Customer)
* Seller product management system
* Product browsing and search
* Shopping cart and checkout system
* Order tracking and history
* Admin dashboard for managing users and products

---

## 🛠️ Requirements

### System Requirements

* Operating System: Windows, macOS, or Linux
* Python Version: 3.8+
* Database: SQLite (default), MySQL / PostgreSQL (optional)

### Pre-installed Tools

* Python 3.x
* Pip
* Git (optional)

---

## ⚙️ Installation & Setup

```bash
git clone https://github.com/SHARAT-S-UNNITHAN/Local_Mart_Final.git
cd Local_Mart_Final

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

python init_db.py
python manage.py runserver
```

Open in browser:

```
http://127.0.0.1:8000/
```

Admin panel:

```
http://127.0.0.1:8000/admin
```

---

## 🔐 Demo Access

A default admin account is created during database initialization.

* **Username:** admin
* **Password:** admin123

⚠️ This is a demo account. It is recommended to change credentials or create new users after setup.

---

## 📸 Screenshots

### Intro Page

![Intro](screenshots/Screenshot%202025-06-21%20221154.png)

### Home Page

![Home](screenshots/Screenshot%202025-06-21%20221201.png)

### Product Page

![Products](screenshots/Screenshot%202025-06-21%20221211.png)

### Cart Page

![Cart](screenshots/Screenshot%202025-06-21%20221223.png)

### Checkout Page

![Checkout](screenshots/Screenshot%202025-06-21%20221234.png)

### Order History

![Orders](screenshots/Screenshot%202025-06-21%20221253.png)

---

## 📌 Project Overview

This project demonstrates my ability to build a full-stack web application with authentication, database integration, and complete e-commerce functionality including user roles and order management.

---

## ⚠️ Notes

* For production use, configure environment variables and secure credentials
* Use MySQL or PostgreSQL for better scalability
* Enable HTTPS for secure communication

---

## 👨‍💻 Author

Sharat S Unnithan
