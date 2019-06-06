#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `NodeCompartmentUpdator` class."""

import os
import tempfile
import shutil

import unittest
from ndex2.nice_cx_network import NiceCXNetwork
from ndexsignorloader.ndexloadsignor import NodeCompartmentUpdator


class TestNodeCompartmentUpdator(unittest.TestCase):
    """Tests for `UpdatePrefixesForNodeRepresents` class."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_get_description(self):
        updator = NodeCompartmentUpdator()
        self.assertEqual('Replace any empty node compartment attribute '
                         'values with cytoplasm',
                         updator.get_description())

    def test_update_network_is_none(self):
        updator = NodeCompartmentUpdator()
        self.assertEqual(['network is None'],
                         updator.update(None))

    def test_update_network_empty(self):
        updator = NodeCompartmentUpdator()
        net = NiceCXNetwork()
        self.assertEqual([],
                         updator.update(net))

    def test_update_network_containing_all_types(self):
        updator = NodeCompartmentUpdator()
        net = NiceCXNetwork()

        comp_attr = NodeCompartmentUpdator.COMPARTMENT
        no_attr = net.create_node('somenode', node_represents='rep1')

        e_attr = net.create_node('somenode2',
                                 node_represents='uniprot:rep2')
        net.set_node_attribute(e_attr,
                               NodeCompartmentUpdator.COMPARTMENT,
                               '')

        o_attr = net.create_node('somenode2',
                                 node_represents='uniprot:rep2')
        net.set_node_attribute(o_attr,
                               NodeCompartmentUpdator.COMPARTMENT,
                               'blah')

        self.assertEqual(['Node 0 did not have compartment attribute. Setting to cytoplasm'],
                         updator.update(net))

        self.assertEqual(NodeCompartmentUpdator.CYTOPLASM,
                         net.get_node_attribute(no_attr, comp_attr)['v'])

        self.assertEqual(NodeCompartmentUpdator.CYTOPLASM,
                         net.get_node_attribute(e_attr, comp_attr)['v'])

        self.assertEqual('blah',
                         net.get_node_attribute(o_attr, comp_attr)['v'])
