from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import resolve_url


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to override allauth redirects."""
    
    def get_password_change_redirect_url(self, request):
        """Redirect to settings page after password change."""
        return resolve_url('/accounts/settings/')

