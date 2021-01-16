from manhattan.users.models import BaseUser, BaseUserSession

__all__ = ['User']


class User(BaseUser):

    _indexes = BaseUser._recommended_indexes + []

    @classmethod
    def get_session_cls(cls):
        return UserSession


User.listen('insert', User._on_upsert)
User.listen('update', User._on_upsert)
User.listen('delete', User._on_delete)


class UserSession(BaseUserSession):

    _indexes = BaseUserSession._recommended_indexes + []
