import magic
import os

from django.conf import settings
from django.http import HttpResponse

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
    