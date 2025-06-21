# Local_Mart_Final
LocalMart is an e-commerce platform designed to connect local sellers with buyers. This guide provides a step-by-step walkthrough for installing, setting up, and using the platform effectively.

1. Requirements

System Requirements

Operating System: Windows, macOS, or Linux

Python Version: 3.8+

Database: SQLite (default), MySQL, or PostgreSQL (optional for production)

Dependencies: Listed in requirements.txt

Pre-installed Tools

Python 3.x

Pip (Python package manager)

Git (optional)

LocalMart is an e-commerce platform designed to connect local sellers with buyers. To set it up, begin by cloning the GitHub repository using the command git clone https://github.com/SHARAT-S-UNNITHAN/Local_Mart_Final.git. Navigate to the project directory and create a virtual environment using python -m venv venv and activate it. Install the dependencies listed in requirements.txt using pip install -r requirements.txt. Initialize the database by running python init_db.py, which creates the necessary tables and seeds default data, including admin credentials (Username: admin, Password: admin123). Start the server with python manage.py runserver and access the application at http://127.0.0.1:8000/. The admin panel is available at http://127.0.0.1:8000/admin, where you can log in using the admin credentials. LocalMart features include seller registration, product management, order tracking, and buyer functionalities like browsing products, adding them to a cart, and placing orders. Admins can approve sellers, manage categories, and oversee orders. For production, use a database like MySQL or PostgreSQL and host on platforms like AWS or Heroku. Ensure sensitive data is stored as environment variables and HTTPS is enabled for security. 


CREDENTIALS ALREADY IN THE PROJECT
Username: admin, Email: admin@example.com, Password: admin123, Role: admin
Username: Aswapathy Raj, Email: aswapathyachu@gmail.com, Password: Achu123#, Role: seller
Username: achu, Email: achuchannelvloger@gmail.com, Password: Achu123#, Role: user
Username: kalhar, Email: kalhar@gmail.com, Password: Achu123#, Role: seller
Username: Sha_Enterprises, Email: sharatsunnithan@seller.com, Password: 123456789, Role: seller


## Screenshots

![Intro Page](screenshots/Screenshot%202025-06-21%20221154.png)

![HomePage](screenshots/Screenshot%202025-06-21%20221201.png)

![Product Page](screenshots/Screenshot%202025-06-21%20221211.png)

![Cart Page](screenshots/Screenshot%202025-06-21%20221223.png)

![Checkout Page](screenshots/Screenshot%202025-06-21%20221234.png)

![Order History](screenshots/Screenshot%202025-06-21%20221253.png)




