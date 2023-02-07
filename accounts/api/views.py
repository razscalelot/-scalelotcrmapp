from django.contrib.auth.hashers import make_password, check_password
from accounts.api.authentication import createPassword, create_access_token
from rest_framework.views import APIView
from core.response import *
from accounts.api.serializers import *
from decouple import config
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import uuid
import socket
import re
import requests
import json

primary = MongoClient(config('MONGO_CONNECTION_STRING')).scalelotcrmapp
secondary = MongoClient(config('MONGO_CONNECTION_STRING'))
headers = {
    'content-type': 'application/x-www-form-urlencoded'
}


class SignUpUser(APIView):
    def post(self, request) -> dict:
        data = request.data
        if data['name'] != '' and len(data['name']) >= 3:
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                    if data['company_name'] != '':
                        # url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                        # otpSend = requests.get(url, headers)
                        # response = json.loads(otpSend.text)
                        # if response["Status"] == "Success":
                        password = createPassword()
                        hostname = socket.gethostname()
                        ip_address = socket.gethostbyname(hostname)
                        obj = {
                            "id": uuid.uuid4().hex,
                            "name": data['name'],
                            "mobile": data['mobile'],
                            "password": make_password(password, config("PASSWORD_KEY")),
                            "email": data['email'],
                            "company_name": data['company_name'],
                            "is_demo": True,
                            "is_approved": True,
                            "status": True,
                            "mobileverified": True,
                            "free_trial": 15,
                            "ip_address": ip_address,
                            "hostname": hostname,
                            "created_at": datetime.now()
                        }
                        primary.customers.insert_one(obj)
                        return onSuccess("Otp send successfull", {"password": password})
                        # else:
                        #     return badRequest("Something went wrong, unable to send otp for given mobile number, please try again.")
                    else:
                        return badRequest("Invalid company name, Please try again.")
                else:
                    return badRequest("Invalid email id, Please try again.")
            else:
                return badRequest("Invalid mobile number, Please try again.")
        else:
            return badRequest("Invalid your name, Please try again.")


class SignInUser(APIView):
    def post(self, request):
        data = request.data
        if data['mobile'] != '' and len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
            if data['password'] != '' and len(data['password']) >= 8:
                customer = primary.customers.find_one({"mobile": data["mobile"], "is_approved": True, "mobileverified": True, "status": True})
                if customer is not None:
                    checkPassword = check_password(data['password'], customer['password'])
                    if checkPassword:
                        createSecondaryDB = 'scalelot_' + data['mobile']
                        secondaryDB = secondary[createSecondaryDB]
                        secondaryDB.superadmins.insert_one(customer)
                        permissionsData = [
                            {
                                "collectionName": "roles",
                                "insertUpdate": True,
                                "delete": True,
                                "view": True,
                                "_id": ObjectId(),
                                "id": uuid.uuid4().hex,
                            },
                            {
                                "collectionName": "permissions",
                                "insertUpdate": True,
                                "delete": True,
                                "view": True,
                                "_id": ObjectId(),
                                "id": uuid.uuid4().hex,
                            },
                        ]
                        secondaryDB.permissions.insert_many(permissionsData)
                        token = create_access_token(customer['id'], createSecondaryDB)
                        return onSuccess("Login successfull", token)
                    else:
                        return badRequest("Invalid mobile or password, Please try again.")
                else:
                    return badRequest("Invalid mobile or password, Please try again.")
            else:
                return badRequest("Invalid mobile or password, Please try again.")
        else:
            return badRequest("Invalid mobile or password, Please try again.")
