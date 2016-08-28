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

    def list_all_class(self, **params):
        data = yield self.db.get(
            "SELECT * FROM class ORDER BY class_id ASC", ()
        )
        return data

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
            "INSERT INTO room (building_id, room_name, floor) VALUES (%s, %s, %s)", (building_id, room_name, floor,)
        )

    def list_my_info(self, uid, **params):
        data = yield self.db.get(
            "SELECT * FROM student s, room r WHERE uid = %s AND s.room_id = r.room_id", (uid,)
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

    def search(self, search_param, **params):
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
        u_data = yield self.db.get(
            "SELECT * FROM student s, room r WHERE s.room_id = r.room_id AND enable = 1" + q, q_param
        )
        data = []
        USER = {
            "uid": "",
            "student_id": "",
            "student_name": "",
            "student_nickname": "",
            "class_id": "",
            "building_id": "",
            "room_name": "",
            "email": "",
            "facebook_id": "",
            "slogan": "",
            "detail": "",
        }
        for user in u_data:
            single_user = USER
            single_user['uid'] = user['uid']
            single_user['student_name'] = user['student_name']
            if user['student_id_enable']==1:
                single_user['student_id'] = user['student_id']
            if user['student_nickname_enable']==1:
                single_user['student_nickname'] = user['student_nickname']
            if user['class_id_enable']==1:
                single_user['class_id'] = user['class_id']
            if user['room_id_enable']==1:
                single_user['building_id'] = user['building_id']
                single_user['room_name'] = user['room_name']
            if user['email_enable']==1:
                single_user['email'] = user['email']
            if user['facebook_id_enable']==1:
                single_user['facebook_id'] = user['facebook_id']
            if user['slogan_enable']==1:
                single_user['slogan'] = user['slogan']
            if user['detail_enable']==1:
                single_user['detail'] = user['detail']
            data.append(single_user)
        return data

    def list_usage_people(self, **params):
        data = yield self.db.get(
            "SELECT count(*) as count FROM student  WHERE enable = 1", ()
        )
        return data
