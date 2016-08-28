import tornado
import tornado.web
import tornado.ioloop
import config as c
from db_op import DB             # Import DB Connection Pool
from db_op import DB_OP_Dorm     # Import DB Operations
from api import *                # Import all handlers

if __name__ == '__main__':
    db = DB(host=c.MYSQL_SERVER_IP, port=int(c.MYSQL_SERVER_PORT),
            user=c.MYSQL_USERNAME, passwd=c.MYSQL_PASSWORD,
            db=c.MYSQL_DATABASE_NAME)
    dorm = DB_OP_Dorm(db)
    args = {
        'db_op': dorm
    }
    app = tornado.web.Application([
        # Login
        ('/d2login/', GetOAuthLoginUrlHandler, args),
        ('/d2/', ReturnFromOAuthHandler, args),
        # Building
        ('/building/list/', ListAllBuildingHandler, args),
        ('/building/list/floor/', ListAllFloorHandler, args),
        # Class
        ('/class/list/', ListAllClassHandler, args),
        # Romm
        ('/search/room/?(?P<building_id>[0-9]+)?/', SearchRoomHandler, args),
        ('/search/class/?(?P<class_id>[0-9]+)?/', SearchClassHandler, args),
        ('/search/name/accurate/', SearchNameAccurateHandler, args),
        ('/search/name/fuzzy/', SearchNameFuzzyHandler, args),
        ('/search/other/student_id/', SearchStudentIDHandler, args),
        ('/search/other/student_nickname/', SearchStudentNicknameHandler, args),
        ('/search/other/email/', SearchEmailHandler, args),
        ('/search/other/facebook_id/', SearchFacebookIDHandler, args),
        # User
        ('/user/myinfo/', ListMyInfoHandler, args),
        ('/user/myinfo/modify/', ModifyMyInfoHandler, args),
        # Bot
        ('/webhook/', BotHandler, args),
        ('/connect/', ConnectHandler, args),
        # Usage info
        ('/usage/people/', UsagePeopleHandler, args),
        # Static
        ('/static/(.*)', tornado.web.StaticFileHandler, {'path': './static'}),
    ], debug=True)

    print("Server running at 0.0.0.0:" + str(c.API_SERVER_PORT))
    app.listen(c.API_SERVER_PORT)
    tornado.ioloop.IOLoop.instance().start()
