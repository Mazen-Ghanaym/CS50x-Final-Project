import os
import datetime
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
import time
from time import strftime
import datetime
from functools import wraps
import requests
from dotenv import load_dotenv

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.debug = True
# Configure CS50 Library to use SQLite database

#SQL("sqlite:///trading.db")    
load_dotenv()
API_KEY = os.getenv('API_KEY')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/",methods=["GET", "POST"])
@login_required
def index():
    con = sqlite3.connect("trading.db")
    db = con.cursor()
    db.execute("SELECT * FROM purchase WHERE user_id=?;", (session["user_id"],))
    columns = [column[0] for column in db.description]
    transactions = [dict(zip(columns, row)) for row in db.fetchall()]
    if request.method=="GET":
        url=f'https://www.googleapis.com/books/v1/volumes?q=arts+subject'
        response = requests.get(url)
        arts = response.json()
        return render_template("profile.html", rows=transactions, data=arts,header="Arts")
    else:
        option = request.form['dropdown']
        url=f'https://www.googleapis.com/books/v1/volumes?q={option}&keys:key={API_KEY}'
        response = requests.get(url)
        data = response.json()
        #print(data)
        con.commit()
        db.close()
        con.close()
        if data is None:
            return redirect("/")
        else:
            return render_template("profile.html", data=data, rows=transactions ,header=option)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    con = sqlite3.connect("trading.db")
    db = con.cursor()
    if request.method == "GET":
        # retrive all books
        db.execute("SELECT * FROM books WHERE amount <> ?;",(0,))
        columns = [column[0] for column in db.description]
        books = [dict(zip(columns, row)) for row in db.fetchall()]
        return render_template("buy.html", books=books)
    else:
        bookid = request.form.get("bookid")
        amount = request.form.get("amount")
        # check if user didn't write book id
        if not bookid:
            return render_template("invalid.html", placeholder="INVALID BOOK ID!")
        # check if user didn't write integer value
        try:
            bookid = int(bookid)
        except ValueError:
            return render_template("invalid.html", placeholder="INVALID BOOK ID!")
        # check if user didn't write amount
        if not amount:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # check if user didn't write integer values
        try:
            amount = int(amount)
        except ValueError:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # check if user didn't write value greater than 0
        if amount <= 0:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # retrive all books whose id = bookid
        db.execute("SELECT * FROM books WHERE id=?;", (bookid,))
        columns = [column[0] for column in db.description]
        book = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if amount less than number of books in the stock
        if int(amount) > int(book[0]["amount"]):
            return render_template(
                "invalid.html", placeholder="INSUFCIENT NUMBER OF BOOKS!"
            )
        # retrive all users whose id in the session
        user = db.execute("SELECT * FROM users WHERE id=?;", (session["user_id"],))
        # check if user's cash suffecient to buy this amount of books.
        if int(user[0]["cash"]) < int(book[0]["price"]) * amount:
            return render_template("invalid.html", placeholder="INSUFCIENT CASH!")
        # update user cash after puchasing this amount of book.
        db.execute(
            "UPDATE users SET cash=? WHERE id=?;",
            (int(user[0]["cash"]) - int(book[0]["price"]) * amount,
            session["user_id"],
            ))
        # retrive data of the owner of the book
        db.execute("SELECT * FROM users WHERE id=?;", (1,))
        columns = [column[0] for column in db.description]
        owner = [dict(zip(columns, row)) for row in db.fetchall()]
        # update the owner's cash to add tatal after buying books
        db.execute(
            "UPDATE users SET cash=? WHERE id=?;",(
            int(owner[0]["cash"]) + int(book[0]["price"]) * amount,
            owner[0]["id"],
            ))
        # update the amount of the book after selling it.
        db.execute(
            "UPDATE books SET amount=? WHERE id=?;",(
            int(book[0]["amount"]) - amount,
            bookid,
            ))
        # add transaction after completing the purchase
        datetime = strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO purchase(user_id,bookname,amount,datetime,bookprice,total) VALUES(?,?,?,?,?,?)",
            (session["user_id"],
            book[0]["name"],
            amount,
            datetime,
            book[0]["price"],
            amount * book[0]["price"],
            ))
        con.commit()
        db.close()
        con.close()
        flash("purchase done successfully")
        return redirect("/")

@app.route("/purchase/<book_id>",methods=["GET","POST"])
@login_required
def purchase(book_id):
    if request.method=="GET":
        url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'
        response = requests.get(url)
        book = response.json()
        return render_template('purchase.html', book=book)
    else:
        address=request.form.get('address')
        phone_number=request.form.get('phone_number')
        amount=request.form.get('amount')
        # connect to database
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute("SELECT * FROM users WHERE id=?;",(session['user_id'],))
        columns = [column[0] for column in db.description]
        user = [dict(zip(columns, row)) for row in db.fetchall()]
        db.execute("UPDATE users SET address=? AND phone_number=? WHERE id=?;",(address,phone_number,session['user_id'],))
        # check if user didn't write amount
        if not amount:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # check if user didn't write integer values
        try:
            amount = int(amount)
        except ValueError:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # check if user didn't write value greater than 0
        if amount <= 0:
            return render_template(
                "invalid.html", placeholder="INVALID NUMBER OF BOOKS!"
            )
        # retrive all books whose id = bookid
        db.execute("SELECT *,SUM(amount) as all_amount FROM books WHERE google_id=?;", (book_id,))
        columns = [column[0] for column in db.description]
        book = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if amount less than number of books in the stock
        print(book[0]["all_amount"])
        print(amount)
        if int(amount) > int(book[0]["all_amount"]):
            return render_template(
                "invalid.html", placeholder="INSUFCIENT NUMBER OF BOOKS!"
            )
        # retrive all users whose id in the session
        db.execute("SELECT * FROM users WHERE id=?;", (session["user_id"],))
        columns = [column[0] for column in db.description]
        user = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if user's cash suffecient to buy this amount of books.
        if int(user[0]["cash"]) < int(book[0]["price"]) * amount:
            return render_template("invalid.html", placeholder="INSUFCIENT CASH!")
        # update user cash after puchasing this amount of book.
        db.execute(
            "UPDATE users SET cash=? WHERE id=?;",(
            int(user[0]["cash"]) - int(book[0]["price"]) * amount,
            session["user_id"],
            ))
        db.execute("SELECT * FROM users WHERE isadmin=?;",(1,))
        columns = [column[0] for column in db.description]
        admin = [dict(zip(columns, row)) for row in db.fetchall()]
        # update the owner's cash to add tatal after buying books
        db.execute(
            "UPDATE users SET cash=? WHERE username=?;",
            (int(admin[0]["cash"]) + int(book[0]["price"]) * amount,
            admin[0]["id"],)
        )
        # update the amount of the book after selling it.
        db.execute(
            "UPDATE books SET amount=? WHERE google_id=?;",
            (int(book[0]["all_amount"]) - amount,
            book_id,)
        )
        # add transaction after completing the purchase
        datetime = strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO purchase(user_id,bookname,amount,datetime,bookprice,total) VALUES(?,?,?,?,?,?)",
            (session["user_id"],
            book[0]["name"],
            amount,
            datetime,
            book[0]["price"],
            amount * book[0]["price"],)
        )
        con.commit()
        db.close()
        con.close()
        flash("purchase done successfully")
        return redirect("/")




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        """Ensure username was submitted"""
        if not request.form.get("username"):
            return render_template("invalid.html", placeholder="must provide username")
        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("invalid.html", placeholder="must provide password")
        # Query database for username
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        # convert retrived data into list of dictionaries
        columns = [column[0] for column in db.description]
        rows = [dict(zip(columns, row)) for row in db.fetchall()]
        # Ensure username exists and password is correct

        if len(rows) != 1:
            return render_template(
                "invalid.html", placeholder="invalid username and/or password"
            )
        print(rows)
        if rows[0]["password"] != request.form.get("password"):
            return render_template(
                "invalid.html", placeholder="invalid username and/or password"
            )
        con.commit()
        db.close()
        con.close()
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        # retrive username from register form
        username = request.form.get("username")

        # retrive password from register form
        password = request.form.get("password")

        # retrive confirm from register form
        confirm = request.form.get("confirm")

        # check if user provide valid username
        if not username:
            return render_template("invalid.html", placeholder="INVALID USERNAME!")

        # check if user provide valid password
        if not password:
            return render_template("invalid.html", placeholder="INVALID PASSWORD!")

        # check if user provide valid confirm
        if not confirm:
            return render_template(
                "invalid.html", placeholder="INVALID CONFIRM PASSWORD!"
            )

        # check if password equals the confirmation password
        if password != confirm:
            return render_template(
                "invalid.html", placeholder="confirmation doesn't match password!"
            )

        # retrive all users from database
        con=sqlite3.connect("trading.db")
        db=con.cursor()
        db.execute("SELECT * FROM users WHERE username=?;", (username,))
        columns = [column[0] for column in db.description]
        users = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if username registered before
        if len(users) >= 1:
            return render_template("invalid.html", placeholder="USERNAME EXISTS")

        # after validating all conditions insert new user into database
        print("inserting new user")
        db.execute(
            "INSERT INTO users(username,password) VALUES(?,?);", (username, password,)
        )

        # retrive new user id from database
        db.execute("SELECT * FROM users WHERE username=?", (username,))
        columns = [column[0] for column in db.description]
        registrant = [dict(zip(columns, row)) for row in db.fetchall()]
        # add user id to session
        session["user_id"] = registrant[0]["id"]
        con.commit()
        db.close()
        con.close()
        # redirect to the main page
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # sell books
    if request.method == "GET":
        # sent him sell page
        return render_template("sell.html")

    else:
        # retrive bookname from sell form
        bookname = request.form.get("bookname")

        # retrive author from sell form
        author = request.form.get("author")

        # retrive price from sell form
        price = request.form.get("price")

        # retrive amount from sell form
        amount = request.form.get("amount")

        # insert new book into database
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute(
            "INSERT INTO books(name,author,price,amount,owner) VALUES(?,?,?,?,?);",
            (bookname,
            author,
            price,
            amount,
            session["user_id"],)
        )
        con.commit()
        db.close()
        con.close()
        # pop up message
        flash("Books Added Successfully")

        # redirect to the main page
        return redirect("/")


@app.route("/password", methods=["GET", "POST"])
def password():
    # change password
    if request.method == "POST":

        # retrive username from password form
        username = request.form.get("username")

        # retrive old password from password form
        oldpassword = request.form.get("old_password")

        # retrive new password from password form
        newpassword = request.form.get("new_password")

        # retrive confirmation password from password form
        confirm = request.form.get("confirm")

        # check if user provide valid username
        if not username:
            return render_template(
                "invalid.html", placeholder="PLEASE PROVIDE USERNAME!"
            )

        # check if user provide valid old password
        if not oldpassword:
            return render_template(
                "invalid.html", placeholder="PLEASE PROVIDE PASSWORD!"
            )

        # check if user provide valid new password
        if not newpassword:
            return render_template(
                "invalid.html", placeholder="PLEASE ENTER NEW PASSWORD!"
            )

        # check if user provide valid confirmation password
        if not confirm:
            return render_template("invalid.html", placeholder="INVALID CONFIRM!")

        # check if new password matches confirmation password
        if newpassword != confirm:
            return render_template(
                "invalid.html", placeholder="INVALID PASSWORD OR CONFIRM!"
            )
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        # retrive all users whose username matches username that user provide
        db.execute("SELECT * FROM users WHERE username=?;", (username,))
        columns = [column[0] for column in db.description]
        user = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if user exits in the database
        if len(user) == 0:
            return render_template(
                "invalid.html", placeholder="YOUR ARE NOT REGISTERD!"
            )

        # check if user's old password matches username password
        if user[0]["password"] != oldpassword:
            return render_template(
                "invalid.html",
                placeholder="INVALID OLD PASSWORD, PLEASE PROVIDE CORRECT PASSWORD!",
            )

        # update user's password with new password
        con=sqlite3.connect("trading.db")
        db=con.cursor()
        db.execute(
            "UPDATE users SET password=? WHERE username=?;", (newpassword, username,)
        )
        con.commit()
        db.close()
        con.close()
        # pop up message to inform user that password updated
        flash("Your Password Changed Successfuly.")

        return render_template("login.html")
    else:
        return render_template("password.html")


@app.route("/account")
@login_required
def account():
    # retrive all current user data form database
    con = sqlite3.connect("trading.db")
    db = con.cursor()
    db.execute("SELECT * FROM users WHERE id=?;", (session["user_id"],))
    columns = [column[0] for column in db.description]
    user = [dict(zip(columns, row)) for row in db.fetchall()]
    # retrive all books matches that this user is the owner to it
    #rows = db.execute("SELECT * FROM books WHERE owner=?;", session["user_id"])
    db.execute(
            "SELECT * FROM purchase WHERE user_id=?;", (session["user_id"],)
        )
    columns = [column[0] for column in db.description]
    rows = [dict(zip(columns, row)) for row in db.fetchall()]
    con.commit()
    db.close()
    con.close()
    return render_template("account.html", user=user[0], rows=rows)


@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash():
    if request.method == "GET":
        return render_template("charge.html")
    else:
        # retrive username from charge form
        username = request.form.get("username")

        # retrive cash from charge form
        cash = request.form.get("cash")

        # retrive visa from charge form
        visa = request.form.get("visa")

        # check if user provide valid username
        if not username:
            flash("Invalid Username!")
            return redirect("/cash")
        # check if user provide valid cash
        if not cash:
            flash("Invalid cash")
            return redirect("/cash")
        # check if user provide valid visa
        if not visa:
            flash("please enter visa number")
            return redirect("/cash")
        # retrive all user's data from database
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute("SELECT * FROM users WHERE id=?;", (session["user_id"],))
        columns = [column[0] for column in db.description]
        user = [dict(zip(columns, row)) for row in db.fetchall()]
        # check if username matches user in the session
        if username != user[0]["username"]:
            flash("Invalid Username")
            return redirect("/cash")

        newcash = user[0]["cash"] + int(cash)
        # update new cash in users table
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute("UPDATE users SET cash=? WHERE id=?;", (cash, session["user_id"],))
        con.commit()
        db.close()
        con.close()
        flash("Your Balance Charged Successfully")
        return redirect("/")


@app.route("/trading")
@login_required
def trade():
    con = sqlite3.connect("trading.db")
    db = con.cursor()
    db.execute("SELECT * FROM purchase;")
    columns = [column[0] for column in db.description]
    rows = [dict(zip(columns, row)) for row in db.fetchall()]
    con.commit()
    db.close()
    con.close()
    return render_template("trade.html", rows=rows)


@app.route('/books',methods=['GET','POST'])
def search_books():
    if request.method=="GET":
        return render_template("books.html",data=[])
    else:
        title = request.form.get('title')
        if not title:
            return 'Please provide a book title'

        url = f'https://www.googleapis.com/books/v1/volumes?q={title}&keys:key=AIzaSyAL46FdWUJnKPTP9_yeYRD6IzkqpvMSjvE'
        response = requests.get(url)
        data = response.json()
        if data is None:
            flash('books title not found')
            return redirect("/books")
        else:
            return render_template('books.html',data=data,header=title)


@app.route('/book/<book_id>')
def book_detail(book_id):
    url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'
    response = requests.get(url)
    book = response.json()
    return render_template('book_detail.html', book=book)



@app.route("/add",methods=["GET","POST"])
@login_required
def add():
    if request.method=="GET":
        return render_template("add.html",data=[])
    else:
        title = request.form.get('title')
        if not title:
            return 'Please provide a book title'

        url = f'https://www.googleapis.com/books/v1/volumes?q={title}&keys:key=AIzaSyAL46FdWUJnKPTP9_yeYRD6IzkqpvMSjvE'
        response = requests.get(url)
        data = response.json()
        if data is None:
            flash('books title not found')
            return redirect("/add")
        else:
            return render_template('add.html',data=data)


@app.route('/newbook/<book_id>',methods=["GET","POST"])
def newbook_detail(book_id):
    if request.method=="GET":
        url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'
        response = requests.get(url)
        book = response.json()
        return render_template('newbook_detail.html', book=book)
    else:
        url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'
        response = requests.get(url)
        book = response.json()
        # retrive bookname from sell form
        bookname = book["volumeInfo"]["title"]
        print(bookname)
        # retrive author from sell form
        author="NOT FOUND"
        if 'authors' in book['volumeInfo']:
            author=book['volumeInfo']['authors'][0]
        # retrive price from sell form
        price = request.form.get("price")

        # retrive amount from sell form
        amount = request.form.get("amount")
        price= int(price)
        amount=int(amount)
        print(price)
        print(amount)
        # insert new book into database
        con = sqlite3.connect("trading.db")
        db = con.cursor()
        db.execute(
            "INSERT INTO books(name,author,price,amount,google_id) VALUES(?,?,?,?,?);",
            (bookname,
            author,
            price,
            amount,
            book_id,)
        )
        con.commit()
        db.close()
        con.close()
        # pop up message
        flash("Books Added Successfully")

        # redirect to the main page
        return redirect("/")
    
if __name__ == "__main__":
    app.run()