import config as c
import tornado.httpclient
import tornado.httputil
import json
import time
from utils.JwtToken import JwtToken

HELP_MSG = "這是交大找室友登入機器人，打login可取得登入連結，用您的帳號登入交大找室友平台。"

def send_msg(fb_id, msg):
    res = {"recipient": {"id": fb_id}, "message": {"text": msg}}
    r_url = "https://graph.facebook.com/v2.6/me/messages?access_token=" + c.FB_PAGE_ACCESS_TOKEN
    r_body = json.dumps(res).encode()
    r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", headers=tornado.httputil.HTTPHeaders({"content-type": "application/json"}), body=r_body)
    connect_out = tornado.httpclient.AsyncHTTPClient()
    try:
        connect_return = yield connect_out.fetch(r_req)
        print("=== Send message to "+fb_id+" ===\n"+msg+"\n=====  Done  =====")
    except Exception as e:
        print('FB send msg not working! ' + str(e))

def connect():
    r_url = "https://graph.facebook.com/v2.6/me/subscribed_apps?access_token=" + c.FB_PAGE_ACCESS_TOKEN
    r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", body="")
    connect_out = tornado.httpclient.AsyncHTTPClient()
    try:
        connect_return = yield connect_out.fetch(r_req)
        return "FB connect Done! " + str(connect_return.body.decode())
    except Exception as e:
        return 'FB connect not working! ' + str(e)

def get_return_login_url(fb_id):
    TIME_UNUSED = 3*60
    t = int(time.time()) + TIME_UNUSED
    j = JwtToken().generate({"fbid": fb_id, "time": t}).decode("utf-8")
    return c.ROOT_URL+'/fb/?token='+j

def get_msg(fb_id, msg):
    msg = msg.lower()
    if msg == "":
        return
    elif reply_login(msg):
        yield from send_msg(fb_id, get_return_login_url(fb_id))
    elif reply_help(msg):
        yield from send_msg(fb_id, HELP_MSG)
    elif reply_hello(msg):
        yield from send_msg(fb_id, "Hello！我是交大找室友登入機器人！")
    elif reply_anan(msg):
        yield from send_msg(fb_id, "安安您好~ 我是交大找室友登入機器人！")
    elif reply_chinese_hello(msg):
        yield from send_msg(fb_id, "您好！我是交大找室友登入機器人！")
    elif reply_bad_word(msg):
        yield from send_msg(fb_id, "請不要罵髒話！謝謝！")
    elif reply_who_r_u(msg):
        yield from send_msg(fb_id, "這是秘密！")
    elif reply_love(msg):
        yield from send_msg(fb_id, "<3 <3 <3")
    else:
        yield from send_msg(fb_id, "我聽不懂你在說些什麼？ ><")
    return

def reply_login(text):
    return text in ["login", "登入"]

def reply_help(text):
    strings = ["help", "怎麼用", "幫助", "提示"]
    for s in strings:
        if text.find(s) != -1:
            return True
    return False

def reply_hello(text):
    return text in ["hi", "hello", "哈囉"]

def reply_anan(text):
    if text.find("安安") != -1:
        return True
    else:
        return False

def reply_chinese_hello(text):
    strings = ["你好", "妳好"]
    for s in strings:
        if text.find(s) != -1:
            return True
    return False

def reply_bad_word(text):
    return text in ["fuck", "幹"]

def reply_who_r_u(text):
    return text in ["who are you", "who r u", "你是誰", "妳是誰"]

def reply_love(text):
    strings = ["<3", "love you", "love u", "愛你", "愛妳"]
    for s in strings:
        if text.find(s) != -1:
            return True
    return False
