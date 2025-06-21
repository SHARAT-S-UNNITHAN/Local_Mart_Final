import sqlite3

conn = sqlite3.connect('ecommerce.db')
c = conn.cursor()
c.execute('PRAGMA table_info(products)')
columns = c.fetchall()
print("Products table columns:", columns)
conn.close()