from django.contrib.auth.hashers import make_password, check_password
from accounts.api.authentication import create_access_token, authenticate, getPermission
from rest_framework.views import APIView
from core.response import *
from accounts.api.serializers import *
from decouple import config
from pymongo import MongoClient
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
    def post(self, request):
        data = request.data
        if data['firstname'] != '' and len(data['firstname']) >= 3:
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                    if data['company_name'] != '':
                        existingUser = primary.users.find_one({'$or': [{"mobile": data["mobile"]}, {"email": data["email"]}]})
                        if not existingUser:
                            url = config('FACTOR_URL') + data['mobile'] + '/AUTOGEN'
                            otpSend = requests.get(url, headers)
                            response = json.loads(otpSend.text)
                            if response["Status"] == "Success":
                                customerData = {
                                    "_id": uuid.uuid4().hex,
                                    "db": "",
                                    "mobile": data['mobile'],
                                    "email": data['email'],
                                    "status": True,
                                    "is_demo": True,
                                    "is_approved": True,
                                    "is_active": False,
                                    "createdAt": datetime.now(),
                                    "updatedAt": "",
                                    "createdBy": "",
                                    "updatedBy": "",
                                }
                                getCustomerID = primary.customers.insert_one(customerData).inserted_id
                                obj = {
                                    "_id": uuid.uuid4().hex,
                                    "firstname": data['firstname'],
                                    "password": make_password(data["password"], config("PASSWORD_KEY")),
                                    "mobile": data['mobile'],
                                    "email": data['email'],
                                    "profile_pic": "",
                                    "roleid": "",
                                    "departments": [{"department": "", "jobwork": ""}],
                                    "company_name": data['company_name'],
                                    "parentid": getCustomerID,
                                    "otpVerifyKey": response["Details"],
                                    "status": True,
                                    "is_approved": True,
                                    "is_active": False,
                                    "createdAt": datetime.now(),
                                    "updatedAt": "",
                                    "createdBy": "",
                                    "updatedBy": "",
                                }
                                primary.users.insert_one(obj)
                                return onSuccess("Otp send successfull", response)
                            else:
                                return badRequest("Something went wrong, unable to send otp for given mobile number, please try again.")
                        else:
                            return badRequest("User already exist with same mobile or email, Please try again.")
                    else:
                        return badRequest("Invalid company name, Please try again.")
                else:
                    return badRequest("Invalid email id, Please try again.")
            else:
                return badRequest("Invalid mobile number, Please try again.")
        else:
            return badRequest("Invalid first name, Please try again.")


class VerifyOtp(APIView):
    def post(self, request):
        data = request.data
        if data["key"] != '' and data["otp"] != '' and data["mobile"]:
            userData = primary.users.find_one({"mobile": data["mobile"], "otpVerifyKey": data["key"]})
            if userData:
                url = config("FACTOR_URL") + "VERIFY/" + data["key"] + "/" + data["otp"]
                otpSend = requests.get(url, headers)
                response = json.loads(otpSend.text)
                if response["Status"] == "Success":
                    createSecondaryDB = 'scalelot_' + data['mobile']
                    primary.customers.find_one_and_update({"_id": userData["parentid"]}, {"$set": {"db": createSecondaryDB}})
                    getUserDB = primary.customers.find_one({"_id": userData["parentid"]})
                    secondaryDB = secondary[getUserDB["db"]]
                    collectionsName = ["roles", "permissions", "departments", "jobworks", "custom_fields", "users", "customers"]
                    for collection in collectionsName:
                        secondaryDB.create_collection(collection)

                    roleData = {
                        "_id": uuid.uuid4().hex,
                        "name": "Admin",
                        "status": True
                    }
                    getRole = secondaryDB.roles.insert_one(roleData).inserted_id
                    permission = [
                        {
                            "collectionName": "roles",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }, {
                            "collectionName": "users",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }, {
                            "collectionName": "departments",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }, {
                            "collectionName": "jobworks",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }, {
                            "collectionName": "customfields",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }, {
                            "collectionName": "customers",
                            "create": True,
                            "edit": True,
                            "delete": True,
                            "view": True,
                        }
                    ]
                    permissionsData = [
                        {
                            "_id": uuid.uuid4().hex,
                            "roleid": getRole,
                            "permission": permission,
                            "updatedBy": "",
                            "createdBy": userData["_id"]
                        }
                    ]
                    secondaryDB.permissions.insert_many(permissionsData)
                    primary.users.find_one_and_update({"_id": userData["_id"]}, {"$set": {"roleid": getRole, "mobileverified": True}})
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
            userData = primary.users.find_one({"mobile": data["mobile"], "is_approved": True, "status": True})
            if userData is not None:
                if not userData["mobileverified"]:
                    url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                    otpSend = requests.get(url, headers)
                    response = json.loads(otpSend.text)
                    if response["Status"] == "Success":
                        primary.users.find_one_and_update({"_id": userData["_id"]}, {"$set": {"otpVerifyKey": response["Details"]}})
                        return onSuccess("Otp send successfully", response)
                    else:
                        return badRequest(
                            "Something went wrong, unable to send otp for given mobile number, please try again.")
                else:
                    return badRequest("This mobile number is already register with us, Please try again.")
            else:
                return badRequest("This mobile number is not register with us, Please try again.")
        else:
            return badRequest("Invalid mobile number, Please try again.")


class SignInUser(APIView):
    def post(self, request):
        data = request.data
        if (data['username'] != '' and len(data['username']) == 10 and re.match("[6-9][0-9]{9}", data['username'])) or (data['username'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["username"])):
            if data['password'] != '' and len(data['password']) >= 8:
                userData = primary.users.find_one({"$or": [{"mobile": data["username"]}, {"email": data["username"]}], "status": True, "mobileverified": True})
                print("userData", userData)
                if userData is not None:
                    if userData["mobileverified"]:
                        checkPassword = check_password(data['password'], userData['password'])
                        if checkPassword:
                            primary.users.update_one({"_id": userData["_id"]}, {"$set": {"is_active": True}})
                            token = create_access_token(userData['_id'])
                            return onSuccess("Login successfully", token)
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
            userData = primary.users.find_one({"mobile": data["mobile"], "status": True, "mobileverified": True})
            if userData is not None:
                url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                otpSend = requests.get(url, headers)
                response = json.loads(otpSend.text)
                if response["Status"] == "Success":
                    primary.users.find_one_and_update({"_id": userData["_id"]}, {"$set": {"otpVerifyKey": response["Details"]}})
                    return onSuccess("Otp send successfull", response)
                else:
                    return badRequest("Something went wrong, unable to send otp for given mobile number, please try again.")
            else:
                return badRequest("This mobile number is not register with us, Please try again.")
        else:
            return badRequest("Invalid mobile number, Please try again.")


class ChangePassword(APIView):
    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if len(data["password"]) >= 8 and data["password"] != '':
                    userData = primary.users.find_one({"mobile": data["mobile"], "status": True, "mobileverified": True})
                    if userData is not None:
                        primary.users.find_one_and_update({"_id": userData["_id"]}, {"$set": {"password": make_password(data["password"], config("PASSWORD_KEY"))}})
                        return onSuccess("User password changed successfully!", 1)
                    else:
                        return badRequest("This mobile number is not register with us, Please try again.")
                else:
                    return badRequest("Invalid password lenght to small, Please try again.")
            else:
                return badRequest("Invalid mobile number, Please try again.")
        else:
            return unauthorisedRequest()


class GetProfile(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            print("token", token)
            userData = primary.users.find_one({"_id": token["id"], "mobileverified": True, "is_approved": True, "status": True}, {"password": 0, "roleid": 0, "parentid": 0, "otpVerifyKey": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0, "is_approved": 0})
            if userData is not None:
                return onSuccess("User profile!", userData)
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()


class SetProfile(APIView):
    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            userData = primary.users.find_one({"_id": token["id"], "mobileverified": True, "is_approved": True, "status": True})
            if userData is not None:
                obj = {"$set": {
                    "firstname": data["firstname"],
                    "lastname": data["lastname"],
                    "profile_pic": "",
                    "company_name": data["company_name"]
                }
                }
                updateUser = primary.users.find_one_and_update({"_id": token["id"]}, obj)
                if updateUser:
                    updatedUser = primary.users.find_one({"_id": token["id"]}, {"password": 0, "roleid": 0, "parentid": 0, "otpVerifyKey": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0, "is_approved": 0})
                    return onSuccess("Profile updated successfully!", updatedUser)
                else:
                    return badRequest("Invalid data to update profile, Please try again.")
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()


class Roles(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "roles", 'view', getSecondaryDB['db'])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        rolesData = secondaryDB.roles.find_one({"_id": id})
                        return onSuccess("Roles list", rolesData)
                    except:
                        return badRequest("Invalid role id, Please try again.")

                rolesData = secondaryDB.roles.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Roles list", list(rolesData))
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            if data["id"] == '':
                havePermission = getPermission(getUser["roleid"], "roles", 'create', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingRole = secondaryDB.roles.find_one({"name": data["name"]})
                        if not existingRole:
                            obj = {
                                "_id": uuid.uuid4().hex,
                                "name": data["name"],
                                "status": True,
                                "createdAt": datetime.now(),
                                "createdBy": token["id"]
                            }
                            createRole = secondaryDB.roles.insert_one(obj).inserted_id
                            if createRole:
                                createdRole = secondaryDB.roles.find_one({"_id": createRole})
                                permissionsData = [
                                    {
                                        "_id": uuid.uuid4().hex,
                                        "roleid": createRole,
                                        "permission": data["permission"],
                                        "status": True,
                                        "createdAt": datetime.now(),
                                        "createdBy": token["id"]
                                    }
                                ]
                                secondaryDB.permissions.insert_many(permissionsData)
                                return onSuccess("Role created successfully!", createdRole)
                            else:
                                return badRequest("Invalid data to add role, Please try again.")
                        else:
                            return badRequest("Role name already exist, Please try again.")
                    else:
                        return badRequest("Invalid role name, Please try again.")
                else:
                    return unauthorisedRequest()
            else:
                havePermission = getPermission(getUser["roleid"], "roles", 'edit', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingRole = secondaryDB.roles.find_one({"_id": data["id"]})
                        if existingRole:
                            obj = {"$set": {
                                "name": data["name"],
                                "status": True,
                                "updatedBy": token["id"],
                                "updatedAt": datetime.now(),
                            }
                            }
                            updateRole = secondaryDB.roles.find_one_and_update({"_id": data["id"]}, obj)
                            if updateRole:
                                updatedRole = secondaryDB.roles.find_one({"_id": updateRole["_id"]})
                                permissionsData = [
                                    {"$set": {
                                        "permission": data["permission"],
                                        "updatedBy": token["id"],
                                        "updatedAt": datetime.now(),
                                    }
                                    }
                                ]
                                secondaryDB.permissions.find_one_and_update({"roleid": data["id"]}, permissionsData)
                                return onSuccess("Role updated successfully!", updatedRole)
                            else:
                                pass
                        else:
                            return badRequest("Invalid data to update role, Please try again.")
                    else:
                        return badRequest("Invalid role name, Please try again.")
                else:
                    return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "roles", 'delete', getSecondaryDB["db"])
            if havePermission:
                secondaryDB.roles.find_one_and_delete({"_id": data["id"]})
                secondaryDB.permissions.find_one_and_delete({"roleid": data["id"]})
                return onSuccess("Roles deleted successfully", 1)
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class Departments(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "departments", 'view', getSecondaryDB["db"])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        departmentssData = secondaryDB.departments.find_one({"_id": id})
                        return onSuccess("Departments list", departmentssData)
                    except:
                        return badRequest("Invalid role id, Please try again.")

                departmentssData = secondaryDB.departments.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Departments list", list(departmentssData))
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            if data["id"] == '':
                havePermission = getPermission(getUser["roleid"], "departments", 'create', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingDepartment = secondaryDB.departments.find_one({"name": data["name"]})
                        if not existingDepartment:
                            obj = {
                                "_id": uuid.uuid4().hex,
                                "name": data["name"],
                                "status": True,
                                "createdBy": token["id"],
                                "createdAt": datetime.now(),
                            }
                            createDepartment = secondaryDB.departments.insert_one(obj).inserted_id
                            if createDepartment:
                                createdDepartment = secondaryDB.departments.find_one({"_id": createDepartment})
                                return onSuccess("Department created successfully!", createdDepartment)
                            else:
                                return badRequest("Invalid data to add department, Please try again.")
                        else:
                            return badRequest("Department name already exist, Please try again.")
                    else:
                        return badRequest("Invalid department 0name, Please try again.")
                else:
                    return unauthorisedRequest()
            else:
                havePermission = getPermission(getUser["roleid"], "departments", 'edit', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingDepartment = secondaryDB.departments.find_one({"_id": data["id"]})
                        if existingDepartment:
                            obj = {"$set": {
                                "name": data["name"],
                                "updatedBy": token["id"],
                                "updatedAt": datetime.now(),
                            }
                            }
                            updateDepartment = secondaryDB.departments.find_one_and_update({"_id": data["id"]}, obj)
                            if updateDepartment:
                                updatedDepartment = secondaryDB.departments.find_one({"_id": updateDepartment["_id"]})
                                return onSuccess("Departments updated successfully!", updatedDepartment)
                            else:
                                return badRequest("Invalid data to update departments, Please try again.")
                        else:
                            return badRequest("Invalid data to update departments, Please try again.")
                    else:
                        return badRequest("Invalid departments name, Please try again.")
                else:
                    return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "departments", 'delete', getSecondaryDB["db"])
            if havePermission:
                secondaryDB.departments.find_one_and_delete({"_id": data["id"]})
                return onSuccess("Departments deleted successfully", 1)
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class JobWorks(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "jobworks", 'view', getSecondaryDB["db"])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        jobworksData = secondaryDB.jobworks.find_one({"_id": id})
                        return onSuccess("Job works list", jobworksData)
                    except:
                        return badRequest("Invalid job work id, Please try again.")

                jobworksData = secondaryDB.jobworks.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Job works list", list(jobworksData))
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            if data["id"] == '':
                havePermission = getPermission(getUser["roleid"], "jobworks", 'create', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingJobwork = secondaryDB.jobworks.find_one({"name": data["name"]})
                        if not existingJobwork:
                            obj = {
                                "_id": uuid.uuid4().hex,
                                "name": data["name"],
                                "status": True,
                                "createdAt": datetime.now(),
                                "createdBy": token["id"]
                            }
                            createJobwork = secondaryDB.jobworks.insert_one(obj).inserted_id
                            if createJobwork:
                                createdJobwork = secondaryDB.jobworks.find_one({"_id": createJobwork})
                                return onSuccess("Job work created successfully!", createdJobwork)
                            else:
                                return badRequest("Invalid data to add job work, Please try again.")
                        else:
                            return badRequest("Job work name already exist, Please try again.")
                    else:
                        return badRequest("Invalid job work name, Please try again.")
                else:
                    return unauthorisedRequest()
            else:
                havePermission = getPermission(getUser["roleid"], "jobworks", 'edit', getSecondaryDB["db"])
                if havePermission:
                    if data["name"] != '':
                        existingJobwork = secondaryDB.jobworks.find_one({"_id": data["id"]})
                        if existingJobwork:
                            obj = {"$set": {
                                "name": data["name"],
                                "updatedBy": token["id"],
                                "updatedAt": datetime.now(),
                            }
                            }
                            updateJobwork = secondaryDB.jobworks.find_one_and_update({"_id": data["id"]}, obj)
                            if updateJobwork:
                                updatedJobwork = secondaryDB.jobworks.find_one({"_id": updateJobwork["_id"]})
                                return onSuccess("Job work updated successfully!", updatedJobwork)
                            else:
                                return badRequest("Invalid data to update job work, Please try again.")
                        else:
                            return badRequest("Invalid data to update job work, Please try again.")
                    else:
                        return badRequest("Invalid job work name, Please try again.")
                else:
                    return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "jobworks", 'delete', getSecondaryDB["db"])
            if havePermission:
                secondaryDB.jobworks.find_one_and_delete({"_id": data["id"]})
                return onSuccess("Job work deleted successfully", 1)
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class Users(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "users", 'view', getSecondaryDB["db"])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        usersData = primary.users.find_one({"_id": id})
                        return onSuccess("Users list", usersData)
                    except:
                        return badRequest("Invalid user id, Please try again.")

                usersData = primary.users.find({"parentid": getSecondaryDB["_id"]}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Users list", list(usersData))
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            if data["id"] == '':
                havePermission = getPermission(getUser["roleid"], "users", 'create', getSecondaryDB["db"])
                if havePermission:
                    if data['firstname'] != '' and len(data['firstname']) >= 2:
                        if data['lastname'] != '' and len(data['lastname']) >= 2:
                            if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                                existingUser = primary.users.find_one({"$or": [{"firstname": data["firstname"]}, {"email": data["email"]}]}, {"mobile": data['mobile']})
                                if not existingUser:
                                    obj = {
                                        "_id": uuid.uuid4().hex,
                                        "firstname": data['firstname'],
                                        "lastname": data['lastname'],
                                        "mobile": data['mobile'],
                                        "password": make_password(data["password"], config("PASSWORD_KEY")),
                                        "email": data['email'],
                                        "profile_pic": "",
                                        "parentid": getSecondaryDB["_id"],
                                        "roleid": data["roleid"],
                                        "departments": data["departments"],
                                        "status": True,
                                        "is_active": False,
                                        "createdAt": datetime.now(),
                                        "createdBy": token["id"]
                                    }
                                    createUser = primary.users.insert_one(obj).inserted_id
                                    if createUser:
                                        createdUser = primary.users.find_one({"_id": createUser})
                                        return onSuccess("User created successfully!", createdUser)
                                    else:
                                        return badRequest("Invalid data to add user, Please try again.")
                                else:
                                    return badRequest("User already exist, Please try again.")
                            else:
                                return badRequest("Invalid email id, Please try again.")
                        else:
                            return badRequest("Invalid last name, Please try again.")
                    else:
                        return badRequest("Invalid last name, Please try again.")
                else:
                    return unauthorisedRequest()
            else:
                havePermission = getPermission(getUser["roleid"], "users", 'edit', getSecondaryDB["db"])
                if havePermission:
                    if data['firstname'] != '' and len(data['firstname']) >= 2:
                        if data['lastname'] != '' and len(data['lastname']) >= 2:
                            if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                                existingUser = primary.users.find_one({"_id": data["id"]})
                                if existingUser:
                                    obj = {"$set": {
                                        "firstname": data['firstname'],
                                        "lastname": data['lastname'],
                                        "mobile": data['mobile'],
                                        "email": data['email'],
                                        "profile_pic": "",
                                        "roleid": data["roleid"],
                                        "departments": data["departments"],
                                        "updatedBy": token["id"],
                                        "updatedAt": datetime.now(),
                                    }
                                    }
                                    updateUser = primary.users.find_one_and_update({"_id": data["id"]}, obj)
                                    if updateUser:
                                        updatedUser = primary.users.find_one({"_id": updateUser["_id"]})
                                        return onSuccess("User updated successfully!", updatedUser)
                                    else:
                                        return badRequest("Invalid data to update user, Please try again.")
                                else:
                                    return badRequest("Invalid id to uodate data, Please try again.")
                            else:
                                return badRequest("Invalid email id, Please try again.")
                        else:
                            return badRequest("Invalid last name, Please try again.")
                    else:
                        return badRequest("Invalid last name, Please try again.")
                else:
                    return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "users", 'delete', getSecondaryDB["db"])
            if havePermission:
                primary.users.find_one_and_delete({"_id": data["id"]})
                return onSuccess("User deleted successfully", 1)
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()
