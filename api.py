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
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "POST, GET")

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


class GetFBLoginUrlHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        self.redirect("https://www.facebook.com/ncturoommate/")


class ReturnFromFBHandler(BaseHandler):
    @gen.coroutine
    def get(self, **params):
        success = True
        err = ""
        fbid = ""
        try:
            token = self.get_argument('token')
        except:
            token = None
            success = False
            err = "Token Not Found"
        if token:
            j = JwtToken().validate(token)
            if len(j.keys()) == 0:
                success = False
                err = "Jwt Validation Error"
            if int(time.time()) > j['time']:
                success = False
                err = "Jwt Expired"
            try:
                fbid = j['fbid']
            except:
                success = False
                err = "Jwt Validation Error"
        if not success:
            self.set_status(401)
            self.res['error'] = err
            self.write_json()
            self.finish()
            raise HTTPError(401)
        else:
            uid = yield from self.db_op.find_uid("fb", fbid, **params)
            if uid == -1:
                yield from self.db_op.add_uid("fb", fbid, **params)
                uid = yield from self.db_op.find_uid("fb", fbid, **params)
            enable = yield from self.db_op.check_uid_enabled(uid, **params)
            if enable == 0:
                self.set_status(401)
                self.res['error'] = "Data already transfered!"
                self.write_json()
                self.finish()
                raise HTTPError(401)
        TIME_UNUSED = 5*60*60
        t = int(time.time()) + TIME_UNUSED
        j = JwtToken().generate({"uid": uid, "type": "fb", "time": t}).decode("utf-8")
        # self.redirect(c.HOME_URL+"?token="+j)
        self.redirect("https://stunion.nctu.edu.tw/blog/")

class ListAllBuildingHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_building(**params)
        self.write_json()


class ListAllClassHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_class(**params)
        self.write_json()


class ListAllRoomHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        self.res['data'] = yield from self.db_op.list_all_room(**params)
        self.write_json()


class ListALLRoomByBuildingHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, building_id, **params):
        self.res['data'] = yield from self.db_op.list_all_room_by_building(building_id, **params)
        self.write_json()

class ListALLRoomByBuildingFloorHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, building_id, floor, **params):
        self.res['data'] = yield from self.db_op.list_all_room_by_building_floor(building_id, floor, **params)
        self.write_json()

class ListALLUserByRoomHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, room_id, **params):
        self.res['data'] = yield from self.db_op.list_all_user_by_room(self.get_method()['type'], room_id, **params)
        self.write_json()

class AddRoomHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def post(self, **params):
        try:
            exist = yield from self.db_op.check_room_exist(self.get_arguments("building_id")[0], self.get_arguments("room_name")[0], **params)
            if exist == -1:
                yield from self.db_op.add_room(self.get_arguments("building_id")[0], self.get_arguments("room_name")[0], **params)
                self.res['data'] = yield from self.db_op.check_room_exist(self.get_arguments("building_id")[0], self.get_arguments("room_name")[0], **params)
            else:
                self.res['data'] = exist
        except:
            self.res['data'] = "Something went wrong!"
            pass
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
        p_normal = ["student_id", "student_nickname", "class_id", "room_id", "email", "facebook_id", "slogan", "detail"]
        p_enable = ["student_id_enable", "student_nickname_enable", "class_id_enable", "room_id_enable", "email_enable", "facebook_id_enable", "slogan_enable", "detail_enable"]
        try:
            if self.get_arguments("student_name")[0] != "":
                yield from self.db_op.modify_my_info(uid, "student_name", self.get_arguments("student_name")[0], **params)
        except:
            pass
        for attribute in p_normal:
            try:
                yield from self.db_op.modify_my_info(uid, attribute, self.get_arguments(attribute)[0], **params)
            except:
                pass
        for attribute in p_enable:
            try:
                if self.get_arguments(attribute)[0] == "true":
                    yield from self.db_op.modify_my_info(uid, attribute, 1, **params)
                elif self.get_arguments(attribute)[0] == "false":
                    yield from self.db_op.modify_my_info(uid, attribute, 0, **params)
                else:
                    pass
            except:
                pass
        self.res['data'] = "Done!"
        self.write_json()

class ListUserInfoHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, uid, **params):
        self.res['data'] = yield from self.db_op.list_user_info(self.get_method()['type'], uid, **params)
        self.write_json()

class SearchHandler(BaseHandler):
    @gen.coroutine
    @auth_login
    @refresh_token
    def get(self, **params):
        search_param = []
        possible_param = ["student_id", "student_name", "student_nickname", "class_id", "email", "facebook_id"]
        for param in possible_param:
            try:
                search_param.append((param, self.get_arguments(param)[0],))
            except:
                pass
        if search_param != []:
            try:
                fuzzy = self.get_arguments("fuzzy")[0]
            except:
                fuzzy = False
                pass
            if fuzzy == "true" and self.get_arguments("student_name") != "":
                self.res['data'] = yield from self.db_op.search(self.get_method()['type'], True, search_param, **params)
            else:
                self.res['data'] = yield from self.db_op.search(self.get_method()['type'], False, search_param, **params)
        else:
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
