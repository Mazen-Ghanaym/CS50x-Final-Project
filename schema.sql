CREATE TABLE IF NOT EXISTS "users"(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,password TEXT NOT NULL,
    visa TEXT, 
    cash DEFAULT 0, 
    isAdmin INTEGER DEFAULT 0, 
    address TEXT, 
    phone_number TEXT);

CREATE TABLE purchase(
    user_id INTEGER,
    bookname TEXT,
    amount INTEGER,
    datetime TEXT,
    bookprice INTEGER,
    total INTEGER);

CREATE TABLE books(
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    name TEXT not null,
    author TEXT, 
    price INTEGER,
    amount INTEGER, 
    google_id TEXT);
