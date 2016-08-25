from tornado import gen, web, ioloop, queues, httpclient
import tormysql
import logging
import json
from datetime import datetime

class DB:
    database = None

    def __init__(self, max_con=20, host='', port=13306, user='', passwd='', db=''):
        self.pool = tormysql.ConnectionPool(
            max_connections=max_con,
            idle_seconds=7200,
            wait_connection_timeout=3,
            host=host,
            port=port,
            user=user,
            passwd=passwd,
            db=db,
            charset="utf8"
        )
        DB.database = self
        ioloop.IOLoop.instance().add_callback(self.connect)

    @classmethod
    def instance(cls):
        return cls.database

    @gen.coroutine
    def connect(self):
        """
        Before using the driver we alter database charset
        """
        with (yield self.pool.Connection()) as conn:
            with conn.cursor() as cursor:
                yield cursor.execute('ALTER DATABASE CHARACTER SET = "utf8"')
            conn.commit()

    @gen.coroutine
    def send(self, query, params):
        """
        Use this method to alter DB
            param query: format string for query
            param params: actual query parameters
            return: None
        """
        print(datetime.now())
        print("DB_SEND: "+query)
        print("INPUT: "+str(params))
        with (yield self.pool.Connection()) as conn:
            try:
                with conn.cursor() as cursor:
                    yield cursor.execute(query, params)
            except Exception as e:
                logging.exception(e)
                yield conn.rollback()
            else:
                yield conn.commit()

    @gen.coroutine
    def get(self, query, params, dry_output=False):
        """
        Use this method to fetch data from db.
            param query: (str) actual query to be executed
            param dry_output: (bool) switch output style
            return: If dry_output True - output tuple of tuples, otherwise list of dicts
        """
        print(datetime.now())
        print("DB_GET: "+query)
        print("INPUT: "+str(params))
        with (yield self.pool.Connection()) as conn:
            with conn.cursor() as cursor:
                yield cursor.execute(query, params)
                yield conn.commit()
                data = rows = cursor.fetchall()
                cols = [x[0] for x in cursor.description]
        if not dry_output:
            data = []
            for row in rows:
                record = {}
                for prop, val in zip(cols, row):
                    record[prop] = val
                data.append(record)
        raise gen.Return(data)


class DB_OP_Dorm:
    def __init__(self, db):
        self.db = db

    def log(self, method, uid, route):
        try:
            yield self.db.send(
                "INSERT INTO log (method, uid, route) VALUES (%s, %s, %s)", (method, uid, route,)
            )
        except:
            print("Logging Error!")

    def hide_disabled_data(self, u_data):
        data = []
        for user in u_data:
            item = {
                "uid": user['uid'],
                "student_name": user['student_name'],
                "student_nickname": "",
                "student_id": "",
                "class_id": "",
                "email": "",
                "facebook_id": "",
                "detail": "",
                "slogan": ""
            }
            if user["student_nickname_enable"]==1:
                item["student_nickname"] = user["student_nickname"]
            if user["student_id_enable"]==1:
                item["student_id"] = user["student_id"]
            if user["class_id_enable"]==1:
                item["class_id"] = user["class_id"]
            if user["email_enable"]==1:
                item["email"] = user["email"]
            if user["facebook_id_enable"]==1:
                item["facebook_id"] = user["facebook_id"]
            if user["detail_enable"]==1:
                item["detail"] = user["detail"]
            if user["slogan_enable"]==1:
                item["slogan"] = user["slogan"]
            data.append(item)
        return data

    def find_uid(self, method, oid="", **params):
        if method == "d2":
            data = json.loads(oid)
            account = data['username']
        elif method == "fb":
            account = oid
        else:
            account = oid
        data = yield self.db.get(
            "SELECT uid FROM student where type = %s AND account = %s", (method, account,)
        )
        try:
            return data[0]['uid']
        except:
            return -1

    def add_uid(self, method, oid="", **params):
        if method == "d2":
            data = json.loads(oid)
            student_id = data['username']
            if "@" in data['d2_email']:
                student_name = data['d2_email'].split("@")[0]
            else:
                student_name = data['username']
            email = data['d2_email']
            yield self.db.send(
                "INSERT INTO student (type, account, account_detail, student_name, student_id, email) VALUES (%s, %s, %s, %s, %s, %s)", ("d2", student_id, oid, student_name, student_id, email)
            )
        elif method == "fb":
            yield self.db.send(
                "INSERT INTO student (type, account, account_detail, student_name, facebook_id) VALUES (%s, %s, %s, %s, %s)", ("fb", oid, oid, oid, oid)
            )
        else:
            return

    def check_uid_enabled(self, uid, **params):
        data = yield self.db.get(
            "SELECT enable FROM student where uid = %s", (uid,)
        )
        try:
            return data[0]['enable']
        except:
            return 0

    def list_all_building(self, **params):
        data = yield self.db.get(
            "SELECT * FROM building ORDER BY building_id ASC", ()
        )
        return data

    def list_all_floor(self, **params):
        data = yield self.db.get(
            "SELECT DISTINCT b.building_id, r.floor FROM building b, room r where b.building_id = r.building_id order by building_id, floor ASC", ()
        )
        return data

    def list_floor_by_building_id(self, building_id, **params):
        data = yield self.db.get(
            "SELECT DISTINCT floor FROM room where building_id = %s order by floor ASC", (building_id,)
        )
        return data

    def list_all_class(self, **params):
        data = yield self.db.get(
            "SELECT * FROM class ORDER BY class_id ASC", ()
        )
        return data

    def list_all_room(self, **params):
        data = yield self.db.get(
            "SELECT * FROM room ORDER BY room_id ASC", ()
        )
        return data

    def list_all_room_by_room_id(self, room_id, **params):
        data = yield self.db.get(
            "SELECT * FROM room WHERE room_id = %s", (room_id,)
        )
        return data

    def list_all_room_by_building(self, building_id, **params):
        data = yield self.db.get(
            "SELECT * FROM room WHERE building_id = %s ORDER BY room_id ASC", (building_id,)
        )
        return data

    def list_all_room_by_building_floor(self, building_id, floor, **params):
        data = yield self.db.get(
            "SELECT * FROM room WHERE building_id = %s AND floor = %s ORDER BY room_id ASC", (building_id, floor,)
        )
        return data

    def list_all_user_by_room(self, method, room_id, **params):
        if method == "d2":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND room_id = %s ORDER BY uid ASC", (room_id,)
            )
        elif method == "fb":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND type=\'fb\' AND room_id = %s ORDER BY uid ASC", (room_id,)
            )
        else:
            data = []
        return self.hide_disabled_data(data)

    def check_room_exist(self, building_id, room_name, **params):
        data = yield self.db.get(
            "SELECT room_id FROM room WHERE building_id = %s AND room_name = %s", (building_id, room_name,)
        )
        if data == []:
            return -1
        else:
            return data[0]['room_id']

    def add_room(self, building_id, room_name, floor, **params):
        yield self.db.send(
            "INSERT INTO room (room_name, building_id, floor) VALUES (%s, %s, %s)", (room_name, building_id, floor,)
        )

    def list_usage_people(self, **params):
        data = yield self.db.get(
            "SELECT count(*) as count FROM student  WHERE enable = 1", ()
        )
        return data

    def list_my_info(self, uid, **params):
        data = yield self.db.get(
            "SELECT * FROM student WHERE uid = %s", (uid,)
        )
        try:
            del data[0]['account']
        except:
            data = [{}]
        return data[0]

    def modify_my_info(self, uid, attribute, data, **params):
        yield self.db.send(
            "UPDATE student SET " + attribute + " = %s WHERE uid = %s", (data, uid,)
        )

    def list_user_info(self, method, uid, **params):
        if method == "d2":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND uid = %s", (uid,)
            )
        elif method == "fb":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND type=\'fb\' AND uid = %s", (uid,)
            )
        else:
            data = [{}]
        try:
            del data[0]['account']
        except:
            data = [{}]
        return data[0]

    def search(self, method, search_param, **params):
        q = ""
        q_param = ()
        for p in search_param:
            if p[0] == "student_name_fuzzy":
                q = q + " AND student_name like %s"
                q_param = q_param + ("%"+p[1]+"%",)
            elif p[0] == "student_name_accurate":
                q = q + " AND student_name = %s"
                q_param = q_param + (p[1], )
            else:
                q = q + " AND " + p[0] + " = %s"
                q_param = q_param + (p[1], )
        if method == "d2":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1" + q, q_param
            )
        elif method == "fb":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND type=\'fb\'" + q, q_param
            )
        else:
            data = []
        return self.hide_disabled_data(data)

    def search_arg(self, method, fuzzy, param, **params):
        q = ""
        q_param = ()
        for p in param:
            if p[0] == "student_name" and fuzzy:
                q = q + " AND " + p[0] + " like %s"
                q_param = q_param + ("%"+p[1]+"%",)
            else:
                q = q + " AND " + p[0] + " = %s"
                q_param = q_param + (p[1], )
        if method == "d2":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1" + q, q_param
            )
        elif method == "fb":
            data = yield self.db.get(
                "SELECT * FROM student WHERE enable = 1 AND type=\'fb\'" + q, q_param
            )
        else:
            data = []
        return self.hide_disabled_data(data)
