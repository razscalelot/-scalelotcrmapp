import jwt
import math
import random
import datetime
from decouple import config


def create_access_token(id, db):
    payload = {
        "id": id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        "iat": datetime.datetime.utcnow(),
        "ext": db
    }
    return jwt.encode(payload, config('SECRET_KEY'), algorithm='HS256')

def createPassword():
    code = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$"
    referCode = ""
    for i in range(8):
        referCode += code[math.floor(random.random() * 39)]
    return referCode

# def authenticate(self, request):
#     token = request.COOKIES.get('jwt')
#
#     if not token:
#         return None
#
#     try:
#         payload = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         raise exceptions.AuthenticationFailed('unauthenticated')
#
#     user = get_user_model().objects.filter(id=payload['user_id']).first()
#
#     if user is None:
#         raise exceptions.AuthenticationFailed('User not found!')
#
#     return (user, None)
