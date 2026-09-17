import os
import uuid
from django.utils.deconstruct import deconstructible

@deconstructible
class GenerateSafeFilename:
    def __init__(self, path):
        self.path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        return os.path.join(self.path, filename)
