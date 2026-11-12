from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .wishlist import merge_session_into_user


@receiver(user_logged_in)
def keep_guest_wishlist(sender, request, user, **kwargs):
    """Items a guest saved before logging in move to their account."""
    if request is not None:
        merge_session_into_user(request, user)
