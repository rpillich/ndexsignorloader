#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `LoadSignorIntoNDex` class."""

import os
import tempfile
import shutil

import unittest
from ndexsignorloader.ndexloadsignor import LoadSignorIntoNDEx
from ndexsignorloader import ndexloadsignor
from ndex2.nice_cx_network import NiceCXNetwork


class FakeArgs(object):
    pass


class TestLoadSignorIntoNDex(unittest.TestCase):
    """Tests for `LoadSignorIntoNDex` class."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_parse_config(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cfile = os.path.join(temp_dir, 'conf')
            with open(cfile, 'w') as f:
                f.write('[hi]\n')
                f.write('user=theuser\n')
                f.write('password=thep\n')
                f.write('server=thes\n')
            fargs = FakeArgs()
            fargs.conf = cfile
            fargs.profile = 'hi'
            fargs.datadir = temp_dir
            fargs.visibility = 'PUBLIC'
            loader = LoadSignorIntoNDEx(fargs, None)
            loader._parse_config()
            self.assertEqual('theuser', loader._user)
            self.assertEqual('thep', loader._pass)
            self.assertEqual('thes', loader._server)
        finally:
            shutil.rmtree(temp_dir)

    def test_get_user_agent(self):
        fargs = FakeArgs()
        fargs.conf = '/ho'
        fargs.profile = 'hi'
        fargs.datadir = '/'
        fargs.visibility = 'PUBLIC'
        fargs.version = '0.3.0'
        loader = LoadSignorIntoNDEx(fargs, None)
        res = loader._get_user_agent()
        self.assertEqual('ndexsignorloader/0.3.0', res)

    def test_set_edgecollapse_notes_with_edgecollapse_true(self):
        fargs = FakeArgs()
        fargs.conf = '/ho'
        fargs.profile = 'hi'
        fargs.datadir = '/'
        fargs.visibility = 'PUBLIC'
        fargs.edgecollapse = True
        loader = LoadSignorIntoNDEx(fargs, None)
        net = NiceCXNetwork()
        loader._set_edgecollapse_notes(net)
        res = net.get_network_attribute(ndexloadsignor.NOTES_ATTRIB)
        self.assertTrue('Edges have been' in res['v'])

    def test_set_edgecollapse_notes_with_edgecollapse_false(self):
        fargs = FakeArgs()
        fargs.conf = '/ho'
        fargs.profile = 'hi'
        fargs.datadir = '/'
        fargs.visibility = 'PUBLIC'
        fargs.edgecollapse = False
        loader = LoadSignorIntoNDEx(fargs, None)
        net = NiceCXNetwork()
        loader._set_edgecollapse_notes(net)
        res = net.get_network_attribute(ndexloadsignor.NOTES_ATTRIB)
        self.assertEqual(None, res)

    def test_wasderivedfrom(self):
        fargs = FakeArgs()
        fargs.conf = 'hi'
        fargs.profile = 'profile'
        fargs.datadir = '/foo'
        fargs.visibility = 'PUBLIC'

        loader = LoadSignorIntoNDEx(fargs, None)
        net = NiceCXNetwork()
        loader._set_wasderivedfrom(net, 'foo')
        res = net.get_network_attribute(ndexloadsignor.DERIVED_FROM_ATTRIB)
        self.assertEqual('https://signor.uniroma2.it/pathway_browser.php?'
                         'organism=&pathway_list=foo', res['v'])

        # try with is_full_pathway false
        net = NiceCXNetwork()
        loader._set_wasderivedfrom(net, 'foo',
                                   is_full_pathway=False)
        res = net.get_network_attribute(ndexloadsignor.DERIVED_FROM_ATTRIB)
        self.assertEqual('https://signor.uniroma2.it/pathway_browser.php?'
                         'organism=&pathway_list=foo', res['v'])

        # try with is_full_pathway true
        net = NiceCXNetwork()
        loader._set_wasderivedfrom(net, 'foo',
                                   is_full_pathway=True)
        res = net.get_network_attribute(ndexloadsignor.DERIVED_FROM_ATTRIB)
        self.assertEqual('https://signor.uniroma2.it', res['v'])

    def test_set_iconurl(self):
        fargs = FakeArgs()
        fargs.conf = 'hi'
        fargs.profile = 'profile'
        fargs.datadir = '/foo'
        fargs.iconurl = 'hi'
        fargs.visibility = 'PUBLIC'

        loader = LoadSignorIntoNDEx(fargs, None)
        net = NiceCXNetwork()
        loader._set_iconurl(net)
        res = net.get_network_attribute('__iconurl')
        self.assertEqual('hi', res['v'])

    def test_set_type(self):
        fargs = FakeArgs()
        fargs.conf = 'hi'
        fargs.profile = 'profile'
        fargs.datadir = '/foo'
        fargs.visibility = 'PUBLIC'

        loader = LoadSignorIntoNDEx(fargs, None)

        net = NiceCXNetwork()

        # test default
        net.set_name('foo')
        loader._set_type(net)
        res = net.get_network_attribute('networkType')
        self.assertEqual(['pathway', 'Signalling Pathway'], res['v'])

        # test disease pathway
        net.set_name('fsgs')
        loader._set_type(net)
        res = net.get_network_attribute('networkType')
        self.assertEqual(['pathway', 'Disease Pathway'], res['v'])

        # test cancer pathway
        net.set_name('prostate cancer')
        loader._set_type(net)
        res = net.get_network_attribute('networkType')
        self.assertEqual(['pathway', 'Cancer Pathway'], res['v'])

        #test interactome True
        net.set_name('some name')
        loader._set_type(net, is_human_fullpathway=True)
        res = net.get_network_attribute('networkType')
        self.assertEqual(['interactome', 'pathway',
                          'Signalling Pathway'], res['v'])
