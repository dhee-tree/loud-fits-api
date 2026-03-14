def build_private_media_url(file_field, request=None):
    if not file_field:
        return None

    url = file_field.url
    if request is not None and not url.startswith(("http://", "https://")):
        return request.build_absolute_uri(url)
    return url
