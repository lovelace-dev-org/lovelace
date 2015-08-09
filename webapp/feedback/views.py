from django.http import HttpResponseNotFound


def content(request, content_slug):
    return HttpResponseNotFound("This page is yet to be implemented")
