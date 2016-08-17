import time
import functools
import config as c
from tornado.web import HTTPError
from utils.JwtToken import JwtToken

def auth_login(method):
    # Decorate method with this to require user logined
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        success, info = self.current_user
        if not success:
            self.set_status(401)
            self.res['error'] = info
            self.write_json()
            self.finish()
            raise HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper

def refresh_token(method):
    # Decorate method to refresh token time after request
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            now = JwtToken().validate(self.get_argument('token'))
            if len(now.keys()) != 0:
                TIME_UNUSED = 5*60*60
                t = int(time.time()) + TIME_UNUSED
                j = JwtToken().generate({"uid": now['uid'], "type": now['type'], "time": t})
                self.res['token'] = j.decode("utf-8")
        except:
            self.set_status(401)
            self.res['error'] = "Token Refresh Error"
            self.write_json()
            self.finish()
            raise HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper
