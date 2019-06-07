#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `SignorDownloader` class."""

import os
import tempfile
import shutil
from mock import MagicMock

import unittest
from ndex2.nice_cx_network import NiceCXNetwork
from ndexsignorloader.ndexloadsignor import SignorDownloader


class TestSignorDownloader(unittest.TestCase):
    """Tests for `NodeMemberUpdator` class."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_get_pathway_list_file(self):
        dloader = SignorDownloader(None, 'f')
        self.assertEqual(os.path.join('f',
                                      SignorDownloader.PATHWAY_LIST_FILE),
                                      dloader.get_pathway_list_file())

    def test_get_complexes_file(self):
        dloader = SignorDownloader(None, 'f')
        self.assertEqual(os.path.join('f',
                                      SignorDownloader.COMPLEXES_FILE),
                                      dloader.get_complexes_file())
