import requests
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


#class RemoteFile(File):

    #def __init__(self, name, storage, mode):
        #self.name = name
        #self._storage = storage
        #self._mode = mode

    #@property
    #def size(self):
        #pass

    #def readlines(self):
        #pass

    #def read(self, num_bytes):
        #pass

    #def write(self, content):
        #pass

    #def close(self):
        #pass


@deconstructible
class RemoteStorage(Storage):

    def __init__(self, location=None, base_url=None, encoding=None):
        self.location = location or settings['REMOTE_STORAGE_LOCATION']

    def size(self, name):
        pass

    def path(self, name):
        pass

    def url(self, name):
        raise ValueError("This file is not accessible via a URL.")

    def open(self, name, mode):
        url = os.path.join(self.location, name)

    def save(self, upload_to, content, max_length):
        db, basename = os.path.split(upload_to)
        url = os.path.join(self.location, db)
        resp = requests.post(
            url,
            data=content,
            headers={
                "x-lovelace-storage-apikey": settings["REMOTE_STORAGE_APIKEY"],
                "metadata": {
                    "filename": basename,
                    "idtype": "snowflake",
                },
            },
        )
        return name

    def delete(self, name):
        pass
















