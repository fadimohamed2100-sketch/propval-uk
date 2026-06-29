"""
Shared rate limiter instance.

Kept in its own module (rather than defined in main.py) so route files can
import it directly without a circular import, since main.py imports the
route modules.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Good enough for now - if this ever needs to be keyed
# per signed-in user instead (more precise, since IPs can be shared on
# corporate/mobile networks), swap get_remote_address for a function that
# reads the Clerk user ID from the request, falling back to IP for
# unauthenticated routes.
limiter = Limiter(key_func=get_remote_address)
