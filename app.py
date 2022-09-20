import os

import base64
import sqlite3
import calendar
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date
from matplotlib.figure import Figure
from flask import Flask, flash, redirect, render_template, url_for, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, id_generator
from io import BytesIO


app = Flask(__name__)

# Ensure templates are auto-reloaded 必要？
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies) 必要？
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
    # ログイン状態の確認
    if not session:
        redirect("/login")

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
        cur.execute("INSERT INTO logs(user_id, temperature, memo, updated_at) VALUES (?,?,?,?)",
                        (session["user_id"], temperature, memo, datetime.now().strftime("%Y-%m-%d")))

        cur.execute("SELECT log_id FROM logs ORDER BY log_id DESC LIMIT 1")
        i = cur.fetchall()
        log_id = i[0]["log_id"]

        headache = request.form.get("headache")
        cough = request.form.get("cough")
        fatigue = request.form.get("stuffiness")
        abnormal = request.form.get("taste_smell_abnormal")
        runny = request.form.get("runny_nose")

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

        user_name = request.form.get('user_name')
        input_check(user_name, "register.html", "名前を入力してください")

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
        newdata = (userid, user_name, password_hash, 1)
        cur.execute("INSERT INTO users (user_id, user_name, hash, role) VALUES(?, ?, ?, ?)", (newdata))
        conn.commit()
        conn.close()

        # リダイレクトでログイン画面に移動
        return render_template("register_ok.html")

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

        # データベースからグループID取得
        cur.execute("SELECT group_id FROM groups")
        checkers = cur.fetchall()

        # グループIDの初期化
        groupid = ""

        # グループIDがかぶらないようにIDを生成するループ処理
        for checker in checkers:
            # グループIDを生成
            groupid = id_generator()

            # グループIDが重複している場合
            if groupid == checker:
                continue

        # データベースに登録
        newdata = (groupid, groupname)
        cur.execute("INSERT INTO groups(group_id, group_name) VALUES(?, ?)", newdata)

        # グループに追加した人のロールを1(管理者)として、グループIDを追加する
        cur.execute("UPDATE users SET group_id = ?, role = 1 WHERE user_id = ?",(groupid, session["user_id"],))
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

        # データベース接続
        conn = sqlite3.connect("health.db")
        cur = conn.cursor()

        # データベースにグループ名とIDがあるかどうか確認
        checker = cur.execute("SELECT group_id FROM groups WHERE group_id = ?", (groupid,))
        if not checker:
            conn.close()
            return apology("groupadd.html", "グループIDが間違っております。")

        # ユーザーIDにグループIDを追加する
        cur.execute("UPDATE users SET group_id = ? WHERE user_id = ?",(groupid, session["user_id"]))

        # グループ作成者に管理者権限を付与
        cur.execute("UPDATE users SET role = 1 WHERE user_id = ?",(session["user_id"],))

        # DB接続終了
        conn.commit()
        conn.close()

        # ユーザーを体温報告ページに移動させる。
        return render_template("groupadd_ok.html")

    # GET経由ならログイン画面を表示させる
    else:
        return render_template("groupadd.html")


# 管理ページ
@app.route("/adminhome")
def adminhome():
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # 権限を確認 dbのカラムを仮で「role」としています、role内も0を一般、1を管理者と仮定して作成しています
    user_id = session["user_id"]
    cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    role = cur.fetchall()

    if role[0]["role"] == 1:
        # 日付の取得
        date = datetime.now().strftime("%Y-%m-%d")
        date_display = datetime.now().strftime("%Y年%m月%d日")

        # 発熱の閾値設定（以上）
        temperature = 37.5

        # 発熱者
        cur.execute("SELECT users.user_name, logs.temperature FROM users INNER JOIN logs ON users.user_id = logs.user_id WHERE logs.updated_at = ? AND logs.temperature >= ?", (date, temperature,))
        fevers = cur.fetchall()

        # 体調不良者
        cur.execute("SELECT users.user_name, log_details.headache, log_details.cough, log_details.fatigue, log_details.abnormal, log_details.runny, logs.memo FROM users INNER JOIN log_details ON log_details.user_id = users.user_id INNER JOIN logs ON logs.log_id = log_details.log_id WHERE logs.updated_at = ? AND (log_details.headache = 1 OR log_details.cough = 1 OR log_details.fatigue = 1 OR log_details.abnormal = 1 OR log_details.runny = 1)", (date,))
        poor_conditions = cur.fetchall()

        # データの整形
        # conditionCheckers = []
        # for i in poor_conditions:
        #     for j in i:
        #         if i[j] == 1:
        #             conditionCheckers.append(j)

        # 未記入者
        groupid = str(cur.execute("SELECT group_id FROM users WHERE user_id = ?", (session["user_id"],)))
        cur.execute("SELECT user_name FROM users WHERE group_id = ?", (groupid,))
        user_sql = cur.fetchall()
        cur.execute("SELECT user_name FROM users INNER JOIN logs ON logs.user_id = users.user_id WHERE logs.updated_at = ?", (date,))
        recorder_sql = cur.fetchall()

        user_list = []
        recorder = []

        for i in range(len(user_sql)):
            user_list.append(user_sql[i]["user_name"])

        for j in range(len(recorder_sql)):
            recorder.append(recorder_sql[j]["user_name"])


        no_records = set(user_list) - set(recorder)

        conn.close()
        return render_template("adminhome.html", date=date, fevers=fevers, no_records=no_records, poor_conditions=poor_conditions, date_display=date_display)

    else:
        conn.close()
        return apology("adminhome.html", "管理者権限がありません")


@app.route("/adminrole", methods=["GET", "POST"])
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

    # 症状の判別を有無に置換（DBで0:無、1:有として扱っているため）
    for i in all:
        for j in i:
            if i[j] == 1:
                i[j] = "有"
            else:
                i[j] = "無"

    # 現時点の月を取得
    dt_now = datetime.now()

    #現時点の月の日数を計算
    time_range = calendar.monthrange(dt_now.year, dt_now.month)[1]

    # t = str(dt_now.year) + '-' + str(dt_now.month) + '-' + '1'
    dates = [date(int(dt_now.year), int(dt_now.month) , 1) + timedelta(days=i) for i in range(time_range)]

    dt1 = datetime(dt_now.year, dt_now.month, dt_now.day)
    first_day = dt1.strftime("%Y-%m-01")
    #first_day = str(dt_now.year) + '-' + str(dt_now.month) + '-' + '1'

    if time_range == 30:
        last_day = dt1.strftime("%Y-%m-30")
    elif time_range == 31:
        last_day = dt1.strftime("%Y-%m-31")
    elif time_range == 29:
        last_day = dt1.strftime("%Y-%m-29")
    elif time_range == 28:
        last_day = dt1.strftime("%Y-%m-28")

    #last_day = str(dt_now.year) + '-' + str(dt_now.month) + '-' + str(time_range)

    # 体温情報を30日分取得
    cur.execute("SELECT temperature FROM logs WHERE user_id = ? AND datetime(updated_at, 'localtime') >= datetime(?, 'localtime') AND datetime(updated_at, 'localtime') <= datetime(?, 'localtime') ", (session["user_id"], first_day, last_day,))
    results = cur.fetchall()
    # 体温情報を収納するリスト
    tem = [0] * time_range
    # 体温情報があれば置換
    for i in range(len(results)):
        if results[i]:
            tem[i] = results[i]["temperature"]

    # グラフの生成
    fig = plt.figure(figsize=(10, 4.0))
    ax = fig.add_subplot(111)

    # 軸ラベルの設定（日本語不可？）
    ax.set_xlabel("date", size = 14)
    ax.set_ylabel("body_temperature[℃]", size = 14)

    ax.set_xticks(dates)

    # y軸(最小値、最大値)
    ax.set_ylim(35, 40)

    ax.grid()

    # x軸は日付、y軸は体温情報
    ax.plot(dates,tem, linewidth = 2, color = "orange")

    # x目盛り軸の設定
    ax.set_xticklabels(dates, rotation=45, ha='right')

    # バッファに保存
    buf = BytesIO()
    fig.savefig(buf, format='png')

    # グラフをHTMLに埋め込めるよう変換
    data = base64.b64encode(buf.getbuffer()).decode('ascii')
    image_tag = f'<img src="data:image/png;base64,{data}"/>'

    return render_template("mypage.html", details=details, logs=logs, all=all, image=image_tag)