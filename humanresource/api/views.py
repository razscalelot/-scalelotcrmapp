from django.contrib.auth.hashers import make_password, check_password
from accounts.api.authentication import createPassword, create_access_token, authenticate
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
                        existingUser = primary.customers.find_one(
                            {'$or': [{"mobile": data["mobile"]}, {"email": data["email"]}]})
                        if not existingUser:
                            password = createPassword()
                            hostname = socket.gethostname()
                            ip_address = socket.gethostbyname(hostname)
                            obj = {
                                "_id": uuid.uuid4().hex,
                                "name": data['name'],
                                "mobile": data['mobile'],
                                "password": make_password(password, config("PASSWORD_KEY")),
                                "email": data['email'],
                                "company_name": data['company_name'],
                                "is_demo": True,
                                "is_approved": True,
                                "status": True,
                                "mobileverified": False,
                                "free_trial": 15,
                                "ip_address": ip_address,
                                "hostname": hostname,
                                "created_at": datetime.now()
                            }
                            url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                            otpSend = requests.get(url, headers)
                            response = json.loads(otpSend.text)
                            if response["Status"] == "Success":
                                createSecondaryDB = 'scalelot_' + data['mobile']
                                secondaryDB = secondary[createSecondaryDB]
                                permissionsData = [
                                    {
                                        "collectionName": "roles",
                                        "insertUpdate": True,
                                        "delete": True,
                                        "view": True,
                                        "_id": uuid.uuid4().hex,
                                    },
                                    {
                                        "collectionName": "permissions",
                                        "insertUpdate": True,
                                        "delete": True,
                                        "view": True,
                                        "_id": uuid.uuid4().hex,
                                    },
                                ]
                                secondaryDB.permissions.insert_many(permissionsData)
                                obj["otpVerifyKey"] = response["Details"]
                                primary.customers.insert_one(obj)
                                return onSuccess("Otp send successfull", {"password": password, "response": response})
                            else:
                                return badRequest(
                                    "Something went wrong, unable to send otp for given mobile number, please try again.")
                        else:
                            return badRequest("User already exist with same mobile or email, Please try again.")
                    else:
                        return badRequest("Invalid company name, Please try again.")
                else:
                    return badRequest("Invalid email id, Please try again.")
            else:
                return badRequest("Invalid mobile number, Please try again.")
        else:
            return badRequest("Invalid your name, Please try again.")


class VerifyOtp(APIView):
    def post(self, request):
        data = request.data
        if data["key"] != '' and data["otp"] != '' and data["mobile"]:
            userData = primary.customers.find_one({"mobile": data["mobile"], "otpVerifyKey": data["key"]})
            if userData:
                url = config("FACTOR_URL") + "VERIFY/" + data["key"] + "/" + data["otp"]
                otpSend = requests.get(url, headers)
                response = json.loads(otpSend.text)
                if response["Status"] == "Success":
                    primary.customers.find_one_and_update({"_id": userData["_id"]},
                                                          {"$set": {"mobileverified": True}})
                    return onSuccess("User mobile number verified successfully!", 1)
                else:
                    return badRequest("Invalid OTP, please try again")
            else:
                return badRequest("Invalid data to verify user mobile number, please try again.")
        else:
            return badRequest("Invalid otp or mobile number to verify user mobile number, please try again.")


class VerifyMobile(APIView):
    def post(self, request):
        data = request.data
        if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
            customer = primary.customers.find_one({"mobile": data["mobile"], "is_approved": True, "status": True})
            if customer is not None:
                url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                otpSend = requests.get(url, headers)
                response = json.loads(otpSend.text)
                if response["Status"] == "Success":
                    primary.customers.find_one_and_update({"_id": customer["_id"]},
                                                          {"$set": {"otpVerifyKey": response["Details"]}})
                    return onSuccess("Otp send successfull", response)
                else:
                    return badRequest(
                        "Something went wrong, unable to send otp for given mobile number, please try again.")
            else:
                return badRequest("This mobile number is not register with us, Please try again.")
        else:
            return badRequest("Invalid mobile number, Please try again.")


class SignInUser(APIView):
    def post(self, request):
        data = request.data
        if data['mobile'] != '' and len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
            if data['password'] != '' and len(data['password']) >= 8:
                customer = primary.customers.find_one({"mobile": data["mobile"], "is_approved": True, "status": True})
                if customer is not None:
                    if customer["mobileverified"]:
                        checkPassword = check_password(data['password'], customer['password'])
                        if checkPassword:
                            getSecondryDB = secondary.get_database('scalelot_' + data["mobile"])
                            if getSecondryDB != '':
                                token = create_access_token(customer['_id'], 'scalelot_' + data["mobile"])
                                return onSuccess("Login successfull", token)
                            else:
                                return badRequest("Invalid mobile or password, Please try again.")
                        else:
                            return badRequest("Invalid mobile or password, Please try again.")
                    else:
                        return badRequest("This mobile number is not verifyed with us, please try again.")
                else:
                    return badRequest("Invalid mobile or password, Please try again.")
            else:
                return badRequest("Invalid mobile or password, Please try again.")
        else:
            return badRequest("Invalid mobile or password, Please try again.")


class ForgotPassword(APIView):
    def post(self, request):
        data = request.data
        if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
            customer = primary.customers.find_one({"mobile": data["mobile"], "status": True})
            if customer is not None:
                url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                otpSend = requests.get(url, headers)
                response = json.loads(otpSend.text)
                if response["Status"] == "Success":
                    primary.customers.find_one_and_update({"_id": customer["_id"]},
                                                          {"$set": {"otpVerifyKey": response["Details"]}})
                    return onSuccess("Otp send successfull", response)
                else:
                    return badRequest(
                        "Something went wrong, unable to send otp for given mobile number, please try again.")
            else:
                return badRequest("This mobile number is not register with us, Please try again.")
        else:
            return badRequest("Invalid mobile number, Please try again.")


class ChangePassword(APIView):
    def post(self, request):
        token, payload = authenticate(request)
        if token:
            data = request.data
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if len(data["password"]) >= 8 and data["password"] != '':
                    customer = primary.customers.find_one({"mobile": data["mobile"], "status": True})
                    if customer is not None:
                        primary.customers.find_one_and_update({"_id": customer["_id"]}, {
                            "$set": {"password": make_password(data["password"], config("PASSWORD_KEY"))}})
                        return onSuccess("User password changed successfully!", 1)
                    else:
                        return badRequest("This mobile number is not register with us, Please try again.")
                else:
                    return badRequest("Invalid password lenght to small, Please try again.")
            else:
                return badRequest("Invalid mobile number, Please try again.")
        else:
            return unauthorisedRequest()


class getProfile(APIView):
    def get(self, request):
        token, payload = authenticate(request)
        if token:
            userData = primary.customers.find_one(
                {"_id": payload["id"], "mobileverified": True, "is_approved": True, "status": True},
                {"password": 0, "ip_address": 0, "hostname": 0, "otpVerifyKey": 0})
            if userData is not None:
                return onSuccess("User profile!", userData)
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()


class setProfile(APIView):
    def post(self, request):
        token, payload = authenticate(request)
        if token:
            data = request.data
            userData = primary.customers.find_one(
                {"_id": payload["id"], "mobileverified": True, "is_approved": True, "status": True},
                {"password": 0, "ip_address": 0, "hostname": 0, "otpVerifyKey": 0})
            if userData is not None:
                obj = {"$set": {
                    "name": data["name"],
                    "company_name": data["company_name"]
                }
                }
                updateUser = primary.customers.find_one_and_update({"_id": payload["id"]}, obj)
                if updateUser:
                    updatedUser = primary.customers.find_one(
                        {"_id": payload["id"]},
                        {"password": 0, "ip_address": 0, "hostname": 0, "otpVerifyKey": 0})
                    return onSuccess("Profile updated successfully!", updatedUser)
                else:
                    return badRequest("Invalid data to update profile, Please try again.")
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()
