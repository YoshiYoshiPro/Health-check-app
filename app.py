import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded 必要？
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)　必要？
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# sqliteを辞書型に変換
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# 体温報告画面
@app.route("/")
@login_required
def index():

    """
    # ログイン状態の確認
    if not session:
        redirect("/login")
    """
    return render_template("input.html")

# ログイン画面
@app.route("/login", methods=["GET", "POST"])
def login():

    # user_id(セッション) をリセット
    session.clear()

    # POST経由の場合
    if request.method == "POST":

        # ユーザー名が空ではないことを確認する
        userid = request.form.get("userid")
        if not userid:
            return apology("login.html", "ユーザーIDを入力してください")

        # パスワードが空ではないことを確認する
        elif not request.form.get("password"):
            return apology("login.html", "パスワードを入力して下さい")

        # データベース接続処理　CS50を使わないバージョン
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

         # データベースにユーザー名があるかどうか確認する
        cur.execute("SELECT * FROM users WHERE id_user = ?", (userid,))
        rows = cur.fetchall()

        # ユーザー名が存在し、次はパスワードが正しいか確認する。
        if len(rows) != 1 or not check_password_hash(rows["hash"], request.form.get("password")):
            # ファイルを閉じる
            conn.close()
            return apology("login.html", "ユーザー名またはパスワードが間違っております。")

        # ログインしたユーザーを記憶する
        session["user_id"] = rows["username"]
        # ファイルを閉じる
        conn.close()
        # ユーザーを体温報告ページに移動させる。
        return redirect("/")

    # GET経由ならログイン画面を表示させる
    else:
        return render_template("login.html")


# ログアウト
@app.route("/logout")
def logout():

    # user_id をリセット
    session.clear()

    # ログインホームへ移動
    return redirect("/")


# 登録画面
@app.route("/register", methods=["GET", "POST"])
def register():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        # グループIDが空ではないことを確認
        groupid = request.form.get('groupid')
        if not groupid:
            return apology("register.html", "団体IDを入力してください")

        # ユーザーIDが空ではないことを確認
        userid = request.form.get('userid')
        if not userid:
            return apology("register.html", "ユーザーIDを入力してください")

        # 名前が空ではないことを確認
        username = request.form.get('username')
        if not username:
            return apology("register.html", "名前を入力してください")

        # パスワードが空ではないことを確認
        password = request.form.get('password')
        if not password:
            return apology("register.html", "パスワードを入力してください")

        # 確認パスワードが空ではないか確認
        confirmation = request.form.get('confirmation')
        if not confirmation:
            return apology("register.html", "確認パスワードを入力してください")

        # ユーザーIDがかぶってないか確認。
        check = db.execute("SELECT username FROM users WHERE username = ?", username)
        if check:
            return apology("Username is already in use")

        #パスワードと確認パスワードがかぶってないか確認
        if not password == confirmation:
            return apology("invalid username and/or password")
        password_hash = generate_password_hash(password, method="sha256")

        # データベースに登録
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, password_hash)
        # リダイレクトでログイン画面に移動
        return redirect("/login")

    # getの場合は登録画面になります。
    else:
        return render_template("register.html")
