"""
Fixtures for users.
"""

from manhattan.comparable.factory import Blueprint
from mongoframes.factory import makers

from blueprints.users.models import User

__all__ = ['UserFixture']


class UserFixture(Blueprint):

    _frame_cls = User
    _meta_fields = {'password'}

    _instructions = {
        'first_name': makers.Faker('first_name'),
        'last_name': makers.Faker('last_name')
        }

    password = makers.Static('password')
    email = makers.Lambda(
        lambda d: '{0}@getme.co.uk'.format(d['first_name'].lower())
        )
