import sqlite3

# Connect to the database
conn = sqlite3.connect('ecommerce.db')
cursor = conn.cursor()

# Query to fetch all user credentials
cursor.execute("SELECT username, email, password, role FROM users")
users = cursor.fetchall()

# Display credentials
print("User Credentials:")
for user in users:
    print(f"Username: {user[0]}, Email: {user[1]}, Password: {user[2]}, Role: {user[3]}")

# Close the connection
conn.close()

# -----------------------------------------------------------------------------
# LocalMart Project - E-commerce Platform
# Created by Sharat S Unnithan
# © 2025, LocalMart Development Team. All Rights Reserved.
# -----------------------------------------------------------------------------

