from flask import Flask, flash, redirect, render_template, session

app = Flask(__name__)

@app.route("/")
def index():
    
    """
    # ログイン状態の確認
    if not session:
        redirect("/login")
    """

    return render_template("input.html")