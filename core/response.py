from rest_framework.response import Response
from rest_framework import status

def onSuccess(message, result):
    return Response({
        "Message": message,
        "Data": result,
        "Status": status.HTTP_200_OK,
        "IsSuccess": True
    })


def onError(error):
    return Response({
        "Message": error.message,
        "Data": 0,
        "Status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "IsSuccess": False
    })


def unauthorisedRequest():
    return Response({
        "Message": "Unauthorized Request!",
        "Data": 0,
        "Status": status.HTTP_401_UNAUTHORIZED,
        "IsSuccess": False
    })


def forbiddenRequest():
    return Response({
        "Message": "Access to the requested resource is forbidden! Contact Administrator.",
        "Data": 0,
        "Status": status.HTTP_403_FORBIDDEN,
        "IsSuccess": False
    })


def badRequest(message):
    return Response({
        "Message": message,
        "Data": 0,
        "Status": status.HTTP_400_BAD_REQUEST,
        "IsSuccess": False
    })
