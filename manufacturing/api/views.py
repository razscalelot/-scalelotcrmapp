from accounts.api.authentication import authenticate, getPermission
from rest_framework.views import APIView
from core.response import *
from accounts.api.serializers import *
from decouple import config
from pymongo import MongoClient
from datetime import datetime
import uuid

primary = MongoClient(config('MONGO_CONNECTION_STRING')).scalelotcrmapp
secondary = MongoClient(config('MONGO_CONNECTION_STRING'))
headers = {
    'content-type': 'application/x-www-form-urlencoded'
}


class CustomFields(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "customfields", 'view', getSecondaryDB["db"])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        fieldsData = secondaryDB.customfields.find_one({"_id": id})
                        return onSuccess("Field list", fieldsData)
                    except:
                        return badRequest("Invalid role id, Please try again.")

                fieldsData = secondaryDB.customfields.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Field list", list(fieldsData))
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
                havePermission = getPermission(getUser["roleid"], "customfields", 'create', getSecondaryDB["db"])
                if havePermission:
                    if data['fieldbelongsto'] != '':
                        if data['fieldname'] != '':
                            if data['fieldtype'] != '':
                                if data['fieldgrid'] != '':
                                    existingField = secondaryDB.customfields.find_one({"fieldbelongsto": data["fieldbelongsto"], "fieldname": data["fieldname"]})
                                    if not existingField:
                                        obj = {
                                            "_id": uuid.uuid4().hex,
                                            "fieldbelongsto": data['fieldbelongsto'],
                                            "fieldname": data['fieldname'],
                                            "fieldtype": data['fieldtype'],
                                            "fielddefaultvalue": data["fielddefaultvalue"],
                                            "fieldorder": data['fieldorder'],
                                            "fieldgrid": data['fieldgrid'],
                                            "disabled": data['disabled'],
                                            "required": data['required'],
                                            "showontable": data["showontable"],
                                            "status": True,
                                            "createdAt": datetime.now(),
                                            "createdBy": token["id"]
                                        }
                                        createField = secondaryDB.customfields.insert_one(obj).inserted_id
                                        if createField:
                                            createdField = secondaryDB.customfields.find_one({"_id": createField})
                                            return onSuccess("Field created successfully!", createdField)
                                        else:
                                            return badRequest("Invalid data to add field, Please try again.")
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
                    return unauthorisedRequest()
            else:
                havePermission = getPermission(getUser["roleid"], "customfields", 'edit', getSecondaryDB["db"])
                if havePermission:
                    if data['fieldbelongsto'] != '':
                        if data['fieldname'] != '':
                            if data['fieldtype'] != '':
                                if data['fieldgrid'] != '':
                                    existingField = secondaryDB.customfields.find_one({"_id": data["id"]})
                                    if existingField:
                                        obj = {"$set": {
                                            "fieldbelongsto": data['fieldbelongsto'],
                                            "fieldname": data['fieldname'],
                                            "fieldtype": data['fieldtype'],
                                            "fielddefaultvalue": data["fielddefaultvalue"],
                                            "fieldorder": data['fieldorder'],
                                            "fieldgrid": data['fieldgrid'],
                                            "disabled": data['disabled'],
                                            "required": data['required'],
                                            "showontable": data["showontable"],
                                            "status": True,
                                            "updatedBy": token["id"],
                                            "updatedAt": datetime.now(),
                                        }
                                        }
                                        updateField = secondaryDB.customfields.find_one_and_update({"_id": data["id"]}, obj)
                                        if updateField:
                                            updatedField = secondaryDB.customfields.find_one({"_id": updateField["_id"]})
                                            return onSuccess("Field updated successfully!", updatedField)
                                        else:
                                            return badRequest("Invalid data to update user, Please try again.")
                                    else:
                                        return badRequest("Invalid id to update data, Please try again.")
                                else:
                                    return badRequest("Invalid field grid, Please try again.")
                            else:
                                return badRequest("Invalid email id, Please try again.")
                        else:
                            return badRequest("Invalid field name, Please try again.")
                    else:
                        return badRequest("Invalid field belongs to, Please try again.")
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
            havePermission = getPermission(getUser["roleid"], "customfields", 'delete', getSecondaryDB["db"])
            if havePermission:
                secondaryDB.customfields.find_one_and_delete({"_id": data["id"]})
                return onSuccess("Field deleted successfully", 1)
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()


class Forms(APIView):
    def get(self, request):
        token = authenticate(request)
        if token:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 5))
            data = request.data
            getUser = primary.users.find_one({"_id": token["id"]})
            getSecondaryDB = primary.customers.find_one({"_id": getUser["parentid"]})
            secondaryDB = secondary[getSecondaryDB['db']]
            havePermission = getPermission(getUser["roleid"], "customfields", 'view', getSecondaryDB["db"])
            if havePermission:
                id = request.GET.get("id")
                if id:
                    try:
                        fieldsData = secondaryDB.customfields.find_one({"_id": id})
                        return onSuccess("Field list", fieldsData)
                    except:
                        return badRequest("Invalid role id, Please try again.")

                fieldsData = secondaryDB.customfields.find({}).skip(limit * (page - 1)).limit(limit).sort("_id", 1)
                return onSuccess("Field list", list(fieldsData))
            else:
                return unauthorisedRequest()
        else:
            return unauthorisedRequest()