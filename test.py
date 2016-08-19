import tornado.ioloop
import tornado.web
import tornado.httpclient
import tornado.httputil
import tornado.gen
import json
import urllib

apiurl = "http://micro.nctu.me:8888/api/"
secret = json.load(open('./secret.txt'))
stu_info = {}
stu_login = False
course_list = {}

def sendmsg(data):
    r_url = "https://bot.twmicrosheep.com/sendmsg/"
    r_body = json.dumps({"id": data['id'], "msg": data['msg'], "attach": data['attach']}).encode()
    r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", body=r_body)
    print("\n### Send msg ###")
    print(r_body)
    connect_out = tornado.httpclient.AsyncHTTPClient()
    connect_return = yield connect_out.fetch(r_req)
    print(connect_return)
    print("### Done ###")

def sendapi(location,data):
    r_url = apiurl+location
    r_body = urllib.parse.urlencode(data)
    r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", body=r_body)
    print("\n### Send api ###")
    print(r_body)
    connect_out = tornado.httpclient.AsyncHTTPClient()
    connect_return = yield connect_out.fetch(r_req)
    api_res = connect_return.body.decode()
    print(api_res)
    print("### Done ###")
    return api_res

def getapi(location,data):
    r_url = apiurl+location
    r_url = r_url+"?"+urllib.parse.urlencode(data)
    r_req = tornado.httpclient.HTTPRequest(r_url, method="GET")
    print("\n### Get api ###")
    print(r_url)
    connect_out = tornado.httpclient.AsyncHTTPClient()
    try:
        connect_return = yield connect_out.fetch(r_req)
        api_res = connect_return.body.decode()
        if api_res=="null":
            api_res = {}
        print(api_res)
        print("### Done ###")
        return api_res
    except:
        api_res = {}
        print(api_res)
        print("### Done ###")
        return api_res

def parsemsg(data): 
    print("### Parsing msg ###")
    global stu_login,stu_info,course_list
    if data['msg']=="login":
        print("Parsed login")
        res = yield from sendapi("login",{"username": secret['username'], "password": secret['password']})
        stu_login = True
        stu_info = json.loads(res)
        res = yield from getapi("course/list",{"loginTicket": stu_info['LoginTicket'], "accountId": stu_info['AccountId'], "role": stu_info['Role']})
        course_list = json.loads(res)
        yield from sendmsg({"id": data['id'], "msg": "Logined!", "attach": data['attach']})
        return
    elif data['msg']=="course":
        print("Parsed course")
        if stu_login:
            res = yield from getapi("course/list",{"loginTicket": stu_info['LoginTicket'], "accountId": stu_info['AccountId'], "role": stu_info['Role']})
            course_list = json.loads(res)
            r = ""
            for c in course_list:
                r = r + c["CourseName"] + "\n"
            yield from sendmsg({"id": data['id'], "msg": r, "attach": data['attach']})
        else:
            yield from sendmsg({"id": data['id'], "msg": "Please login first!", "attach": data['attach']})
        return
    elif data['msg']=="homework":
        print("Parsed homework")
        if stu_login:
            r = ""
            for c in course_list:
                res = yield from getapi("homework/list",{"loginTicket": stu_info['LoginTicket'], "accountId": stu_info['AccountId'], "courseId": c['CourseId'], "listType": "1"})
                if res=={}:
                    continue
                homework_list = json.loads(res)
                for i in homework_list:
                    r = r + c['CourseName'] + " " + i['DisplayName'] + " " + i['EndDate'] + "\n"
            yield from sendmsg({"id": data['id'], "msg": r, "attach": data['attach']})
        else:
            yield from sendmsg({"id": data['id'], "msg": "Please login first!", "attach": data['attach']})
        return
    elif data['msg']=="announce":
        print("Parsed announce")
        if stu_login:
            for c in course_list:
                res = yield from getapi("announce/list",{"loginTicket": stu_info['LoginTicket'], "courseId": c['CourseId'], "bulType": "1"})
                if res=={}:
                    continue
                announce_list = json.loads(res)
                for i in announce_list[:1]:
                    r = c['CourseName'] + " " + i['Caption'] + "\n"
                    yield from sendmsg({"id": data['id'], "msg": r, "attach": data['attach']})
        else:
            yield from sendmsg({"id": data['id'], "msg": "Please login first!", "attach": data['attach']})
        return
    else:
        print("Parsed unknown")
        yield from sendmsg({"id": data['id'], "msg": "Unknown command: "+data['msg'], "attach": data['attach']})
        print("Unknown command")
        return


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        KEY = "951236"
        if self.get_argument("hub.mode")=="subscribe" and self.get_argument("hub.verify_token")==KEY:
            self.write(self.get_argument("hub.challenge"))
    
    @tornado.gen.coroutine
    def post(self):
        body = json.loads(self.request.body.decode())
        print("\n=== Get message ===")
        s_id = body['entry'][0]['messaging'][0]['sender']['id']
        print(s_id)
        s_text=""
        s_attach=""
        try:
            s_text = body['entry'][0]['messaging'][0]['message']['text']
            print(s_text)
        except:
            pass
        try:
            s_attach = body['entry'][0]['messaging'][0]['message']['attachments'][0]
            print(s_attach)
        except:
            pass
        print("=== Decoding ===\n")
        result={'s_id':s_id, 's_text':s_text, 's_attach':s_attach}
        try:
            if(s_text!=""):
                s_l = s_text.split()
                for l in s_l:
                    yield from parsemsg({"id": s_id, "msg": l, "attach":s_attach})
        except:
            pass

class SendHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        self.write("Send Something~")

    @tornado.gen.coroutine
    def post(self):
        body = json.loads(self.request.body.decode())
        '''{id,msg}'''
        if body['msg']=="":
            res = {"recipient": {"id": body['id']}, "message": {"attachment": body['attach']}}
        else:
            res = {"recipient": {"id": body['id']}, "message": {"text": body['msg']}}
        PAGE_ACCESS_TOKEN="EAAPmV8LskZAcBALAtZBGZArPPr96cy1tcTvAbyxxVEiAzzanpLvpllAOp80R5MkFoXtJJ609ZA072WZByZBy5uQ7eAtVK8868V2CKQB9jxkvVNXd39kLoUVJn66S9EZAcSjHTNd4sjI87VHJ8qHhaB0OvlIj4hMFZCSM9ZA3HlrWZAngZDZD"
        r_url = "https://graph.facebook.com/v2.6/me/messages?access_token="+PAGE_ACCESS_TOKEN
        r_body = json.dumps(res).encode()
        r_req = tornado.httpclient.HTTPRequest(r_url, method="POST", headers=tornado.httputil.HTTPHeaders({"content-type": "application/json"}), body=r_body)
        connect_out = tornado.httpclient.AsyncHTTPClient()
        try: connect_return = yield connect_out.fetch(r_req)
        except Exception as e:
            print('FB GG', e)

def make_app():
    return tornado.web.Application([
        (r"/webhook/", MainHandler),
        (r"/sendmsg/", SendHandler),
    ],debug=True)

if __name__ == "__main__":
    app = make_app()
    PORT_NUM=8787
    app.listen(PORT_NUM)
    print("Server started on port "+str(PORT_NUM))
    tornado.ioloop.IOLoop.current().start()

