from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    location = "media/private"
    default_acl = "private"
    file_overwrite = False
    custom_domain = False
    querystring_auth = True
    querystring_expire = getattr(settings, "AWS_QUERYSTRING_EXPIRE", 3600)
