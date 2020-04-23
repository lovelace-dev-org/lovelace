import magic
import os
import re

from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import HttpResponse

mod_pat = re.compile("[wrx]")

PRIVATE_UPLOAD = getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT)
upload_storage = FileSystemStorage(location=PRIVATE_UPLOAD)


def generate_download_response(fs_path, dl_name=None):

    if getattr(settings, "PRIVATE_STORAGE_X_SENDFILE", False):
        response = HttpResponse()
        response["X-Sendfile"] = fs_path.encode("utf-8")
    else:
        with open(fs_path.encode("utf-8"), "rb") as f:
            response = HttpResponse(f.read())
            
    if dl_name:
        dl_name = dl_name
    else:
        dl_name = os.path.basename(fs_path)
        
    mime = magic.Magic(mime=True)    
    response["Content-Type"] = mime.from_file(fs_path)
    response["Content-Disposition"] = "attachment; filename={}".format(dl_name)
    
    return response
    
def get_file_upload_path(instance, filename):
    return os.path.join("files", "%s" % (filename))

def get_image_upload_path(instance, filename):
    return os.path.join("images", "%s" % (filename))

def get_instancefile_path(included_file, filename):
    return os.path.join(
        "{course}_files".format(course=included_file.course),
        "{filename}".format(filename=filename), # TODO: Versioning?
        # TODO: Language?
    )

def get_file_contents(model_instance):
    file_contents = None
    with open(model_instance.fileinfo.path, 'rb') as f:
        file_contents = f.read()
    return file_contents

def get_testfile_path(instance, filename):
    return os.path.join(
        "{exercise_name}_files".format(exercise_name=instance.exercise.name),
        "{filename}".format(filename=filename), # TODO: Versioning?
        # TODO: Language?
    )

# TODO: Put in UserFileUploadExerciseAnswer's manager?
def get_version(return_file):
    from courses.models import UserFileUploadExerciseAnswer
    return UserFileUploadExerciseAnswer.objects.filter(
        user=return_file.answer.user,
        exercise=return_file.answer.exercise
    ).count()

def get_answerfile_path(return_file, filename): # TODO: Versioning?
    return os.path.join(
        "returnables",
        return_file.answer.instance.slug,
        return_file.answer.user.username,
        return_file.answer.exercise.slug,
        "%04d" % (get_version(return_file)),
        "%s" % (filename)
    )

def get_moss_basefile_path(basefile, filename):
    return os.path.join(
        "{exercise_name}_files".format(exercise_name=basefile.exercise.slug),
        "mossbase",
        "{filename}".format(filename=filename)
    )

def chmod_parse(modstring):
    return int(re.sub(mod_pat, "1", modstring).replace("-", "0"), 2)
