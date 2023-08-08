import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import re

from helpers import apology, login_required, lookup, usd


app = Flask(__name__)


app.jinja_env.filters["usd"] = usd


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


db = SQL("sqlite:///finance.db")



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get the user ID from the session
    user_id = session["user_id"]

    # Get the user's cash balance
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)[0]
    cash_balance = user["cash"]

    # Get the user's stock portfolio
    portfolio = db.execute("SELECT * FROM portfolio WHERE user_id = ?", user_id)

    # Create a list to store the stock information
    stock_info = []

    # Loop through each stock in the portfolio
    for stock in portfolio:
        # Lookup the stock symbol to get the current price
        stock_data = lookup(stock["stock_symbol"])

        # Calculate the total value of the holding (shares times price)
        total_value = stock["shares"] * stock_data["price"]

        # Add the stock information to the list
        stock_info.append({
            "symbol": stock_data["symbol"],
            "name": stock_data["name"],
            "shares": stock["shares"],
            "price": stock_data["price"],
            "total_value": total_value
        })

    # Calculate the total value of all holdings
    total_value_stocks = sum(stock["total_value"] for stock in stock_info)

    # Calculate the grand total (stocks' total value plus cash)
    grand_total = total_value_stocks + cash_balance

    # Render the index template with the stock information and totals
    return render_template("index.html", stocks=stock_info, cash_balance=cash_balance, total_value_stocks=total_value_stocks, grand_total=grand_total)




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide stock symbol", 400)

        # Ensure shares were submitted
        shares = request.form.get("shares")
        if not shares:
            return apology("must provide number of shares", 400)

        try:
            shares = int(shares)
            if shares <= 0:
                raise ValueError
        except ValueError:
            return apology("number of shares must be a positive integer", 400)

        # Lookup the stock symbol
        stock = lookup(symbol)
        if stock is None:
            return apology("symbol does not exist", 400)

        # Calculate the total cost of the purchase
        total_cost = stock["price"] * shares

        # Check if the user can afford the purchase
        user_id = session["user_id"]
        user = db.execute("SELECT * FROM users WHERE id = ?", user_id)[0]
        if user["cash"] < total_cost:
            return apology("not enough cash to complete the purchase", 403)

        # Record the purchase in the operations table
        db.execute("INSERT INTO operations (user_id, stock_symbol, shares, operation_type, price) VALUES (?, ?, ?, ?, ?)",
                   user_id, symbol, shares, "buy", stock["price"])

        # Update the user's cash
        updated_cash = user["cash"] - total_cost
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        # Update the user's portfolio with the purchased stocks
        portfolio = db.execute("SELECT * FROM portfolio WHERE user_id = ? AND stock_symbol = ?", user_id, symbol)
        if len(portfolio) == 0:
            db.execute("INSERT INTO portfolio (user_id, stock_symbol, shares) VALUES (?, ?, ?)",
                       user_id, symbol, shares)
        else:
            db.execute("UPDATE portfolio SET shares = shares + ? WHERE user_id = ? AND stock_symbol = ?",
                       shares, user_id, symbol)

        # Redirect user to the home page
        return redirect("/")

    # If the request method is GET, display the buy form
    else:
        return render_template("buy.html")





@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget an user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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




@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide stock symbol", 400)

        # Lookup the stock symbol
        stock = lookup(symbol)
        if stock is None:
            return apology("symbol does not exist", 400)

        # Render the quoted template with the stock information
        return render_template("quoted.html", stock=stock)

    # If the request method is GET, display the quote form
    else:
        return render_template("quote.html")







@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        # Check if the username is already taken
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) > 0:
            return apology("username already taken", 400)

        # Generate a hash of the password
        hashed_password = generate_password_hash(request.form.get("password"))

        # Insert the new user into the users table
        result = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                            request.form.get("username"), hashed_password)

        # Check if the user was successfully added to the database
        if not result:
            return apology("error adding user to database", 500)

        # Log the user in by setting the session["user_id"] to the new user's ID
        session["user_id"] = result

        # Redirect user to the home page
        return redirect("/")

    # If the request method is GET, display the registration form
    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":
        stock_symbol = request.form.get("symbol")
        shares_to_sell = int(request.form.get("shares"))

        if not stock_symbol:
            return apology("must select a stock symbol", 400)

        if shares_to_sell <= 0:
            return apology("must input a positive integer for shares", 400)

        # Get user's portfolio to check if they own the stock
        portfolio = db.execute("SELECT * FROM portfolio WHERE user_id = ? AND stock_symbol = ?", user_id, stock_symbol)

        if not portfolio:
            return apology("you do not own any shares of this stock", 400)

        current_shares = portfolio[0]["shares"]
        if shares_to_sell > current_shares:
            return apology("you do not own enough shares to sell", 400)

        stock_data = lookup(stock_symbol)

        total_value = shares_to_sell * stock_data["price"]

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_value, user_id)

        new_shares = current_shares - shares_to_sell
        if new_shares == 0:
            db.execute("DELETE FROM portfolio WHERE user_id = ? AND stock_symbol = ?", user_id, stock_symbol)
        else:
            # Update the shares in the portfolio
            db.execute("UPDATE portfolio SET shares = ? WHERE user_id = ? AND stock_symbol = ?", new_shares, user_id, stock_symbol)

        # Add the sell transaction to the operations table
        db.execute("INSERT INTO operations (user_id, stock_symbol, shares, operation_type, price, money) VALUES (?, ?, ?, ?, ?, ?)",
                   user_id, stock_symbol, shares_to_sell, "SELL", stock_data["price"], total_value)

        return redirect("/")

    else:
        portfolio = db.execute("SELECT stock_symbol FROM portfolio WHERE user_id = ?", user_id)
        return render_template("sell.html", portfolio=portfolio)




def change_password():
    """Change user's password"""

    if request.method == "POST":
        # Check if current_password, new_password, and confirmation are provided
        if not request.form.get("current_password") or not request.form.get("new_password") or not request.form.get("confirmation"):
            return apology("Please provide all required fields.", 400)

        # Check if new passwords match
        if request.form.get("new_password") != request.form.get("confirmation"):
            return apology("New passwords must match.", 400)

        # Check if current password is correct
        user_id = session["user_id"]
        user = db.execute("SELECT * FROM users WHERE id = ?", user_id)[0]

        if not check_password_hash(user["hash"], request.form.get("current_password")):
            return apology("Current password is incorrect.", 403)

        # Hash the new password
        hashed_password = generate_password_hash(request.form.get("new_password"))

        # Update the user's password in the users table
        db.execute("UPDATE users SET hash = ? WHERE id = ?", hashed_password, user_id)

        return redirect("/")

    else:
        return render_template("change_password.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # Get the user ID from the session
    user_id = session["user_id"]

    # Fetch all the user's transactions from the operations table
    transactions = db.execute("SELECT * FROM operations WHERE user_id = ? ORDER BY time DESC", user_id)

    return render_template("history.html", transactions=transactions)
