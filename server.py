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
        ('/fblogin/', GetFBLoginUrlHandler, args),
        ('/fb/', ReturnFromFBHandler, args),
        # Building
        ('/building/list/', ListAllBuildingHandler, args),
        # Class
        ('/class/list/', ListAllClassHandler, args),
        # Romm
        ('/room/list/', ListAllRoomHandler, args),
        ('/room/list/?(?P<building_id>[0-9]+)?/', ListALLRoomByBuildingHandler, args),
        ('/room/list/?(?P<building_id>[0-9]+)?/?(?P<floor>[0-9]+)?/', ListALLRoomByBuildingFloorHandler, args),
        ('/room/list/user/?(?P<room_id>[0-9]+)?/', ListALLUserByRoomHandler, args),
        ('/room/add/', AddRoomHandler, args),
        # Search
        ('/search/', SearchHandler, args),
        # User
        ('/user/myinfo/', ListMyInfoHandler, args),
        ('/user/myinfo/modify/', ModifyMyInfoHandler, args),
        ('/user/info/?(?P<uid>[0-9]+)?/', ListUserInfoHandler, args),
        # Static
        ('/static/(.*)', tornado.web.StaticFileHandler, {'path': './static'}),
    ], debug=True)

    print("Server running at 0.0.0.0:" + str(c.API_SERVER_PORT))
    app.listen(c.API_SERVER_PORT)
    tornado.ioloop.IOLoop.instance().start()
