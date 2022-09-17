import os

import sqlite3
import random
import string
from flask import Flask, flash, redirect, render_template, url_for, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from datetime import datetime


from helpers import apology, login_required, admin_required

app = Flask(__name__)

# Ensure templates are auto-reloaded 必要？
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies) 必要？
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# グループIDを生成する関数（頭文字1文字と数字5桁）
def id_generator():
    text = f'{random.randrange(1, 10**5):05}'
    uppercase_list = random.sample(string.ascii_uppercase, 1)

    # リスト型 → str型
    uppercase = ''.join(uppercase_list)

    # 文字と数字を連結
    text = uppercase + text

    return text

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# 取り出したSQliteデータを辞書型に変換
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# 入力の空欄チェック
def input_check(inputtext, html, message):
    if not inputtext:
        return apology(html, message)


# 体温報告画面
@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    if request.method == "POST":
        # データベースに接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # 体温を取得
        temperature = request.form.get("body_temperature")

        # 備考を取得
        memo = request.form.get("memo")

        # 体温、備考情報を記録テーブルに挿入
        cur.execute("INSERT INTO logs(user_id,temperature,memo,datetime) VALUES (?,?,?,?)",
                        (session["user_id"], temperature, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        cur.execute("SELECT log_id FROM logs ORDER BY log_id DESC LIMIT 1")
        i = cur.fetchall()
        log_id = i[0]["log_id"]

        # 頭痛の有無を取得
        headache = request.form.get("headache")
        if headache == "ある":
            headache = 1
        else:
            headache = 0

        # 咳の有無を取得
        cough = request.form.get("cough")
        if cough == "ある":
            cough = 1
        else:
            cough = 0

        # 倦怠感の有無を取得
        fatigue = request.form.get("stuffiness")
        if fatigue == "ある":
            fatigue = 1
        else:
            fatigue = 0

        # 異常を取得
        abnormal = request.form.get("taste_smell_abnormal")
        if abnormal == "ある":
            abnormal = 1
        else:
            abnormal = 0

        # 鼻づまりの有無を取得
        runny = request.form.get("runny_nose")
        if runny == "ある":
            runny = 1
        else:
            runny = 0

        # 記録詳細テーブルに挿入
        cur.execute("INSERT INTO log_details(log_id,user_id,headache,cough,fatigue,abnormal,runny) VALUES (?,?,?,?,?,?,?)",
                   (log_id, session["user_id"], int(headache), int(cough), int(fatigue), int(abnormal), int(runny),))

        conn.commit()
        conn.close()

        return redirect("/mypage")

    else:
        # ログイン状態の確認
        if not session:
            redirect("/login")
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
        input_check(userid,"login.html", "ユーザーIDを入力してください")

        # パスワードが空ではないことを確認する
        input_check(request.form.get("password"), "login.html", "パスワードを入力して下さい")

        # データベース接続処理
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # データベースにユーザー名があるかどうか確認する
        cur.execute("SELECT * FROM users WHERE user_id = ?", (userid,))
        rows = cur.fetchall()

        # ユーザー名が存在し、次はパスワードが正しいか確認する。
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            # ファイルを閉じる
            conn.close()
            return apology("login.html", "ユーザー名またはパスワードが間違っております。")

        # ログインしたユーザーを記憶する
        session["user_id"] = rows[0]["user_id"]
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


# アカウント登録画面
@app.route("/register", methods=["GET", "POST"])
def register():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        userid = request.form.get('userid')
        input_check(userid,"register.html", "ユーザーIDを入力してください")

        username = request.form.get('username')
        input_check(username, "register.html", "名前を入力してください")

        password = request.form.get('password')
        input_check(password, "register.html", "パスワードを入力してください")

        confirmation = request.form.get('confirmation')
        input_check(confirmation, "register.html", "確認パスワードを入力してください")

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # ユーザーIDがかぶってないか確認。
        cur.execute("SELECT user_id FROM users WHERE user_id = ?", (userid,))
        rows = cur.fetchall()
        if rows:
            conn.close()
            return apology("register.html", "入力されたユーザーIDは既に登録済みです。")

        #パスワードと確認パスワードが同じかどうか確認
        if not password == confirmation:
            conn.close()
            return apology("register.html", "パスワードが一致しません")
        password_hash = generate_password_hash(password, method="sha256")

        # データベースに登録
        newdata = (userid, username, password_hash, 1)
        cur.execute("INSERT INTO users (user_id, username, hash, role) VALUES(?, ?, ?, ?)", (newdata))
        conn.commit()
        conn.close()

        # リダイレクトでログイン画面に移動
        return redirect("/login")

    # getの場合は登録画面になります。
    else:
        return render_template("register.html")

# グループ作成
@app.route("/groupcreate", methods=["GET", "POST"])
@login_required
def groupcreate():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        # 空欄チェック
        groupname = request.form.get('groupname')
        input_check(groupname, "groupcreate.html", "グループ名を入力してください")

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()
        groupid = "0"

        # グループIDがかぶらないようにIDを生成するループ処理
        while True:
            # グループIDを生成
            groupid = id_generator()

            # 一致するグループIDがあるか確認
            cur.execute("SELECT group_id FROM groups_test WHERE group_id = ?", (groupid,))
            groupid_check = cur.fetchall()

            # グループIDが重複していない場合
            if not groupid_check:
                break

            # グループIDが重複している場合
            else:
                continue

        # データベースに登録
        newdata = (groupid, groupname,)
        cur.execute("INSERT INTO groups_test (group_id, group_name) VALUES(?, ?)", newdata)

        # グループに追加した人のロールを1(管理者)とする
        cur.execute("UPDATE users SET role = 1 WHERE user_id = ?",(session["user_id"],))
        conn.commit()
        conn.close()

        # 団体ID表示画面へ移動
        return render_template("group_id.html", groupid = groupid)

    # getの場合は作成画面になります。
    else:
        return render_template("groupcreate.html")

# グループ参加
@app.route("/groupadd", methods=["GET", "POST"])
@login_required
def groupadd():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        # 空欄チェック
        groupid = request.form.get('groupid')
        input_check(groupid, "groupadd.html", "グループIDを入力してください")

        # データベース接続処理
        conn = sqlite3.connect("health.db")
        cur = conn.cursor()

        # データベースにグループ名とIDがあるかどうか確認
        cur.execute("SELECT group_id FROM groups_test WHERE group_id = ?", (groupid,))
        rows = cur.fetchall()
        if rows:
            conn.close()
            return apology("groupadd.html", "グループIDが間違っております。")

        # ユーザーIDにグループIDを追加する
        cur.execute("UPDATE users SET group_id = ? WHERE user_id = ?",(groupid,),(session["user_id"],))
        conn.commit()
        conn.close()

        # ユーザーを体温報告ページに移動させる。
        return redirect("/")

    # GET経由ならログイン画面を表示させる
    else:
        return render_template("adminreg.html")

# 管理者ID表示
@app.route("/adminid")
@admin_required
def adminid():

    # データベース接続
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    groupid = cur.execute("SELECT group_id FROM groups WHERE group_id = ?", (session["group_id"],))

    return render_template("admin_html", groupid=groupid)


# 管理ページ
@app.route("/adminhome")
@admin_required
def adminhome():

    return render_template("adminhome.html")

# グループID通知画面
@app.route("/groupid")
@admin_required
def groupId():

    # データベースに接続
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # グループIDがかぶらないようにIDを生成するループ処理
    while True:
        # グループIDを生成
        groupid = id_generator()

        # 一致するグループIDがあるか確認
        groupid_check = cur.execute("SELECT group_id FROM groups WHERE group_id = ?", groupid)

        # グループIDが重複していない場合
        if groupid_check is None:
            break

        # グループIDが重複している場合
        else:
            continue

    return render_template("group_id.html", groupid=groupid)

@app.route("/mypage")
@login_required
def mypage():

    # データベースに接続
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # ユーザーIDの取得
    user_id = cur.execute("SELECT user_id FROM users WHERE user_id = ?", (session["user_id"],))

    # 記録の詳細を取得
    details = cur.execute("SELECT * FROM log_details WHERE user_id = ?", (session["user_id"],))

    # 記録を取得
    logs = cur.execute("SELECT * FROM logs WHERE user_id = ?", (session["user_id"],))

    # 記録テーブルと記録詳細テーブルを結合
    cur.execute("SELECT * FROM logs INNER JOIN log_details ON logs.log_id = log_details.log_id AND log_details.user_id = ?", (session["user_id"],))
    all = cur.fetchall()

    # 頭痛の有無を判別、書き換え
    for i in all:
            if i["headache"] == 1:
                i["headache"] = "有"
            else:
                i["headache"] = "無"

    # 咳の有無を判別、書き換え
    for i in all:
            if i["cough"] == 1:
                i["cough"] = "有"
            else:
                i["cough"] = "無"

    # 倦怠感の有無を判別、書き換え
    for i in all:
            if i["fatigue"] == 1:
                i["fatigue"] = "有"
            else:
                i["fatigue"] = "無"

    # 味覚・嗅覚の異常の有無を判別、書き換え
    for i in all:
            if i["abnormal"] == 1:
                i["abnormal"] = "有"
            else:
                i["abnormal"] = "無"

    # 咳の有無を判別、書き換え
    for i in all:
            if i["runny"] == 1:
                i["runny"] = "有"
            else:
                i["runny"] = "無"

    return render_template("mypage.html", details=details, logs=logs, all=all)


