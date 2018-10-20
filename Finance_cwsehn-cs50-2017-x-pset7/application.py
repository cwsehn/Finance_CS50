from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
check_list = []


@app.route("/")
@login_required
def index():
    # query transactions table from db...."ORDER BY symbol" is critical for execution of the "while loop" that follows...
    rows = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = :user_id ORDER BY symbol", user_id=session["user_id"])
    i = 0
    stocks = {}
    stock_list = []
    price = 0
    value = 0
    name = ''
    while True:
        try:
            try:
                # if the stock has been purchased on more than one occassion...ie. occupies more than one row in db....
                # this try block will execute to update total shares.....otherwise += operation will cause exception...
                stocks[rows[i]["symbol"]] += int(rows[i]["shares"])
                stock_list.remove(stock_list[-1])
                new_tup = (rows[i]["symbol"], stocks[rows[i]["symbol"]] , price, stocks[rows[i]["symbol"]] * price, name, usd(price),
                          usd(stocks[rows[i]["symbol"]] * price) )
                stock_list.append(new_tup)
                i += 1
    
            except KeyError:
                stocks[rows[i]["symbol"]] = int(rows[i]["shares"])
                quote = lookup(rows[i]["symbol"])
                price = quote["price"]
                name = quote["name"]
                new_tup = (rows[i]["symbol"], int(rows[i]["shares"]), price, (int(rows[i]["shares"]) * price), name, usd(price),
                          usd(int(rows[i]["shares"]) * price) )
                stock_list.append(new_tup)
                i += 1
                
        except IndexError:
            break
    
    # calculate total stock value and format value to US Dollars
    for member in stock_list:
        value += (member[3])
    
    # query user db for current cash on-hand...
    bank = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    cash = bank[0]["cash"]
    
    Tot_Val = value + cash 
    value = usd(value)
    cash = usd(cash)
    Tot_Val = usd(Tot_Val)
    return render_template("index.html", stock_list = stock_list, value = value, cash = cash, Tot_Val = Tot_Val )

 

@app.route("/double_check", methods=["GET", "POST"])
@login_required
def double_check():
    if request.method == "POST":
        
        
        if request.form.get("confirm"):

            rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
            name = check_list[0][0]
            price = check_list[0][1]
            symbol = check_list[0][2]
            shares = check_list[0][3]
            purchase = 1
    
            new_row = db.execute("INSERT INTO transactions (user_id, symbol, shares) VALUES (:user_id, :symbol, :shares)",
            user_id=session["user_id"], symbol=symbol, shares=shares)
            record_row = db.execute("INSERT INTO sold (user_id, symbol, shares, price, purchase) VALUES (:user_id, :symbol, :shares, :price, :purchase)",
            user_id=session["user_id"], symbol=symbol, shares=shares , price=price, purchase=purchase )
            
            cash = rows[0]["cash"] - (shares * price)
            withdrawl = db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id=session["user_id"])
        
            check_list.clear()
            return redirect(url_for("history"))
    
        else:
            check_list.clear()
            return redirect(url_for("index"))
    elif check_list == []:
        return redirect(url_for("index"))
    else:    
        return render_template("double_check.html", name=check_list[0][0], price=check_list[0][1], symbol=check_list[0][2],
               shares=check_list[0][3], cash=check_list[0][4], cost=check_list[0][5])
        

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        check_list.clear()
        # ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("invalid symbol")
        
        buy_symbol = request.form.get("symbol")    
        
        if not buy_symbol.isalpha():
            return apology("invalid symbol entry please...no extraneous punctuation...")
            
        # ensure shares were submitted
        if not request.form.get("shares"):
            return apology("invalid shares")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("invalid shares")
        if shares < 1:
            return apology("invalid shares")
        
        try:    
            quote = lookup(buy_symbol)
        except TypeError:
            return apology("invalid symbol request")
        if quote:
            symbol = quote["symbol"]
            name = quote["name"]
            price = quote["price"]
        
        else:
            return apology("invalid symbol ... try again")
            
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]
        cost = shares * price
        if cost <= cash:
            
            checkers = [name, price, symbol, shares, usd(cash), usd(cost)]
            check_list.append(checkers)
            return redirect(url_for("double_check"))
            
        elif  cost > cash:
            return apology("insufficient funds")
            
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    
    buy_rows = db.execute("SELECT symbol, shares, price, date, purchase FROM sold WHERE user_id = :user_id ORDER BY date",
               user_id=session["user_id"])
    
    buy_list = []
    i = 0
    while True:
        try:
            buy_tup = (buy_rows[i]["symbol"], buy_rows[i]["shares"], buy_rows[i]["price"], buy_rows[i]["date"], buy_rows[i]["purchase"])
            buy_list.append(buy_tup)
            i += 1
        except IndexError:
            break
    
    return render_template("history.html", buy_list = buy_list)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # ensure symbol was submitted properly
        if not request.form.get("symbol"):
            return apology("re-select quote and enter a stock symbol")
            
        quote_symbol = request.form.get("symbol")
        if not quote_symbol.isalpha():
            return apology("invalid symbol entry...no quote marks in your 'quote' request please...")
        
        # call function from helpers.py    
        quote = lookup(quote_symbol)
        
        if not quote:
            return apology("invalid symbol")
            
        return render_template("quoted.html", name = quote["name"], symbol = quote["symbol"], price = quote["price"])
        
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
            
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
            
        elif not request.form.get("password_confirm"):
            return apology("must confirm password")
            
        elif request.form.get("password_confirm") != request.form.get("password"):
            return apology("passwords don't match")
           
        # hash password
        hash = pwd_context.encrypt(request.form.get("password"))
        
        # check for unique user
        new_row = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash = hash)
        if not new_row:
            return apology("username is taken")
            
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        
        session["user_id"] = rows[0]["id"]
        return redirect(url_for("index"))
    else:        
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure symbol was submitted properly
        if not request.form.get("symbol"):
            return apology("invalid symbol")
            
        symbol = request.form.get("symbol")
        if not symbol.isalpha():
            return apology("invalid symbol entry...")
            
        # ensure shares were submitted properly
        if not request.form.get("shares"):
            return apology("invalid shares")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("invalid shares")
        if shares < 1:
            return apology("invalid shares")

        quote = lookup(symbol)

        if not quote:
            return apology("invalid symbol")
        # query dbs for pertinent info    
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        to_sell = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = :user_id AND symbol = :symbol ORDER BY shares DESC",
                  user_id=session["user_id"], symbol = symbol.upper())

        if not to_sell:
            return apology("You can't sell what you don't own!")
        else:
            sellers = 0
            sell_list = []
            i = 0
            while True:
                try:
                    sellers += to_sell[i]["shares"]
                    sell_list.append(to_sell[i]["shares"])
                    i += 1
                except IndexError:
                    sell_list.sort()
                    break
        if sellers < shares:
            return apology("You may sell up to {} shares of {}".format(sellers, symbol))
            
        price = quote["price"]
        cash = rows[0]["cash"] + (shares * price)
        deposit = db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id=session["user_id"])
        purchase = 0
        sold_row = db.execute("INSERT INTO sold (user_id, symbol, shares, price, purchase) VALUES (:user_id, :symbol, :shares, :price, :purchase)",
                   user_id=session["user_id"], symbol=symbol.upper(), shares=shares , price=price, purchase=purchase )
            
        while True:
            batch = sell_list.pop()
            if batch <= shares:
                shares = shares - batch
                
                new_row = db.execute("DELETE FROM transactions WHERE user_id = :user_id AND symbol = :symbol AND shares = :batch ORDER BY shares DESC LIMIT 1",
                          user_id=session["user_id"], symbol=symbol.upper(), batch=batch )
                          
                if shares == 0:
                    break
            elif shares != 0:
                batch = batch - shares
                new_row = db.execute("UPDATE transactions SET shares = :batch WHERE user_id = :user_id AND symbol = :symbol ORDER BY shares DESC LIMIT 1",
                          user_id=session["user_id"], symbol=symbol.upper(), batch=batch )
                break
            else:
                break
            
        return redirect(url_for("index"))
    else:
        return render_template("sell.html")
    
    
    
