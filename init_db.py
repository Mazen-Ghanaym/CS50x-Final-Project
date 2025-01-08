import sqlite3

conn = sqlite3.connect('trading2.db')
c = conn.cursor()

# create the whole database structure using schema.sql
with open('schema.sql', 'r') as f:
    c.executescript(f.read())
    
conn.commit()
conn.close
