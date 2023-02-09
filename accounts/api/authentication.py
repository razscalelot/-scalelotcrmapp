import jwt
import math
import random
import datetime
from decouple import config
from core.response import *
from pymongo import MongoClient

primary = MongoClient(config('MONGO_CONNECTION_STRING')).scalelotcrmapp
secondary = MongoClient(config('MONGO_CONNECTION_STRING'))


def create_access_token(id, db, roleid):
    payload = {
        "id": id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=43200),
        "iat": datetime.datetime.utcnow(),
        "ext": db,
        "roleid": roleid
    }
    return jwt.encode(payload, config('SECRET_KEY'), algorithm='HS256')


def createPassword():
    code = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$"
    referCode = ""
    for i in range(8):
        referCode += code[math.floor(random.random() * 39)]
    return referCode


def authenticate(request):
    req = request.META.get('HTTP_AUTHORIZATION', None)
    if req != '' and req is not None:
        token = req.split(" ", 1)[1]
        if not token:
            return False, None

        try:
            payload = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
        except:
            return False, None

        user = primary.customers.find_one({"_id": payload['id']})

        if user is None:
            return False, None

        return user, payload
    else:
        return False, None


def getPermission(roleid, modelname, permissiontype, secondarydb):
    result = secondary[secondarydb].permissions.find_one({"roleid": roleid})
    if result is not None:
        permission = result["permission"]
        for i in permission:
            if i["collectionName"] == modelname:
                if permissiontype == "insertUpdate":
                    if i["insertUpdate"]:
                        return True
                    else:
                        return False
                if permissiontype == "view":
                    if i["view"]:
                        return True
                    else:
                        return False
                if permissiontype == "delete":
                    if i["delete"]:
                        return True
                    else:
                        return False
            else:
                return False
    else:
        return False
