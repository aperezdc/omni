#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the MIT license.

"""
Utilities for dealing with configuration files.
"""

from six import text_type
from schema import Schema, SchemaError
from schema import Optional, And, Or, Use
from functools import wraps
from os import path


_UNDEFINED = object()


def IPv4Address(value):
    from socket import inet_pton, AF_INET, error
    try:
        inet_pton(AF_INET, value)
        return True
    except error:
        return False


def IPv6Address(value):
    from socket import inet_pton, AF_INET6, error
    try:
        inet_pton(AF_INET6, value)
        return True
    except error:
        return False


def schema(func):
    schema = Schema(func())
    @wraps(func)
    def f():
        return schema
    f.validate = lambda d: f().validate(d)
    return f


def Match(regexp, flags=0):
    import re
    match = re.compile(regexp, flags).match
    @wraps(Match)
    def f(value):
        return match(value) is not None
    return f


Password       = text_type
Text           = And(text_type, len)
Identifier     = And(text_type, Match(r"^\w+$"), error="Invalid identifier")
DotIdentifier  = And(text_type, Match(r"^[\w\.]+$"), error="Invalid identifier")
Path           = And(text_type, Use(path.realpath), error="Invalid path")
NaturalNumber  = And(int, lambda v: v >= 0, error="Not a positive number")
PortNumber     = And(int, lambda v: 0 < v <= 65535)
Hostname       = Match(r"^[\w][\.\w]*$")
NetworkAddress = Or(IPv4Address, IPv6Address, Hostname)