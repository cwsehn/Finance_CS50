def index():
    rows = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = :user_id", user_id=session["user_id"])
    i = 0
    stocks = {}
    stock_price = {}
    stock_list = []
    while True:
        try:
            try:
                stocks[rows[i]["symbol"]] += int(rows[i]["shares"])
                stock_list.remove(stock_list[-1])
                new_tup = (rows[i]["symbol"], stocks[rows[i]["symbol"]] , quote["price"])
                stock_list.append(new_tup)
                i += 1
    
            except KeyError:
                
                stocks[rows[i]["symbol"]] = int(rows[i]["shares"])
                quote = lookup(rows[i]["symbol"])
                # stock_price[rows[i]["symbol"]] = quote["price"]
                new_tup = (rows[i]["symbol"], int(rows[i]["shares"]), quote["price"])
                stock_list.append(new_tup)
                i += 1
                
        except IndexError:
            break
    
    #d_list = [stocks, stock_price]        
    
    return render_template("index.html", stock_list = stock_list)
    
    
    
    
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("invalid symbol")
            
        # ensure shares were submitted
        if not request.form.get("shares"):
            return apology("invalid shares")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("invalid shares")
        if shares < 1:
            return apology("invalid shares")
            
        quote = lookup(request.form.get("symbol"))
        
        if not quote:
            return apology("invalid symbol")
            
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

        if (shares * quote["price"]) <= rows[0]["cash"]:
            new_row = db.execute("INSERT INTO transactions (user_id, symbol, shares, price, purchased) VALUES (:user_id, :symbol, :shares, :price, :purchased)",
            user_id=session["user_id"], symbol=quote["symbol"], shares=shares , price=quote["price"], purchased=shares )
            record_row = db.execute("INSERT INTO transactions (user_id, symbol, shares, price, purchased) VALUES (:user_id, :symbol, :shares, :price, :purchased)",
            user_id=session["user_id"], symbol=quote["symbol"], shares=shares , price=quote["price"], purchased=shares )
            
            cash = rows[0]["cash"] - (shares * quote["price"])
            withdrawl = db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id=session["user_id"])
            
            #buy_tup = (new_row[0]["symbol"], quote["name"], new_row[0]["purchased"], new_row[0]["price"], new_row[0]["date"])
            #buy_list.append(buy_tup)
            #render_template("history.html", buy_list = buy_list) 
        
        elif  (shares * quote["price"]) > rows[0]["cash"]:
            return apology("insufficient funds")
            
        return redirect(url_for("index"))
    else:
        return render_template("buy.html")
