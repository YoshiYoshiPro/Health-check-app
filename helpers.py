import random
import string
from flask import redirect, render_template, session
from functools import wraps

# 入力ミスなどをメッセージ付きで返す
def apology(html,messages):
    return render_template(html, message=messages)

# ログインユーザーのみアクセス可能にする
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# グループIDを生成する関数（頭文字1文字と数字5桁）
def id_generator():
    text = f'{random.randrange(1, 10**5):05}'
    uppercase_list = random.sample(string.ascii_uppercase, 1)

    # リスト型 → str型
    uppercase = ''.join(uppercase_list)

    # 文字と数字を連結
    text = uppercase + text

    return text
