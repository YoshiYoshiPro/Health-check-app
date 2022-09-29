import os
import base64
import sqlite3
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import calendar
import base64
from email import message
from unittest import result
from datetime import datetime, timedelta, date
from matplotlib.figure import Figure
from io import BytesIO
from flask import Flask, flash, redirect, render_template, url_for, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, id_generator
from io import BytesIO


app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

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

        # 詳細情報を取得
        headache = int(request.form.get("headache"))
        cough = int(request.form.get("cough"))
        fatigue = int(request.form.get("stuffiness"))
        abnormal = int(request.form.get("taste_smell_abnormal"))
        runny = int(request.form.get("runny_nose"))

        #今日既に体温報告をしているかどうか確認
        cur.execute("SELECT log_id FROM logs WHERE user_id = ? AND updated_at = ?", (session["user_id"], datetime.now().strftime("%Y-%m-%d")))
        i = cur.fetchall()

        if not i:
            # 体温、備考情報を記録テーブルに挿入
            cur.execute("INSERT INTO logs(user_id, temperature, memo, updated_at) VALUES (?,?,?,?)",\
                        (session["user_id"], temperature, memo, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            # log_idを取得
            cur.execute("SELECT log_id FROM logs ORDER BY log_id DESC LIMIT 1")
            i = cur.fetchall()
            log_id = i[0]["log_id"]

            # 記録詳細テーブルに挿入
            cur.execute("INSERT INTO log_details(log_id,user_id,headache,cough,fatigue,abnormal,runny) VALUES (?,?,?,?,?,?,?)",\
                        (log_id, session["user_id"], headache, cough, fatigue, abnormal, runny),)
            conn.commit()
        else:
            # 体温、備考情報を更新
            log_id = i[0]["log_id"]
            cur.execute("UPDATE logs SET temperature = ?, memo = ? WHERE log_id = ?", (temperature, memo, log_id))
            cur.execute("UPDATE log_details SET headache = ?, cough= ?, fatigue = ?, abnormal = ?, runny = ? WHERE log_id = ?", \
                        (headache, cough, fatigue, abnormal, runny, log_id,))
            conn.commit()

        conn.close()

        flash("情報を更新しました。")
        return redirect("/mypage")

    # GETの場合
    else:
        # データベースに接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        #今日既に体温報告をしているかどうか確認
        cur.execute("SELECT * FROM logs WHERE user_id = ? AND updated_at = ?", (session["user_id"], datetime.now().strftime("%Y-%m-%d")))
        logs_data = cur.fetchall()

        # 今日まだ入力していない場合
        if not logs_data:
            conn.close()
            return render_template("input.html",runny_nose0="checked", headache0="checked", stuffiness0="checked", cough0="checked",taste_smell_abnormal0="checked")

        # 入力している場合
        else:
            cur.execute("SELECT * FROM log_details WHERE log_id = ?", (logs_data[0]["log_id"],))
            log_details_data = cur.fetchall()

            # htmlのタグ作成
            body_temperature = "value=" + str(logs_data[0]["temperature"])
            memo = logs_data[0]["memo"]

            # checkedをリストで管理する
            inputstatus = []
            inputstatusname  = ["runny", "headache", "fatigue", "cough", "abnormal"]
            for n in inputstatusname:
                if log_details_data[0][n] == 0:
                    inputstatus.append("checked")
                    inputstatus.append("")
                else:
                    inputstatus.append("")
                    inputstatus.append("checked")
            conn.close()
            return render_template("input.html",body_temperature=body_temperature,\
                                    runny_nose0=inputstatus[0], runny_nose1=inputstatus[1],\
                                    headache0=inputstatus[2], headache1=inputstatus[3],\
                                    stuffiness0=inputstatus[4], stuffiness1=inputstatus[5],\
                                    cough0=inputstatus[6], cough1=inputstatus[7],\
                                    taste_smell_abnormal0=inputstatus[8], taste_smell_abnormal1=inputstatus[9],\
                                    memo=memo)

# ログイン画面
@app.route("/login", methods=["GET", "POST"])
def login():

    # user_id(セッション) をリセット
    session.clear()

    # POST経由の場合
    if request.method == "POST":

        userid = request.form.get("userid")

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

    if request.method == "POST":

        userid = request.form.get('userid')
        user_name = request.form.get('user_name')
        password = request.form.get('password')

        if len(password) < 4:
            return apology("register.html", "パスワードは4文字以上入力してください")
        confirmation = request.form.get('confirmation')

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
        newdata = (userid, user_name, password_hash)
        cur.execute("INSERT INTO users (user_id, user_name, hash) VALUES(?, ?, ?)", (newdata))

        # データべースの接続終了
        conn.commit()
        conn.close()

        # アカウント登録したユーザーを記憶する
        session["user_id"] = userid

        # フラッシュメッセージ
        flash("登録完了しました")

        # リダイレクトで入力画面に移動
        return redirect("/")

    # getの場合は登録画面をレンダリング
    else:
        return render_template("register.html")

# グループ作成
@app.route("/groupcreate", methods=["GET", "POST"])
@login_required
def groupcreate():

    # postで入ってきたらデータベースに登録の処理を実行
    if request.method == "POST":

        groupname = request.form.get('groupname')

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # データベースからグループID取得
        cur.execute("SELECT group_id FROM groups")
        checkers = cur.fetchall()

        # グループIDの初期化
        groupid = ""

        # 初期にグループを登録する場合
        if checkers:
            # グループIDがかぶらないようにIDを生成するループ処理
            for checker in checkers:
                # グループIDを生成
                groupid = id_generator()

                # グループIDが重複している場合
                if groupid == checker:
                    continue
        else:
            groupid = id_generator()

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

        groupid = str(request.form.get('groupid'))

        # データベース接続
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # データベースにグループ名とIDがあるかどうか確認
        cur.execute("SELECT group_name FROM groups WHERE group_id = ?", (groupid,))
        group_name = cur.fetchall()
        if not group_name:
            conn.close()
            return apology("groupadd.html", "グループIDが間違っております。")

        # ユーザーIDにグループIDを追加する
        cur.execute("UPDATE users SET role = 0, group_id = ? WHERE user_id = ?", (groupid, session["user_id"]))

        # DB接続終了
        conn.commit()
        conn.close()

        # ユーザーを体温報告ページに移動させる
        return render_template("groupadd_ok.html", group_name=group_name[0]["group_name"])

    # GET経由ならログイン画面を表示させる
    else:
        return render_template("groupadd.html")

# グループ脱退
@app.route("/groupgetout")
def groupgetout():

    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    #usersテーブルのgroup_idをNULLにする
    cur.execute("UPDATE users SET roll = 0, group_id = NULL WHERE user_id = ?",(session["user_id"],))

    conn.commit()
    conn.close()

    # フラッシュメッセージ
    flash("グループから脱退しました。")

    # リダイレクトでマイページに移動
    return redirect("/mypage")


# 管理ページ
@app.route("/adminhome")
def adminhome():
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # 権限を確認
    user_id = session["user_id"]
    cur.execute("SELECT role FROM users WHERE user_id = ?;", (user_id,))
    role = cur.fetchall()

    # 管理者権限がある人
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

        # 症状の判別を有無に置換（DBで0:無、1:有として扱っているため）
        for i in poor_conditions:
            for j in i:
                if i[j] == 1:
                    i[j] = "有"
                elif i[j] == 0:
                    i[j] = "無"

        # 未記入者
        cur.execute("SELECT group_id FROM users WHERE user_id = ?", (session["user_id"],))
        groupid = cur.fetchall()
        cur.execute("SELECT user_name FROM users WHERE group_id = ?", (groupid[0]["group_id"],))
        user_sql = cur.fetchall()
        cur.execute("SELECT user_name FROM users INNER JOIN logs ON logs.user_id = users.user_id WHERE logs.updated_at = ? and users.group_id = ?", (date, groupid[0]["group_id"]))
        recorder_sql = cur.fetchall()

        user_list = list()
        recorder = list()

        for i in user_sql:
            user_list.append(i["user_name"])

        for j in recorder_sql:
            recorder.append(j["user_name"])

        # 集合の差集合で未記入者を判別
        no_record = set(user_list) - set(recorder)
        no_record = list(no_record)

        conn.close()
        return render_template("adminhome.html", date=date, fevers=fevers, no_records=no_record, poor_conditions=poor_conditions, date_display=date_display)

    # 管理者権限がない人
    else:
        conn.close()
        # ユーザーを体温報告ページに移動させる。
        return render_template("noAuthorization.html", message="管理者権限がありません")


@app.route("/adminrole", methods=["GET", "POST"])
def adminrole():
    # POSTで入ってきたら権限を変更する
    if request.method == "POST":

        # ユーザーIDが入力されていなかったらエラーを表示する
        if not request.form.get("user_id"):
            return apology("adminrole.html", "ユーザーIDを入力してください")

        user_id = request.form.get("user_id")
        role = request.form.get("role")

        # 受け取ったユーザーIDが数字であることを確認
        if str.isdigit(user_id) == False:
            return apology("adminrole.html", "ユーザーIDは数字のみで入力してください")

        # 受け取ったロールを変換
        if role == "admin":
            role = 1
        elif role == "ippan":
            role = 0

        # データベースを設定
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # 送信者のユーザーIDを取得
        admin_user_id = session["user_id"]

        # グループidの取得(もしsessionで取得できるならsessionで取得)
        # group_id = session["group_id"]

        cur.execute("SELECT group_id FROM users WHERE user_id = ?;", (admin_user_id,))
        group_id = cur.fetchall()

        # 指定されたidのユーザーが管理者と同じグループに存在しているか確認
        cur.execute("SELECT user_id FROM users WHERE user_id = ? and group_id = ?;", (int(user_id), group_id[0]["group_id"]))
        user = cur.fetchall()

        if len(user) == 0:
            conn.close()
            return apology("adminrole.html", "このユーザーは存在しないか、このグループに所属していません")

        # roleを変更
        cur.execute("UPDATE users SET role = ? WHERE user_id = ?;", (role, int(user_id)))
        conn.commit()

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
        # データベースを設定
        conn = sqlite3.connect("health.db")
        conn.row_factory = dict_factory
        cur = conn.cursor()

        # 権限を確認 dbのカラムを仮で「role」としています、role内も0を一般、1を管理者と仮定して作成しています
        user_id = session["user_id"]

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
            # ユーザーを体温報告ページに移動させる。 「管理者権限がありません。」というメッセージを表示したいのですが、やり方がわからないため保留
            return redirect("/")


@app.route("/mypage")
@login_required
def mypage():

    # データベースに接続
    conn = sqlite3.connect("health.db")
    conn.row_factory = dict_factory
    cur = conn.cursor()

    # ユーザの入力情報を取得
    cur.execute("SELECT * FROM logs INNER JOIN log_details ON logs.log_id = log_details.log_id AND log_details.user_id = ?", (session["user_id"],))
    all = cur.fetchall()

    # 現時点
    dt_now = datetime.now()

    #現時点の月の日数を計算
    month_days_range = calendar.monthrange(dt_now.year, dt_now.month)[1]

    # 日のデータを収納するリスト（横軸に使用）
    dates = [date(int(dt_now.year), int(dt_now.month) , 1) + timedelta(days=i) for i in range(month_days_range)]

    # 現時点の年月日を取得
    dt1 = datetime(dt_now.year, dt_now.month, dt_now.day)

    # 月の初めを取得
    first_day = dt1.strftime("%Y-%m-01")

    # 月の最終日を取得（もっとスマートな方法があれば変える）
    if  month_days_range == 31:
        last_day = dt1.strftime("%Y-%m-31")
    elif month_days_range == 30:
        last_day = dt1.strftime("%Y-%m-30")
    elif month_days_range == 29:
        last_day = dt1.strftime("%Y-%m-29")
    elif month_days_range == 28:
        last_day = dt1.strftime("%Y-%m-28")

    # 体温情報を一月分取得（BETWEENだとうまくいく）
    # cur.execute("SELECT temperature FROM logs WHERE user_id = ? AND datetime(updated_at, 'localtime') >= datetime(?, 'localtime') AND datetime(updated_at, 'localtime') <= datetime(?, 'localtime') ", (session["user_id"], first_day, last_day,))
    cur.execute("SELECT temperature, updated_at FROM logs WHERE user_id = ? AND updated_at BETWEEN ? AND ? ", (session["user_id"], first_day, last_day,))
    results = cur.fetchall()

    # 体温情報を収納するリスト
    tem = [np.nan] * month_days_range

    # 体温情報と日付を対応づけて管理
    for i in range(len(results)):
        if results[i]:
            # 日付情報を0000-00-00の形で抽出
            d = datetime.strptime(results[i]["updated_at"], '%Y-%m-%d')
            # さらに日付部分だけを抽出（n日）
            n = d.day
            #体温情報リストのn番目に体温値を挿入
            tem[n - 1] = results[i]["temperature"]

    # グラフの生成
    fig = plt.figure(figsize=(10, 4.0))
    ax = fig.add_subplot(111)

    # 軸ラベルの設定（日本語でもできるが詳細な設定が必要）
    ax.set_xlabel("date", size = 14)
    ax.set_ylabel("body_temperature[℃]", size = 14)

    # y軸(最小値、最大値)
    ax.set_ylim(35, 40)

    # 目盛り線表示
    ax.grid()

    # x目盛り軸の設定
    ax.set_xticklabels(dates, rotation=45, ha='right')

    # x軸は日付、y軸は体温情報
    ax.plot(dates, tem, linewidth = 2, color = "orange", marker = "D")

    # x軸の目盛りラベル
    ax.set_xticks(dates)

    # バッファに保存
    buf = BytesIO()
    fig.savefig(buf, format='png')

    # グラフをHTMLに埋め込めるよう変換
    data = base64.b64encode(buf.getbuffer()).decode('ascii')
    image_tag = f'<img src="data:image/png;base64,{data}"/>'

    # DB接続終了,グラフの閉め
    plt.close()
    conn.close()

    # 症状の判別を有無に置換（DBで0:無、1:有として扱っているため）
    for i in all:
        for j in i:
            if i[j] == 1:
                i[j] = "有"
            elif i[j] == 0:
                i[j] = "無"

    return render_template("mypage.html", all=all, image_tag=image_tag)
