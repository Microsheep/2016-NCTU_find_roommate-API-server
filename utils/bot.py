import config as c
import tornado.httpclient
import tornado.httputil
import json
import time
from utils.JwtToken import JwtToken

DEFAULT_MSG = "您好！我是交大找室友機器人。已經收到您的訊息。等等會有人正式回覆給您！謝謝！"

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
    elif reply_help(msg):
        yield from send_msg(fb_id, DEFAULT_MSG)
    elif reply_login(msg):
        yield from send_msg(fb_id, get_return_login_url(fb_id))
    else:
        yield from send_msg(fb_id, "我聽不懂你在說些什麼？ ><")
    return

def reply_login(text):
    return text in ["login", "登入"]

def reply_help(text):
    return True
