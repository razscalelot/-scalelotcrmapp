from django.urls import path
from accounts.api.views import *

urlpatterns = [
    path('signup', SignUpUser.as_view(), name="SignUpUser"),
    path('signin', SignInUser.as_view(), name="SignInUser"),
    path('verifyotp', VerifyOtp.as_view(), name="VerifyOtp"),
    path('verifymobile', VerifyMobile.as_view(), name="VerifyMobile"),
    path('forgotpassword', ForgotPassword.as_view(), name="ForgotPassword"),
    path('changepassword', ChangePassword.as_view(), name="ChangePassword"),
    path('getprofile', GetProfile.as_view(), name="GetProfile"),
    path('setprofile', SetProfile.as_view(), name="SetProfile"),

    # path('role', Roles.as_view(), name="RolesList"),
    path('user', Users.as_view(), name="Users"),
    path('department', Departments.as_view(), name="Departments"),
    path('jobwork', JobWorks.as_view(), name="JobWorks"),

    path("<slug:slug>", Main.as_view(), name="Main"),
]
