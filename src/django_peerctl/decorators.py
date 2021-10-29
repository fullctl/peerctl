import django.http
import reversion


class create_revision:
    """
    Same as `reversion.create_revision` but automatically set
    reversion user from request
    """

    def __init_(self):
        pass

    def __call__(self, fn):
        @reversion.create_revision()
        def wrapper(*args, **kwargs):
            if isinstance(args[0], django.http.HttpRequest):
                self = None
                request = args[0]
            else:
                self = args[0]
                request = args[1]

            if request.user:
                reversion.set_user(request.user)
            return fn(*args, **kwargs)

        return wrapper
