import os

import sqlite3
import random
import string
from flask import Flask, flash, redirect, render_template, url_for, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime


from helpers import apology, login_required

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
@app.route("/")
@login_required
def index():

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
        newdata = (userid, username, password_hash,)
        cur.execute("INSERT INTO users (user_id, username, hash) VALUES(?, ?, ?)", (newdata))
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
<<<<<<< HEAD
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
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # 権限を確認 dbのカラムを仮で「role」としています、role内も0を一般、1を管理者と仮定して作成しています
    user_id = session["user_id"]
    cur.execute("SELECT role FROM users WHERE user_id = ?;", (user_id,))
    role = cur.fetchall()

    if role[0]["role"] == 1:
        # 日付の取得
        date = datetime.date.today()
        today = "{0:%Y/%m/%d}".format(date)
        date = str(date)

        # 発熱の閾値設定
        temperature = 37.5

        # 確認用(仮データの日付) 発熱者、体調不良者、未記入者のデータベースのdate変数を変えてください
        sample = "2022-09-11"

        # 発熱者
        cur.execute("SELECT users.user_name, records.body_temperature FROM records INNER JOIN users ON records.user_id = users.user_id WHERE (records.record_date = ?) and (records.body_temperature >= ?);", (sample, temperature))
        fevers = cur.fetchall()
        # 体調不良者
        # bad = cur.execute("SELECT users.user_name, FROM records INNER JOIN users ON records.user_id = users.user_id WHERE (records.record_date = ?) and (records.body_temperature >= ?);", (date, temperature))

        # 未記入者
        cur.execute("SELECT user_name from users;")
        user_sql = cur.fetchall()
        cur.execute("SELECT users.user_name FROM records INNER JOIN users ON records.user_id = users.user_id WHERE record_date = ?;", (sample,))
        recorder_sql = cur.fetchall()

        user_num = len(user_sql)
        recorder_num = len(recorder_sql)

        user_list = []
        recorder = []

        for i in range(user_num):
            user_list.append(user_sql[i]["user_name"])

        for j in range(recorder_num):
            recorder.append(recorder_sql[j]["user_name"])


        no_record = set(user_list) - set(recorder)

        conn.close()
        return render_template("adminhome.html", date = today, fevers = fevers, no_records = no_record)

    else:
        conn.close()
        return render_template("adminerror.html", message = "管理者権限がありません。")


@app.route("/adminrole", methods=["GET", "POST"])
@admin_required
def adminrole():
    # POSTで入ってきたら権限を変更する
    if request.method == "POST":

        # ユーザーIDが入力されていなかったらエラーを表示する
        if not request.form.get("user_id"):
            return render_template("adminerror.html", message = "ユーザーIDを入力してください")

        user_id = request.form.get("user_id")
        role = request.form.get("role")

        # 受け取ったユーザーIDが数字であることを確認
        if str.isdigit(user_id) == False:
            return render_template("adminerror.html", message = "ユーザーIDは数字のみで入力してください")

        # 受け取ったロールを変換
        if role == "admin":
            role = 1
        else:
            role = 0

        # データベースを設定
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # 送信者のユーザーIDを取得
        # admin_user_id = session["user_id"]
        # sessionが使えないため仮置き
        admin_user_id = 12345

        #グループidの取得(もしsessionで取得できるならsessionで取得)
        # group_id = session["group_id"]

        cur.execute("SELECT group_id FROM users WHERE user_id = ?;", (admin_user_id,))
        group_id = cur.fetchall()

        # 指定されたidのユーザーが管理者と同じグループに存在しているか確認
        cur.execute("SELECT user_id FROM users WHERE user_id = ? and group_id = ?;", (int(user_id), group_id[0]["group_id"]))
        user = cur.fetchall()

        if len(user) == 0:
            return render_template("adminerror.html", message = "このユーザーは存在しないか、このグループに所属していません")

        # roleを変更
        cur.execute("UPDATE users SET role = ? WHERE user_id = ?;", (role, int(user_id)))

        # メンバー一覧の作成
        cur.execute("SELECT user_name, user_id, role FROM users WHERE group_id = ?;", (group_id[0]["group_id"],))
        member_list = cur.fetchall()

        for i in range(len(member_list)):
            if member_list[i]["role"] == 1:
                member_list[i]["role"] = "管理者"
            else:
                member_list[i]["role"] = "一般"

        conn.close()
        return render_template("adminrole.html", lists = member_list, role = group_id[0]["group_id"])

    else:
        # データベースを設定
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # 権限を確認 dbのカラムを仮で「role」としています、role内も0を一般、1を管理者と仮定して作成しています
        # user_id = session["user_id"]
        # user_idを仮置き
        user_id = 12345
        cur.execute("SELECT role FROM users WHERE user_id = ?;", (user_id,))
        role = cur.fetchall()

        # ロールの確認
        if role[0]["role"] == 1:

            #グループidの取得(もしsessionで取得できるならsessionで取得)
            # group_id = session["group_id"]
            cur.execute("SELECT group_id FROM users WHERE user_id = ?;", (user_id,))
            group_id = cur.fetchall()

            # メンバー一覧の作成
            cur.execute("SELECT user_name, user_id, role FROM users WHERE group_id = ?;", (group_id[0]["group_id"],))
            member_list = cur.fetchall()

            for i in range(len(member_list)):
                if member_list[i]["role"] == 1:
                    member_list[i]["role"] = "管理者"
                else:
                    member_list[i]["role"] = "一般"

            conn.close()
            return render_template("adminrole.html", lists = member_list)

        else:
            conn.close()
            return render_template("adminerror.html", message = "管理者権限がありません。")


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
=======
        return render_template("groupadd.html")
>>>>>>> 141083b76ab507af928fc6d81f0756b6e9f35449

