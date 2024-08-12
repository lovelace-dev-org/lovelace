import json
import logging
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import courses.models as cm
from api.utils import management_api

# Create your views here.

decorators = [management_api, csrf_exempt]
logger = logging.getLogger(__name__)

@method_decorator(decorators, name="dispatch")
class UserCollection(View):

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=415)

        try:
            user = cm.User(
                username=data["username"],
                email=data["email"],
                password=make_password(data["password"]),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
            profile = cm.UserProfile(
                student_id=data["student_id"],
                study_program=data.get("program"),
                enrollment_year=data.get("enrollment_year")
            )
        except KeyError as e:
            logger.warning(f"Missing key in API request: {e}")
            return HttpResponse(status=400)

        try:
            user.save()
            profile.user = user
            profile.save()
        except Exception as e:
            logger.warning(f"Unable to create user: {e}")
            return HttpResponse(status=400)

        return HttpResponse(status=201)
