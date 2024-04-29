from oauth2_provider.validators import RedirectURIValidator

class CustomRedirectURIValidator(RedirectURIValidator):
    def validate(self, value, client=None):
        # Add your custom URI validation logic here
        # Allow certain custom schemes or additional checks
        if value.startswith("at.luftdaten.pmble://"):
            return True
        # Fall back to the default validation for other cases
        return super(CustomRedirectURIValidator, self).validate(value, client)