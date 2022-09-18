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


