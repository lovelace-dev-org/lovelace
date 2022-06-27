import base64
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
    """
    Reads the contents of a file from disc and wraps it into an HttpResponse
    using either the message body for the payload, or using the X-Sendfile
    header if the it's been enabled. Content type will be determined by the
    magic module. Optionally a name suggestion for the file can be given as
    dl_name, otherwise the file's base name on disc will be used.
    """

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
    """
    Returns the upload sub path for media files
    """

    return os.path.join("files", "%s" % (filename))

def get_image_upload_path(instance, filename):
    """
    Returns the upload sub path for media images
    """

    return os.path.join("images", "%s" % (filename))

def get_instancefile_path(included_file, filename):
    """
    Returns the path for a file within a specific instance.
    """
    
    return os.path.join(
        "{course}_files".format(course=included_file.course),
        "{filename}".format(filename=filename), # TODO: Versioning?
        # TODO: Language?
    )

def get_file_contents(model_instance):
    """
    Gets the contents of a file as a byte string.
    """

    file_contents = None
    with open(model_instance.fileinfo.path, 'rb') as f:
        file_contents = f.read()
    return file_contents

def get_file_contents_b64(model_instance):
    bytes = get_file_contents(model_instance)
    return base64.b64encode(bytes).decode("utf-8")

def get_testfile_path(instance, filename):
    """
    Gets the path for exercise files.
    """

    return os.path.join(
        "{exercise_name}_files".format(exercise_name=instance.exercise.name),
        "{filename}".format(filename=filename), # TODO: Versioning?
        # TODO: Language?
    )

# TODO: Put in UserFileUploadExerciseAnswer's manager?
def get_version(return_file):
    """
    Gets the versioning number for the submitted answer. Basically just an
    autoincrement. 
    """

    from courses.models import UserFileUploadExerciseAnswer
    return UserFileUploadExerciseAnswer.objects.filter(
        user=return_file.answer.user,
        exercise=return_file.answer.exercise
    ).count()

def get_answerfile_path(return_file, filename): # TODO: Versioning?
    """
    Forms the path for submitted answer files. The path consists of
    instance, user, exercise, version number (four digit autoincrement), and
    finally the filename.
    """

    return os.path.join(
        "returnables",
        return_file.answer.instance.slug,
        return_file.answer.user.username,
        return_file.answer.exercise.slug,
        "%04d" % (get_version(return_file)),
        "%s" % (filename)
    )

def get_moss_basefile_path(basefile, filename):
    """
    Forms the path for moss base files. 
    """
    return os.path.join(
        "{exercise_name}_files".format(exercise_name=basefile.exercise.slug),
        "mossbase",
        "{filename}".format(filename=filename)
    )

def chmod_parse(modstring):
    """
    Parses a chmod string of the 9 character unix format into an integer by
    turning it into a binary string, and then converting.
    """

    return int(re.sub(mod_pat, "1", modstring).replace("-", "0"), 2)

