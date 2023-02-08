from django.urls import path
from accounts.api.views import *

urlpatterns = [
    path('signup', SignUpUser.as_view(), name="SignUpUser"),
    path('signin', SignInUser.as_view(), name="SignInUser"),
    path('verifyotp', VerifyOtp.as_view(), name="VerifyOtp"),
    path('verifymobile', VerifyMobile.as_view(), name="VerifyMobile"),
    path('forgotpassword', ForgotPassword.as_view(), name="ForgotPassword"),
    path('changepassword', ChangePassword.as_view(), name="ChangePassword"),
]