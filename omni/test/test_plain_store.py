#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2014 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

from ..stores import plain
from .. import store
from textwrap import dedent
from six import StringIO
import unittest


class StringIOWithContext(StringIO):
    def __enter__(self):
        return self
    def __exit__(self, type_, value, traceback):
        pass


class TestPlainStoreUnimplementeds(unittest.TestCase):

    def test_format_crypt_password(self):
        f = plain.BaseFileFormat(lambda mode: None)
        with self.assertRaises(NotImplementedError):
            f.crypt_password("user", "pass")


class TestPlainStoreFileFormat(unittest.TestCase):

    def setUp(self):
        self.last_io = None

    def tearDown(self):
        self.last_io = None

    def userdb_string(self, data):
        def open_data(mode):
            if mode == "r":
                self.last_io = \
                        StringIOWithContext(dedent(data))
            else:
                self.last_io = StringIOWithContext()
            return self.last_io
        return plain.PlainFileFormat(open_data)

    data01 = u"""\
    bob:b0b
    alice:4l1c3
    """

    def test_user_list(self):
        with self.userdb_string(self.data01) as db:
            self.assertEqual(list(db.users), ["bob", "alice"])

    def test_user_exists(self):
        with self.userdb_string(self.data01) as db:
            self.assertTrue("bob" in db)
            self.assertTrue(db.__contains__("bob"))
            self.assertFalse("peter" in db)
            self.assertFalse(db.__contains__("peter"))

    def test_user_get(self):
        with self.userdb_string(self.data01) as db:
            self.assertTrue(db["bob"])
            self.assertTrue(len(db["bob"]) > 0)
            self.assertEqual("b0b", db["bob"])

    def test_user_add(self):
        with self.userdb_string(self.data01) as db:
            db.add("andrew", "andr3w")
            self.assertTrue("andrew" in db)
            self.assertEqual("andr3w", db["andrew"])
        expected = dedent(self.data01).strip()
        expected += "\nandrew:andr3w\n"
        self.assertEqual(expected, self.last_io.getvalue())

    def test_user_add_with_extrainfo(self):
        with self.userdb_string(self.data01) as db:
            db.add("andrew", "andr3w", "Some extra, ignored info")
            self.assertTrue("andrew" in db)
            self.assertEqual("andr3w", db["andrew"])
        expected = dedent(self.data01).strip()
        expected += "\nandrew:andr3w:Some extra, ignored info\n"
        self.assertEqual(expected, self.last_io.getvalue())

    def test_user_add_existing(self):
        with self.userdb_string(self.data01) as db:
            with self.assertRaises(KeyError):
                db.add("bob", "meh")

    def test_user_delete(self):
        with self.userdb_string(self.data01) as db:
            db.delete("bob")
            self.assertFalse("bob" in db)
        self.assertEqual("alice:4l1c3\n", self.last_io.getvalue())

    def test_user_delete_nonexisting(self):
        with self.userdb_string(self.data01) as db:
            with self.assertRaises(KeyError):
                db.delete("peter")
        expected = dedent(self.data01)
        self.assertEqual(expected, self.last_io.getvalue())

    def test_user_crypt_password(self):
        with self.userdb_string(self.data01) as db:
            self.assertEqual("b0b", db.crypt_password("bob", "b0b", db["bob"]))

    data02 = u"""\
    peter:p3t3r:Extra info
    bob:b0b:
    alice:4l1c3
    """

    def test_extrainfo_roundtrip(self):
        with self.userdb_string(self.data02) as db:
            pass
        self.assertEqual(dedent(self.data02), self.last_io.getvalue())

    def test_list_usernames(self):
        with self.userdb_string(self.data02) as db:
            self.assertEqual(["alice", "bob", "peter"], list(db.users))


class TestHtpasswdStoreFormat(unittest.TestCase):

    def setUp(self):
        self.last_io = None

    def tearDown(self):
        self.last_io = None

    def userdb_string(self, data, method):
        m = plain._crypt_methods.get(method, None)
        if m is None:
            self.skipTest(("Crypt method '{}' is not supported by this"
                " Python version").format(method))
        def open_data(mode):
            if mode == "r":
                self.last_io = StringIOWithContext(dedent(data))
            else:
                self.last_io = StringIOWithContext()
            return self.last_io
        return plain.HtpasswdFileFormat(open_data, m)


    # Generated with: printf "alice:$(openssl passwd -crypt mirror)" 
    data01 = (u"""\
    alice:su7aWQyEG4lo."
    """, "crypt")

    def test_user_crypt_check_password(self):
        with self.userdb_string(*self.data01) as db:
            self.assertEqual(db["alice"],
                    db.crypt_password("alice", "mirror", db["alice"]))

    def test_user_crypt_check_password_invalid(self):
        with self.userdb_string(*self.data01) as db:
            self.assertNotEqual(db["alice"],
                    db.crypt_password("alice", "hatter", db["alice"]))

    def test_user_crypt_newpassword(self):
        with self.userdb_string(*self.data01) as db:
            old_crypted_pw = db["alice"]
            new_crypted_pw = db.crypt_password("alice", "mirror")
            # If we don't pass the salt (or the existing crypted password),
            # a new crupted password one will be created with a new salt.
            self.assertNotEqual(old_crypted_pw, new_crypted_pw)

    def test_list_usernames(self):
        with self.userdb_string(*self.data01) as db:
            self.assertEqual(["alice"], list(db.users))


class TestPlainStoreInstatiation(unittest.TestCase):

    valid_confs = (
        { "path": "path/to/passwd" },
        { "path": "path/to/passwd", "format": "plain" },
        { "path": "path/to/passwd", "format": "htpasswd" },
        { "path": "path/to/passwd", "format": "htpasswd", "method": "crypt" },
        # The configuration dictionary is not strictly checked, and keys
        # which are of not interest for instantiation are just skipped over.
        { "path": "path/to/passwd", "pi": 3.14 },
    )

    def test_from_valid_conf(self):
        for conf in self.valid_confs:
            s = plain.from_config(conf)
            self.assertTrue(isinstance(s, store.Base))

    invalid_confs = (
        # No "path" key.
        { },
        # Invalid "format" values.
        { "path": "path/to/passwd", "format": "" },
        { "path": "path/to/passwd", "format": 42 },
        { "path": "path/to/passwd", "format": True },
        { "path": "path/to/passwd", "format": 3.14 },
        { "path": "path/to/passwd", "format": "bogus" },
        # Invalid "crypt" methods for htpasswd format
        { "path": "path/to/passwd", "format": "htpasswd", "method": "" },
        { "path": "path/to/passwd", "format": "htpasswd", "method": 42 },
        { "path": "path/to/passwd", "format": "htpasswd", "method": True },
        { "path": "path/to/passwd", "format": "htpasswd", "method": 3.14 },
        { "path": "path/to/passwd", "format": "htpasswd", "method": "bogus" },
    )

    def test_from_invalid_conf(self):
        for conf in self.invalid_confs:
            with self.assertRaises(Exception):
                s = plain.from_config(conf)

    def test_find_store(self):
        self.assertEqual(plain, store.find("plain"))


class TestablePlainStore(plain.PlainStore):
    def __init__(self, data, path, format_, *fargs):
        super(TestablePlainStore, self).__init__(path, format_, *fargs)
        self._data = data

    def _open_file(self, mode):
        if mode == "r":
            self.last_io = StringIOWithContext(dedent(self._data))
        else:
            self.last_io = StringIOWithContext()
        return self.last_io


class TestPlainStoreAuthentication(unittest.TestCase):

    plain_data = TestPlainStoreFileFormat.data01
    crypt_data = TestHtpasswdStoreFormat.data01[0]

    def test_plain_authenticate_success(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertTrue(s.authenticate("bob", "b0b"))

    def test_plain_authenticate_failure(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertFalse(s.authenticate("bob", "badpass"))

    def test_plain_list_usernames(self):
        s = TestablePlainStore(self.plain_data, "path/to/file",
                plain.PlainFileFormat)
        self.assertEqual(["alice", "bob"], list(sorted(s.usernames())))
