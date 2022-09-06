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

        # 空欄チェック
        groupid = request.form.get('groupid')
        if not groupid:
            return apology("register.html", "団体IDを入力してください")

        userid = request.form.get('userid')
        if not userid:
            return apology("register.html", "ユーザーIDを入力してください")

        username = request.form.get('username')
        if not username:
            return apology("register.html", "名前を入力してください")

        password = request.form.get('password')
        if not password:
            return apology("register.html", "パスワードを入力してください")

        confirmation = request.form.get('confirmation')
        if not confirmation:
            return apology("register.html", "確認パスワードを入力してください")

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        #団体IDが既にあるかどうか
        check_group = cur.execute("SELECT group_id FROM groups WHERE group_id = ?", (groupid,))
        if not check_group:
            conn.close()
            return apology("register.html", "団体が存在しません")

        # ユーザーIDがかぶってないか確認。
        check_userid = cur.execute("SELECT id_user FROM users WHERE id_user = ?", (userid,))
        if check_userid:
            conn.close()
            return apology("register.html", "既に登録済みではありませんか?")

        #パスワードと確認パスワードがかぶってないか確認
        if not password == confirmation:
            conn.close()
            return apology("register.html", "パスワードが一致しません")
        password_hash = generate_password_hash(password, method="sha256")

        # データベースに登録 あとでもろもろ追加
        newdata = (userid, username, password_hash)
        cur.execute("INSERT INTO users (id_user, username, hash) VALUES(?, ?, ?)", (newdata))
        conn.commit()
        conn.close()

        # リダイレクトでログイン画面に移動
        return redirect("/login")

    # getの場合は登録画面になります。
    else:
        return render_template("register.html")

# 管理者ログイン
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    # セッションをリセット
    session.clear()

    # POST経由の場合
    if request.method == "POST":

        # ユーザー名が空ではないことを確認する
        groupid = request.form.get("groupid")
        if not groupid:
            return apology("admin_login.html", "団体IDを入力してください")

        # パスワードが空ではないことを確認する
        elif not request.form.get("password"):
            return apology("admin_login.html", "パスワードを入力してください")

        # データベース接続処理　CS50を使わないバージョン
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

         # データベースに団体名があるかどうか確認する
        cur.execute("SELECT * groups FROM group_id WHERE group_id = ?", (groupid,))
        rows = cur.fetchall()

        # 団体が存在し、パスワードが正しいか確認する。
        if len(rows) != 1 or not check_password_hash(rows["group_password"], request.form.get("password")):
            # ファイルを閉じる
            conn.close()
            return apology("admin_login.html", "団体IDまたはパスワードが間違っております。")

        # ログインした団体名を記憶する
        session["group_id"] = rows["group_id"]
        # ファイルを閉じる
        conn.close()

        # ログイン者を管理ページに移動させる。
        return redirect("/admin_home")

    # GET経由ならログイン画面を表示させる
    else:
        return render_template("admin_login.html")

# グループ作成
@app.route("/admin_reg", methods=["GET", "POST"])
def admin_reg():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        # 空欄チェック
        groupname = request.form.get('groupname')
        if not groupname:
            return apology("admin_reg.html", "団体名を入力してください")

        password = request.form.get('password')
        if not password:
            return apology("admin_reg.html", "パスワードを入力してください")

        confirmation = request.form.get('confirmation')
        if not confirmation:
            return apology("admin_reg.html", "確認パスワードを入力してください")

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        #パスワードと確認パスワードがかぶってないか確認
        if not password == confirmation:
            conn.close()
            return apology("admin_reg.html", "パスワードが一致しません")
        password_hash = generate_password_hash(password, method="sha256")

        # データベースに登録 あとでもろもろ追加
        newdata = (groupname, password_hash)
        cur.execute("INSERT INTO groups (group_name, group_password) VALUES(?, ?)", (newdata))
        session["group_id"] = rows["group_id"]
        conn.commit()
        conn.close()

        # リダイレクトで団体IDを表示
        return redirect("/adminid")

    # getの場合は登録画面になります。
    else:
        return render_template("admin_reg.html")

# 管理者ID表示
@app.route("/adminid")
def adminid():

    # データベース接続
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    groupid = cur.execute("SELECT group_id FROM groups WHERE group_id = ?", (session["group_id"],))

    return render_template("admin_html", groupid=groupid)


# 管理ページ
@app.route("/admin_home")
@login_required
def admin_home():

    return render_template("admin_home.html")