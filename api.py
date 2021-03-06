import tornado
from tornado import gen
from tornado.web import HTTPError
import config as c
import json
import time
import urllib
from datetime import datetime
from utils.JwtToken import JwtToken
from utils.json_decoder import DatetimeEncoder
from utils.permission import auth_login, refresh_token
from utils.bot import get_msg, connect
from utils.sql_check import check_safe

class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwarg):
        self.db_op = kwarg.pop('db_op')
        self.res = {
            'token': "",
            'data': [],
            'error': {}
        }
        super().__init__(*args, **kwarg)

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, PATCH, OPTIONS")

    def write_json(self):
        print(str(datetime.now()) + " " + self.request.uri)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(self.res, cls=DatetimeEncoder))

    def get_current_user(self):
        try:
            token = self.get_argument('token')
        except:
            token = None
        if token:
            j = JwtToken().validate(token)
            if len(j.keys()) == 0:
                return False, "Jwt Validation Error"
            try:
                if int(time.time()) < j['time']:
                    return True, j['uid']
                else:
                    return False, "Jwt Expired"
            except:
                return False, "Jwt Validation Error"
        return False, "Jwt Token Not Found"

    def get_method(self):
        try:
            token = self.get_argument('token')
            j= JwtToken().validate(token)
            data = {
                "type": j['type'],
                "uid": j['uid']
            }
            return data
        except:
            return "Error getting method!"


class GetOAuthLoginUrlHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        OAUTH_URL = "http://id.nctu.edu.tw/o/authorize/?client_id="+c.OAUTH_CLIENT_ID+"&scope=profile&response_type=code"
        self.redirect(OAUTH_URL)


class ReturnFromOAuthHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        r_url = "https://id.nctu.edu.tw/o/token/"
        r_body = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": self.get_argument('code'),
            "client_id": c.OAUTH_CLIENT_ID,
            "client_secret": c.OAUTH_CLIENT_SECRET,
            "redirect_uri": c.ROOT_URL + "/d2/"
        })
        r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", body=r_body)
        connect_out = tornado.httpclient.AsyncHTTPClient()
        connect_return = yield connect_out.fetch(r_req)
        connect_res = json.loads(connect_return.body.decode())

        r_url = "https://id.nctu.edu.tw/api/profile/"
        r_header = {
            "Authorization": ("Bearer "+connect_res['access_token'])
        }
        r_req = tornado.httpclient.HTTPRequest(r_url, method="GET", headers=r_header)
        connect_out = tornado.httpclient.AsyncHTTPClient()
        connect_return = yield connect_out.fetch(r_req)
        d2 = connect_return.body.decode()
        uid = yield from self.db_op.find_uid("d2", d2, **params)
        if uid == -1:
            yield from self.db_op.add_uid("d2", d2, **params)
            uid = yield from self.db_op.find_uid("d2", d2, **params)
        TIME_UNUSED = 5*60*60
        t = int(time.time()) + TIME_UNUSED
        j = JwtToken().generate({"uid": uid, "type": "d2", "time": t}).decode("utf-8")
        self.redirect(c.HOME_URL+"?token="+j)

class ListAllBuildingHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_building(**params)
        self.write_json()

class ListAllFloorHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_building(**params)
        floor = yield from self.db_op.list_all_floor(**params)
        for f in floor:
            if 'floor' in self.res['data'][f['building_id']].keys():
                self.res['data'][f['building_id']]['floor'].append(f['floor'])
            else:
                self.res['data'][f['building_id']]['floor'] = [f['floor']]
        for b in self.res['data']:
            if 'floor' not in b.keys():
                b['floor'] = []
        self.write_json()

class ListAllClassHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_class(**params)
        self.write_json()

class ListMyInfoHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_my_info(self.get_method()['uid'], **params)
        self.write_json()

class ModifyMyInfoHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def patch(self, **params):
        uid = self.get_method()['uid']
        try:
            j = json.loads(self.request.body.decode("utf-8"))
        except:
            self.res['data'] = "JSON decode Error!"
            self.write_json()
        p_normal = ["student_id", "student_nickname", "class_id", "email", "facebook_id", "slogan", "detail"]
        p_enable = ["student_id_enable", "student_nickname_enable", "class_id_enable", "room_id_enable", "email_enable", "facebook_id_enable", "slogan_enable", "detail_enable"]
        # Student Name Cannot Be Blank
        try:
            if j["student_name"] != "":
                yield from self.db_op.modify_my_info(uid, "student_name", j["student_name"], **params)
        except:
            pass
        # Add room if needed
        try:
            exist = yield from self.db_op.check_room_exist(j["room"]["building_id"], j["room"]["room_name"], **params)
            if exist == -1:
                yield from self.db_op.add_room(j["room"]["building_id"], j["room"]["room_name"], str(j["room"]["room_name"])[0], **params)
                exist = yield from self.db_op.check_room_exist(j["room"]["building_id"], j["room"]["room_name"], **params)
            yield from self.db_op.modify_my_info(uid, "room_id", exist, **params)
        except:
            pass
        # Other Attribute
        for attribute in p_normal:
            try:
                yield from self.db_op.modify_my_info(uid, attribute, j[attribute], **params)
            except:
                pass
        for attribute in p_enable:
            try:
                if j[attribute]:
                    yield from self.db_op.modify_my_info(uid, attribute, 1, **params)
                else:
                    yield from self.db_op.modify_my_info(uid, attribute, 0, **params)
            except:
                pass
        self.res['data'] = "Done!"
        self.write_json()

    def options(self, **params):
        self.res['data'] = "Options OK!"
        self.write_json()

class SearchRoomHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, building_id, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if arg.isdigit() and len(arg) <= 5:
                room_id = yield from self.db_op.check_room_exist(building_id, arg, **params)
                search_param = [
                    ("s.room_id", room_id,),
                    ("room_id_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchClassHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, class_id, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if check_safe(arg, 2):
                search_param = [
                    ("student_name_fuzzy", arg,),
                    ("class_id", class_id,),
                    ("class_id_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchNameAccurateHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if check_safe(arg, 2):
                search_param = [
                    ("student_name_accurate", arg,)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchNameFuzzyHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if check_safe(arg, 2):
                search_param = [
                    ("student_name_fuzzy", arg,)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchStudentIDHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if arg.isdigit() and len(arg) <= 10:
                search_param = [
                    ("student_id", arg,),
                    ("student_id_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchStudentNicknameHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if check_safe(arg, 2):
                search_param = [
                    ("student_nickname", arg,),
                    ("student_nickname_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchEmailHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if check_safe(arg, 2) and arg.find("@") != -1:
                search_param = [
                    ("email", arg,),
                    ("email_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class SearchFacebookIDHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        try:
            arg = self.get_arguments("arg")[0]
            if arg.isdigit() and len(arg) <= 20:
                search_param = [
                    ("facebook_id", arg,),
                    ("facebook_id_enable", 1)
                ]
                self.res['data'] = yield from self.db_op.search(search_param, self.get_method(), **params)
            else:
                self.res['data'] = []
        except:
            self.res['data'] = []
        self.write_json()

class BotHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        if self.get_argument("hub.mode") == "subscribe" and self.get_argument("hub.verify_token") == c.FB_WEBHOOK_KEY:
            self.write(self.get_argument("hub.challenge"))

    @tornado.gen.coroutine
    def post(self, **params):
        body = json.loads(self.request.body.decode())
        s_id = body['entry'][0]['messaging'][0]['sender']['id']
        s_text=""
        try:
            s_text = body['entry'][0]['messaging'][0]['message']['text']
            print(s_text)
        except:
            pass
        print("=== Get message from "+s_id+" ===\n"+s_text+"\n=====  Done  =====")
        yield from get_msg(s_id, s_text)

class ConnectHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        self.res['data'] = yield from connect()
        self.write_json()

class UsagePeopleHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_usage_people(**params)
        self.write_json()
