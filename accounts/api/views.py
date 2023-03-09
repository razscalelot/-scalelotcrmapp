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
from bson.objectid import ObjectId

primary = MongoClient(config('MONGO_CONNECTION_STRING')).scalelotcrmapp
secondary = MongoClient(config('MONGO_CONNECTION_STRING'))
headers = {
    'content-type': 'application/x-www-form-urlencoded'
}


def valueEntity(item) -> dict:
    for key, value in item.items():
        if ObjectId.is_valid(value):
            item[key] = str(item[key])
    return item


def valuesEntity(entity) -> list:
    return [valueEntity(item) for item in entity]


def modifiedString(string):
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda word: word.group(0).capitalize(), string)


def createdUpdateUser(user):
    createdByUser = valueEntity(primary.users.find_one({"_id": ObjectId(user["createdBy"])}, {"password": 0, "roleid": 0, "departments": 0, "company_name": 0, "parentid": 0, "otpVerifyKey": 0, "status": 0, "is_approved": 0, "is_active": 0, "createdAt": 0, "updatedAt": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0}))
    updatedByUser = valueEntity(primary.users.find_one({"_id": ObjectId(user["updatedBy"])}, {"password": 0, "roleid": 0, "departments": 0, "company_name": 0, "parentid": 0, "otpVerifyKey": 0, "status": 0, "is_approved": 0, "is_active": 0, "createdAt": 0, "updatedAt": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0}))
    user["createdBy"] = createdByUser
    user["updatedBy"] = updatedByUser
    return user


class SignUpUser(APIView):
    def post(self, request):
        data = request.data
        if data['firstname'] != '' and len(data['firstname']) >= 3:
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                    if data['company_name'] != '':
                        existingUser = primary.users.find_one({'$or': [{"mobile": data["mobile"]}, {"email": data["email"]}]})
                        if not existingUser:
                            # url = config('FACTOR_URL') + data['mobile'] + '/AUTOGEN'
                            # otpSend = requests.get(url, headers)
                            # response = json.loads(otpSend.text)
                            # if response["Status"] == "Success":
                            customerData = {
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
                                "firstname": data['firstname'],
                                "password": make_password(data["password"], config("PASSWORD_KEY")),
                                "mobile": data['mobile'],
                                "email": data['email'],
                                "profile_pic": "",
                                "roleid": ObjectId('63fd1ae19ac2c074d516b79d'),
                                "departments": [{"department": "", "jobwork": ""}],
                                "company_name": data['company_name'],
                                "parentid": ObjectId(getCustomerID),
                                "otpVerifyKey": 1234,  # response["Details"],
                                "status": True,
                                "is_approved": True,
                                "is_active": False,
                                "createdAt": datetime.now(),
                                "updatedAt": "",
                                "createdBy": "",
                                "updatedBy": "",
                            }
                            primary.users.insert_one(obj)
                            return onSuccess("Otp send successfull", {"otp": 1234, "key": 1234})
                        # else:
                        #     return badRequest("Something went wrong, unable to send otp for given mobile number, please try again.")
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
            userData = primary.users.find_one({"mobile": data["mobile"], "otpVerifyKey": 1234})
            if userData:
                # url = config("FACTOR_URL") + "VERIFY/" + data["key"] + "/" + data["otp"]
                # otpSend = requests.get(url, headers)
                # response = json.loads(otpSend.text)
                # if response["Status"] == "Success":
                createSecondaryDB = 'scalelot_' + data['mobile']
                primary.customers.find_one_and_update({"_id": ObjectId(userData["parentid"])}, {"$set": {"db": createSecondaryDB}})
                getUserDB = primary.customers.find_one({"_id": ObjectId(userData["parentid"])})
                secondaryDB = secondary[getUserDB["db"]]
                collectionsName = ["roles", "permissions", "departments", "jobworks", "custom_fields", "users", "customers", "raw_materials", "packagings", "process_trackings", "reports", "main_menu", "forms"]
                for collection in collectionsName:
                    try:
                        secondaryDB.create_collection(collection)
                    except:
                        continue
                    menu = collection.replace("_", " ")
                    menuLower = menu.lower()
                    menuSlug = menuLower.replace(" ", "-")
                    modifiedMenuName = modifiedString(menu)
                    obj = {
                        "menuname": modifiedMenuName,
                        "menuslug": menuSlug,
                        "status": True,
                        "createdAt": datetime.now(),
                        "createdBy": ObjectId(userData["_id"]),
                        "updatedAt": datetime.now(),
                        "updatedBy": ObjectId(userData["_id"]),
                    }
                    secondaryDB.main_menu.insert_one(obj).inserted_id
                primary.users.find_one_and_update({"_id": ObjectId(userData["_id"])}, {"$set": {"mobileverified": True}})
                return onSuccess("User mobile number verified successfully!", 1)
            # else:
            #     return badRequest("Invalid OTP, please try again")
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
                        primary.users.find_one_and_update({"_id": ObjectId(userData["_id"]), }, {"$set": {"otpVerifyKey": response["Details"]}})
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
                if userData is not None:
                    if userData["mobileverified"]:
                        checkPassword = check_password(data['password'], userData['password'])
                        if checkPassword:
                            primary.users.update_one({"_id": ObjectId(userData["_id"])}, {"$set": {"is_active": True}})
                            token = create_access_token(userData["_id"])
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
                # url = config('FACTOR_URL') + (data['mobile']) + '/AUTOGEN'
                # otpSend = requests.get(url, headers)
                # response = json.loads(otpSend.text)
                # if response["Status"] == "Success":
                primary.users.find_one_and_update({"_id": ObjectId(userData["_id"]), }, {"$set": {"otpVerifyKey": 1234}})
                return onSuccess("Otp send successfull", {"key": 1234})
                # else:
                #     return badRequest("Something went wrong, unable to send otp for given mobile number, please try again.")
            else:
                return badRequest("This mobile number is not register with us, Please try again.")
        else:
            return badRequest("Invalid mobile number, Please try again.")


class ChangePassword(APIView):
    def post(self, request):
        token = authenticate(request)
        if token and ObjectId().is_valid(token["_id"]):
            data = request.data
            if len(data['mobile']) == 10 and re.match("[6-9][0-9]{9}", data['mobile']):
                if len(data["password"]) >= 8 and data["password"] != '':
                    userData = primary.users.find_one({"mobile": data["mobile"], "status": True, "mobileverified": True})
                    if userData is not None:
                        primary.users.find_one_and_update({"_id": ObjectId(userData["_id"]), }, {"$set": {"password": make_password(data["password"], config("PASSWORD_KEY"))}})
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
        if token and ObjectId().is_valid(token["_id"]):
            userData = valueEntity(primary.users.find_one({"_id": ObjectId(token["_id"]), "mobileverified": True, "is_approved": True, "status": True}, {"password": 0, "roleid": 0, "parentid": 0, "otpVerifyKey": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0, "is_approved": 0}))
            if userData is not None:
                return onSuccess("User profile!", userData)
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()


class SetProfile(APIView):
    def post(self, request):
        token = authenticate(request)
        if token and ObjectId().is_valid(token["_id"]):
            data = request.data
            userData = primary.users.find_one({"_id": ObjectId(token["_id"]), "mobileverified": True, "is_approved": True, "status": True})
            if userData is not None:
                obj = {"$set": {
                    "firstname": data["firstname"],
                    "lastname": data["lastname"],
                    "profile_pic": "",
                    "company_name": data["company_name"],
                    "updatedAt": datetime.now(),
                    "updatedBy": ObjectId(token["_id"]),
                }
                }
                updateUser = primary.users.find_one_and_update({"_id": ObjectId(token["_id"])}, obj)
                if updateUser:
                    updatedUser = valueEntity(primary.users.find_one({"_id": ObjectId(token["_id"])}, {"password": 0, "roleid": 0, "parentid": 0, "otpVerifyKey": 0, "createdBy": 0, "updatedBy": 0, "mobileverified": 0, "is_approved": 0}))
                    return onSuccess("Profile updated successfully!", updatedUser)
                else:
                    return badRequest("Invalid data to update profile, Please try again.")
            else:
                return badRequest("User not found")
        else:
            return unauthorisedRequest()


class Main(APIView):
    def get(self, request, slug):
        token = authenticate(request)
        if token and ObjectId().is_valid(token["_id"]):
            itemid = request.GET.get("id")
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            formId = request.GET.get("form")
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                getMenu = secondaryDB.main_menu.find_one({"menuslug": slug})
                if getMenu is not None:
                    havePermission = getPermission(ObjectId(getUser["roleid"]), ObjectId(getMenu["_id"]), 'view', getSecondaryDB['db'])
                    if havePermission:
                        menuInCollection = getMenu["menuslug"]
                        collection = menuInCollection.replace("-", "_")
                        getCollection = secondaryDB.list_collection_names(filter={"name": {"$regex": collection}})
                        if formId is not None:
                            if ObjectId().is_valid(formId):
                                finalForm = []
                                getForm = valueEntity(secondaryDB.forms.find_one({"menuid": ObjectId(formId)}))
                                if getForm is not None:
                                    for field in getForm["form"]:
                                        getField = valueEntity(secondaryDB.custom_fields.find_one({"_id": ObjectId(field)}))
                                        usr = createdUpdateUser(getField)
                                        finalForm.append(usr)
                                    getForm = createdUpdateUser(getForm)
                                    getForm["form"] = finalForm
                                    return onSuccess("Record list", getForm)
                            else:
                                return badRequest("Invalid id, Please try again.")
                        if itemid:
                            try:
                                getData = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": ObjectId(itemid)}))
                                finalData = createdUpdateUser(getData)
                                return onSuccess("Record list", finalData)
                            except:
                                return badRequest("Invalid id, Please try again.")
                        finalData = []
                        getData = valuesEntity(secondaryDB[getCollection[0]].find({}).skip(limit * (page - 1)).limit(limit).sort("createdAt", -1))
                        for user in getData:
                            usr = createdUpdateUser(user)
                            finalData.append(usr)
                        return onSuccess("Record list", getData)
                    else:
                        return unauthorisedRequest()
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request, slug):
        token = authenticate(request)
        if token and ObjectId().is_valid(token["_id"]):
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                getMenu = secondaryDB.main_menu.find_one({"menuslug": slug})
                if getMenu is not None:
                    if data["id"] == '' and ObjectId().is_valid(data["id"]):
                        havePermission = getPermission(ObjectId(getUser["roleid"]), ObjectId(getMenu["_id"]), 'create', getSecondaryDB["db"])
                        if havePermission:
                            menuInCollection = getMenu["menuslug"]
                            collection = menuInCollection.replace("-", "_")
                            getCollection = secondaryDB.list_collection_names(filter={"name": {"$regex": collection}})
                            if getCollection[0] == 'main_menu':
                                if data["menuname"] != '':
                                    existingMenu = secondaryDB[getCollection[0]].find_one({"menuname": data["menuname"]})
                                    if not existingMenu:
                                        menuLower = data["menuname"].lower()
                                        menuSlug = menuLower.replace(" ", "-")
                                        modifiedMenuName = modifiedString(data["menuname"])
                                        obj = {
                                            "menuname": modifiedMenuName,
                                            "menuslug": menuSlug,
                                            "status": True,
                                            "createdAt": datetime.now(),
                                            "createdBy": ObjectId(token["_id"]),
                                            "updatedAt": datetime.now(),
                                            "updatedBy": ObjectId(token["_id"]),
                                        }
                                        createData = secondaryDB[getCollection[0]].insert_one(obj).inserted_id
                                        if createData:
                                            secondaryDB.create_collection(menuSlug)
                                            getRoleID = secondaryDB.permissions.find_one({"roleid": ObjectId(getUser["roleid"])})
                                            permission = {
                                                "collectionName": createData,
                                                "create": True,
                                                "edit": True,
                                                "delete": True,
                                                "view": True,
                                                "globalview": True
                                            }
                                            if getRoleID is not None:
                                                getAllPermission = getRoleID["permission"]
                                                getAllPermission.append(permission)
                                                obj = {"$set": {
                                                    "permission": [getAllPermission],
                                                    "updatedAt": datetime.now(),
                                                    "updatedBy": ObjectId(token["_id"]),
                                                }}
                                                secondaryDB.permissions.find_one_and_update({"roleid": ObjectId(getUser["roleid"])}, obj)
                                            else:
                                                permissionsData = {
                                                    "roleid": ObjectId(getUser["roleid"]),
                                                    "permission": [permission],
                                                    "status": True,
                                                    "createdAt": datetime.now(),
                                                    "createdBy": ObjectId(token["_id"]),
                                                    "updatedAt": datetime.now(),
                                                    "updatedBy": ObjectId(token["_id"]),
                                                }
                                                secondaryDB.permissions.insert_one(permissionsData)
                                            createdMenu = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": createData}))
                                            return onSuccess("Record created successfully!", createdMenu)
                                        else:
                                            return badRequest("Invalid data to add record, Please try again.")
                                    else:
                                        return badRequest("Record already exist, Please try again.")
                                else:
                                    return badRequest("Invalid menu name, Please try again.")
                            elif getCollection[0] == 'custom_fields':
                                if data['fieldbelongsto'] != '':
                                    if data['fieldname'] != '':
                                        if data['fieldtype'] != '':
                                            if data['fieldgrid'] != '':
                                                existingField = secondaryDB[getCollection[0]].find_one({"fieldbelongsto": ObjectId(data["fieldbelongsto"]), "fieldname": data["fieldname"]})
                                                if not existingField:
                                                    fieldvalue = re.sub(" |_|-", "", data['fieldname'].lower())
                                                    obj = {
                                                        "fieldbelongsto": ObjectId(data['fieldbelongsto']),
                                                        "fieldname": data['fieldname'],
                                                        "fieldtype": data['fieldtype'],
                                                        "fieldvalue": fieldvalue,
                                                        "fielddefaultvalue": data["fielddefaultvalue"] == '' if '' else data["fielddefaultvalue"],
                                                        "fieldorder": data['fieldorder'] == '' if '' else data['fieldorder'],
                                                        "fieldgrid": data['fieldgrid'],
                                                        "disabled": data['disabled'],
                                                        "required": data['required'],
                                                        "showontable": data["showontable"],
                                                        "status": True,
                                                        "createdAt": datetime.now(),
                                                        "createdBy": ObjectId(token["_id"]),
                                                        "updatedAt": datetime.now(),
                                                        "updatedBy": ObjectId(token["_id"]),
                                                    }
                                                    createField = secondaryDB[getCollection[0]].insert_one(obj).inserted_id
                                                    if createField:
                                                        getForm = secondaryDB.forms.find_one({"menuid": ObjectId(data["fieldbelongsto"])})
                                                        if getForm is not None:
                                                            finalCreateField = getForm["form"]
                                                            finalCreateField.append(ObjectId(createField))
                                                            obj = {"$set": {
                                                                "form": finalCreateField,
                                                                "updatedAt": datetime.now(),
                                                                "updatedBy": ObjectId(token["_id"]),
                                                            }
                                                            }
                                                            secondaryDB.forms.find_one_and_update({"menuid": ObjectId(data["fieldbelongsto"])}, obj)
                                                        else:
                                                            obj = {
                                                                "menuid": ObjectId(data['fieldbelongsto']),
                                                                "form": [createField],
                                                                "status": True,
                                                                "createdAt": datetime.now(),
                                                                "createdBy": ObjectId(token["_id"]),
                                                                "updatedAt": datetime.now(),
                                                                "updatedBy": ObjectId(token["_id"]),
                                                            }
                                                            secondaryDB.forms.insert_one(obj)
                                                        createdField = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": createField}))
                                                        return onSuccess("Record created successfully!", createdField)
                                                    else:
                                                        return badRequest("Invalid data to add record, Please try again.")
                                                else:
                                                    return badRequest("Field already exist, Please try again.")
                                            else:
                                                return badRequest("Invalid field grid, Please try again.")
                                        else:
                                            return badRequest("Invalid email id, Please try again.")
                                    else:
                                        return badRequest("Invalid field name, Please try again.")
                                else:
                                    return badRequest("Invalid field belongs to, Please try again.")
                            else:
                                getForm = secondaryDB.forms.find_one({"menuid": ObjectId(data["formid"])})
                                if getForm is not None:
                                    finalData = {
                                        "status": True,
                                        "createdAt": datetime.now(),
                                        "createdBy": ObjectId(token["_id"]),
                                        "updatedAt": datetime.now(),
                                        "updatedBy": ObjectId(token["_id"]),
                                    }
                                    for field in getForm["form"]:
                                        getField = secondaryDB.custom_fields.find_one({"_id": ObjectId(field)})
                                        for i in data:
                                            if i == getField["fieldvalue"]:
                                                if getField["required"] and data[i] != '':
                                                    existingData = secondaryDB[getCollection[0]].find_one({getField["fieldvalue"]: data[i]})
                                                    if getField["unique"] and not existingData:
                                                        field = getField["fieldvalue"]
                                                        finalData[field] = data[i]
                                                    elif not getField["unique"]:
                                                        field = getField["fieldvalue"]
                                                        finalData[field] = data[i]
                                                    else:
                                                        return badRequest(f"{re.sub('_', ' ', getField['fieldvalue'].title())} already exist, Please try again.")
                                                elif not getField["required"]:
                                                    field = getField["fieldvalue"]
                                                    finalData[field] = data[i]
                                                else:
                                                    return badRequest(f"{re.sub('_', ' ', getField['fieldvalue'].title())} is required, Please try again.")
                                    createData = secondaryDB[getCollection[0]].insert_one(finalData).inserted_id
                                    if createData:
                                        createdData = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": ObjectId(createData)}))
                                        return onSuccess("Record created successfully!", createdData)
                                    else:
                                        return badRequest("Invalid data to create record, Please try again.")
                                else:
                                    return badRequest("Invalid id, Please try again.")
                        else:
                            return unauthorisedRequest()
                    elif data["id"] != '' and ObjectId().is_valid(data["id"]):
                        havePermission = getPermission(ObjectId(getUser["roleid"]), ObjectId(getMenu["_id"]), 'edit', getSecondaryDB["db"])
                        if havePermission:
                            menuInCollection = getMenu["menuslug"]
                            collection = menuInCollection.replace("-", "_")
                            getCollection = secondaryDB.list_collection_names(filter={"name": {"$regex": collection}})
                            if getCollection[0] == 'main_menu':
                                if data["menuname"] != '':
                                    existingData = secondaryDB[getCollection[0]].find_one({"$or": [{"menuname": data["menuname"]}, {"_id": ObjectId(data["id"])}]})
                                    if existingData:
                                        menuLower = data["menuname"].lower()
                                        menuSlug = menuLower.replace(" ", "-")
                                        modifiedMenuName = modifiedString(data["menuname"])
                                        obj = {"$set": {
                                            "menuname": modifiedMenuName,
                                            "menuslug": menuSlug,
                                            "status": True,
                                            "updatedBy": ObjectId(token["_id"]),
                                            "updatedAt": datetime.now(),
                                        }
                                        }
                                        updateData = secondaryDB[getCollection[0]].find_one_and_update({"_id": ObjectId(data["id"])}, obj)
                                        if updateData:
                                            updatedData = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": ObjectId(updateData["_id"])}))
                                            return onSuccess("Record updated successfully!", updatedData)
                                        else:
                                            return badRequest("Invalid data to update record, Please try again.")
                                    else:
                                        return badRequest("Invalid data to update record, Please try again.")
                                else:
                                    return badRequest("Invalid record, Please try again.")
                            elif getCollection[0] == 'custom_fields':
                                if data['fieldbelongsto'] != '':
                                    if data['fieldname'] != '':
                                        if data['fieldtype'] != '':
                                            if data['fieldgrid'] != '':
                                                existingField = secondaryDB[getCollection[0]].find_one({"$or": [{"fieldname": data["fieldname"]}], "_id": {"$ne": ObjectId(data["id"])}})
                                                if not existingField:
                                                    fieldvalue = re.sub(" |_|-", "_", data['fieldname'].lower())
                                                    obj = {"$set": {
                                                        "fieldbelongsto": data['fieldbelongsto'],
                                                        "fieldname": data['fieldname'],
                                                        "fieldtype": data['fieldtype'],
                                                        "fieldvalue": fieldvalue,
                                                        "fielddefaultvalue": data["fielddefaultvalue"],
                                                        "fieldorder": data['fieldorder'],
                                                        "fieldgrid": data['fieldgrid'],
                                                        "disabled": data['disabled'],
                                                        "required": data['required'],
                                                        "showontable": data["showontable"],
                                                        "updatedAt": datetime.now(),
                                                        "updatedBy": ObjectId(token["_id"]),
                                                    }
                                                    }
                                                    updateField = secondaryDB[getCollection[0]].find_one_and_update({"_id": ObjectId(data["id"])}, obj)
                                                    if updateField:
                                                        createdField = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": ObjectId(updateField["_id"])}))
                                                        return onSuccess("Record updated successfully!", createdField)
                                                    else:
                                                        return badRequest("Invalid data to add record, Please try again.")
                                                else:
                                                    return badRequest("Field already exist, Please try again.")
                                            else:
                                                return badRequest("Invalid field grid, Please try again.")
                                        else:
                                            return badRequest("Invalid email id, Please try again.")
                                    else:
                                        return badRequest("Invalid field name, Please try again.")
                                else:
                                    return badRequest("Invalid field belongs to, Please try again.")
                            else:
                                getForm = secondaryDB.forms.find_one({"menuid": ObjectId(data["formid"])})
                                getData = secondaryDB[getCollection[0]].find_one({"_id": ObjectId(data["id"])})
                                if getForm is not None and getData is not None:
                                    getData["updatedAt"] = datetime.now()
                                    getData["updatedBy"] = ObjectId(token["_id"])
                                    finalData = {"$set": getData}
                                    for field in getForm["form"]:
                                        getField = secondaryDB.custom_fields.find_one({"_id": ObjectId(field)})
                                        for i in data:
                                            if i == getField["fieldvalue"]:
                                                if getField["required"] and data[i] != '':
                                                    existingData = secondaryDB[getCollection[0]].find_one({getField["fieldvalue"]: data[i]})
                                                    if getField["unique"] and existingData is not None:
                                                        getData[getField["fieldvalue"]] = data[i]
                                                    elif not getField["unique"]:
                                                        getData[getField["fieldvalue"]] = data[i]
                                                    else:
                                                        return badRequest(f"{re.sub('_', ' ', getField['fieldvalue'].title())} already exist, Please try again.")
                                                elif not getField["required"]:
                                                    getData[getField["fieldvalue"]] = data[i]
                                                else:
                                                    return badRequest(f"Invalid {re.sub('_', ' ', getField['fieldvalue'].title())} to create record, Please try again.")
                                    createData = secondaryDB[getCollection[0]].find_one_and_update({"_id": ObjectId(getData["_id"])}, finalData)
                                    if createData:
                                        createdData = valueEntity(secondaryDB[getCollection[0]].find_one({"_id": ObjectId(data["id"])}))
                                        return onSuccess("Record created successfully!", createdData)
                                    else:
                                        return badRequest("Invalid data to create record, Please try again.")
                                else:
                                    return badRequest("Invalid id, Please try again.")
                        else:
                            return unauthorisedRequest()
                    else:
                        return badRequest("Invalid id to update record, Please try again.")
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request, slug):
        token = authenticate(request)
        if token and ObjectId().is_valid(token["_id"]):
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                getMenu = secondaryDB.main_menu.find_one({"menuslug": slug})
                if getMenu is not None:
                    havePermission = getPermission(ObjectId(getUser["roleid"]), ObjectId(getMenu["_id"]), 'delete', getSecondaryDB["db"])
                    if havePermission:
                        menuInCollection = getMenu["menuslug"]
                        collection = menuInCollection.replace("-", "_")
                        getCollection = secondaryDB.list_collection_names(filter={"name": {"$regex": collection}})
                        if data["id"] != '':
                            existingData = secondaryDB[getCollection[0]].find_one({"_id": ObjectId(data["id"])})
                            if existingData is not None:
                                if getCollection[0] == "custom_fields":
                                    getMenu = secondaryDB.forms.find_one({"form": ObjectId(data["id"])})
                                    getId = getMenu["form"]
                                    getId.remove(data["id"])
                                    secondaryDB.forms.update_one({"_id": ObjectId(getMenu["_id"])}, {"$set": {"form": ObjectId(getId)}})
                                secondaryDB[getCollection[0]].find_one_and_delete({"_id": ObjectId(data["id"])})
                                return onSuccess("Record deleted successfully", 1)
                            else:
                                return badRequest("Invalid id to delete record, Please try again.")
                        else:
                            return badRequest("Invalid id to delete record, Please try again.")
                    else:
                        return unauthorisedRequest()
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class Roles(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "roles", 'view', getSecondaryDB['db'])
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
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                if data["id"] == '':
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "roles", 'create', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingRole = secondaryDB.roles.find_one({"name": data["name"]})
                            if not existingRole:
                                obj = {
                                    "name": data["name"],
                                    "status": True,
                                    "createdAt": datetime.now(),
                                    "createdBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                    "updatedBy": ObjectId(token["_id"]),
                                }
                                createRole = secondaryDB.roles.insert_one(obj).inserted_id
                                if createRole:
                                    createdRole = secondaryDB.roles.find_one({"_id": createRole})
                                    permissionsData = [
                                        {
                                            "roleid": ObjectId(createRole),
                                            "permission": data["permission"],
                                            "status": True,
                                            "createdAt": datetime.now(),
                                            "createdBy": ObjectId(token["_id"]),
                                            "updatedAt": datetime.now(),
                                            "updatedBy": ObjectId(token["_id"]),
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
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "roles", 'edit', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingRole = secondaryDB.roles.find_one({"_id": data["id"]})
                            if existingRole:
                                obj = {"$set": {
                                    "name": data["name"],
                                    "status": True,
                                    "updatedBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                }
                                }
                                updateRole = secondaryDB.roles.find_one_and_update({"_id": data["id"]}, obj)
                                if updateRole:
                                    updatedRole = secondaryDB.roles.find_one({"_id": updateRole["_id"]})
                                    permissionsData = [
                                        {"$set": {
                                            "permission": data["permission"],
                                            "updatedBy": ObjectId(token["_id"]),
                                            "updatedAt": datetime.now(),
                                        }
                                        }
                                    ]
                                    secondaryDB.permissions.find_one_and_update({"roleid": ObjectId(data["id"])}, permissionsData)
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
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "roles", 'delete', getSecondaryDB["db"])
                if havePermission:
                    secondaryDB.roles.find_one_and_delete({"_id": data["id"]})
                    secondaryDB.permissions.find_one_and_delete({"roleid": ObjectId(data["id"])})
                    return onSuccess("Roles deleted successfully", 1)
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class MainMenu(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                menuPermission = getPermission(ObjectId(getUser["roleid"]), "main_menu", 'globalview', getSecondaryDB['db'])
                if menuPermission:
                    id = request.GET.get("id")
                    if id:
                        try:
                            menuData = secondaryDB.mainmenu.find_one({"_id": id})
                            finalData = createdUpdateUser(menuData)
                            return onSuccess("Main menu list", finalData)
                        except:
                            return badRequest("Invalid manu id, Please try again.")

                    finalData = []
                    menusData = secondaryDB.mainmenu.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                    for user in menusData:
                        usr = createdUpdateUser(user)
                        finalData.append(usr)
                    return onSuccess("Main menu list", finalData)
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                if data["id"] == '':
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "mainmenu", 'create', getSecondaryDB["db"])
                    if havePermission:
                        if data["menuname"] != '' and data["roleid"] != '':
                            existingMenu = secondaryDB.mainmenu.find_one({"menuname": data["menuname"]})
                            if not existingMenu:
                                menuLower = data["menuname"].lower()
                                menuSlug = menuLower.replace(" ", "-")
                                modifiedMenuName = modifiedString(data["menuname"])
                                obj = {
                                    "roleid": ObjectId(data["roleid"]),
                                    "menuname": modifiedMenuName,
                                    "menuslug": menuSlug,
                                    "status": True,
                                    "createdAt": datetime.now(),
                                    "createdBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                    "updatedBy": ObjectId(token["_id"]),
                                }
                                createMenu = secondaryDB.mainmenu.insert_one(obj).inserted_id
                                if createMenu:
                                    getRole = secondaryDB.role.find_one({"_id": ObjectId(data['roleid'])})
                                    menu = re.sub(" |_|-", "", data['menuname'])
                                    menuLower = menu.lower()
                                    finalPermissions = []
                                    permissions = data["permission"]
                                    for i in permissions:
                                        per = i["collectionName"] = menuLower
                                        finalPermissions.append(per)
                                    if getRole:
                                        permissionsData = [
                                            {
                                                "roleid": ObjectId(data["roleid"]),
                                                "permission": finalPermissions,
                                                "status": True,
                                                "createdAt": datetime.now(),
                                                "createdBy": ObjectId(token["_id"]),
                                                "updatedBy": ObjectId(token["_id"]),
                                                "updatedAt": datetime.now(),
                                            }
                                        ]
                                        secondaryDB.permissions.insert_many(permissionsData)
                                    else:
                                        permissionsData = [{"$set":
                                            {
                                                "permission": data["permission"],
                                                "updatedBy": ObjectId(token["_id"]),
                                                "updatedAt": datetime.now(),
                                            }
                                        }
                                        ]
                                        secondaryDB.permissions.find_one_and_update({"roleid": ObjectId(data["roleid"])}, permissionsData)

                                    createdMenu = secondaryDB.mainmenu.find_one({"_id": createMenu})
                                    return onSuccess("Menu created successfully!", createdMenu)
                                else:
                                    return badRequest("Invalid data to add menu, Please try again.")
                            else:
                                return badRequest("Menu name already exist, Please try again.")
                        else:
                            return badRequest("Invalid menu name, Please try again.")
                    else:
                        return unauthorisedRequest()
                else:
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "mainmenu", 'edit', getSecondaryDB["db"])
                    if havePermission:
                        if data["menuname"] != '' and ObjectId(data["roleid"]) != '':
                            existingMenu = secondaryDB.mainmenu.find_one({"_id": data["id"]})
                            if existingMenu:
                                menuLower = data["menuname"].lower()
                                menuSlug = menuLower.replace(" ", "-")
                                modifiedMenuName = modifiedString(data["menuname"])
                                obj = {"$set": {
                                    "menuname": modifiedMenuName,
                                    "menuslug": menuSlug,
                                    "status": True,
                                    "updatedBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                }
                                }
                                updateMenu = secondaryDB.mainmenu.find_one_and_update({"_id": data["id"]}, obj)
                                if updateMenu:
                                    updatedMenu = secondaryDB.mainmenu.find_one({"_id": updateMenu["_id"]})
                                    return onSuccess("Menu updated successfully!", updatedMenu)
                                else:
                                    pass
                            else:
                                return badRequest("Invalid data to update menu, Please try again.")
                        else:
                            return badRequest("Invalid menu name, Please try again.")
                    else:
                        return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "mainmenu", 'delete', getSecondaryDB["db"])
                if havePermission:
                    secondaryDB.mainmenu.find_one_and_delete({"_id": data["id"]})
                    return onSuccess("Menu deleted successfully", 1)
                else:
                    return unauthorisedRequest()
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
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "departments", 'view', getSecondaryDB["db"])
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
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                if data["id"] == '':
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "departments", 'create', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingDepartment = secondaryDB.departments.find_one({"name": data["name"]})
                            if not existingDepartment:
                                obj = {
                                    "name": data["name"],
                                    "status": True,
                                    "createdAt": datetime.now(),
                                    "createdBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                    "updatedBy": ObjectId(token["_id"]),
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
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "departments", 'edit', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingDepartment = secondaryDB.departments.find_one({"_id": data["id"]})
                            if existingDepartment:
                                obj = {"$set": {
                                    "name": data["name"],
                                    "updatedBy": ObjectId(token["_id"]),
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
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "departments", 'delete', getSecondaryDB["db"])
                if havePermission:
                    secondaryDB.departments.find_one_and_delete({"_id": data["id"]})
                    return onSuccess("Departments deleted successfully", 1)
                else:
                    return unauthorisedRequest()
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
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "jobworks", 'view', getSecondaryDB["db"])
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
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                if data["id"] == '':
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "jobworks", 'create', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingJobwork = secondaryDB.jobworks.find_one({"name": data["name"]})
                            if not existingJobwork:
                                obj = {
                                    "name": data["name"],
                                    "status": True,
                                    "createdAt": datetime.now(),
                                    "createdBy": ObjectId(token["_id"]),
                                    "updatedAt": datetime.now(),
                                    "updatedBy": ObjectId(token["_id"]),
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
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "jobworks", 'edit', getSecondaryDB["db"])
                    if havePermission:
                        if data["name"] != '':
                            existingJobwork = secondaryDB.jobworks.find_one({"_id": data["id"]})
                            if existingJobwork:
                                obj = {"$set": {
                                    "name": data["name"],
                                    "updatedBy": ObjectId(token["_id"]),
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
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "jobworks", 'delete', getSecondaryDB["db"])
                if havePermission:
                    secondaryDB.jobworks.find_one_and_delete({"_id": data["id"]})
                    return onSuccess("Job work deleted successfully", 1)
                else:
                    return unauthorisedRequest()
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
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "users", 'view', getSecondaryDB["db"])
                if havePermission:
                    id = request.GET.get("id")
                    if id:
                        try:
                            usersData = primary.users.find_one({"_id": id})
                            return onSuccess("Users list", usersData)
                        except:
                            return badRequest("Invalid user id, Please try again.")

                    usersData = primary.users.find({"parentid": ObjectId(getSecondaryDB["_id"])}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                    return onSuccess("Users list", list(usersData))
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()

    def post(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                if data["id"] == '':
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "users", 'create', getSecondaryDB["db"])
                    if havePermission:
                        if data['firstname'] != '' and len(data['firstname']) >= 2:
                            if data['lastname'] != '' and len(data['lastname']) >= 2:
                                if data['email'] != '' and re.match("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$", data["email"]):
                                    existingUser = primary.users.find_one({"$or": [{"firstname": data["firstname"]}, {"email": data["email"]}]}, {"mobile": data['mobile']})
                                    if not existingUser:
                                        obj = {
                                            "firstname": data['firstname'],
                                            "lastname": data['lastname'],
                                            "mobile": data['mobile'],
                                            "password": make_password(data["password"], config("PASSWORD_KEY")),
                                            "email": data['email'],
                                            "profile_pic": "",
                                            "parentid": ObjectId(getSecondaryDB["_id"]),
                                            "roleid": ObjectId(data["roleid"]),
                                            "departments": data["departments"],
                                            "status": True,
                                            "is_active": False,
                                            "createdAt": datetime.now(),
                                            "createdBy": ObjectId(token["_id"]),
                                            "updatedAt": datetime.now(),
                                            "updatedBy": ObjectId(token["_id"]),
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
                    havePermission = getPermission(ObjectId(getUser["roleid"]), "users", 'edit', getSecondaryDB["db"])
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
                                            "roleid": ObjectId(data["roleid"]),
                                            "departments": data["departments"],
                                            "updatedBy": ObjectId(token["_id"]),
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
        else:
            return unauthorisedRequest()

    def delete(self, request):
        token = authenticate(request)
        if token:
            data = request.data
            getUser = primary.users.find_one({"_id": ObjectId(token["_id"])})
            if getUser is not None:
                getSecondaryDB = primary.customers.find_one({"_id": ObjectId(getUser["parentid"])})
                secondaryDB = secondary[getSecondaryDB['db']]
                havePermission = getPermission(ObjectId(getUser["roleid"]), "users", 'delete', getSecondaryDB["db"])
                if havePermission:
                    primary.users.find_one_and_delete({"_id": ObjectId(data["id"])})
                    return onSuccess("User deleted successfully", 1)
                else:
                    return unauthorisedRequest()
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()
