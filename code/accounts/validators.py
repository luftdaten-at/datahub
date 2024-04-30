from oauthlib.oauth2 import RequestValidator

class CustomOAuth2Validator(RequestValidator):
    def __init__(self, *args, **kwargs):
        super(CustomOAuth2Validator, self).__init__(*args, **kwargs)
        self.allowed_schemes = ['http', 'https', 'at.luftdaten.pmble']

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        from urllib.parse import urlparse
        uri = urlparse(redirect_uri)
        if uri.scheme in self.allowed_schemes:
            return super(CustomOAuth2Validator, self).validate_redirect_uri(client_id, redirect_uri, request, *args, **kwargs)
        return False