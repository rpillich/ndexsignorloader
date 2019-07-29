#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `RedundantEdgeCollapser` class."""

import os
import tempfile
import shutil

import unittest
from ndex2.nice_cx_network import NiceCXNetwork
from ndexsignorloader.ndexloadsignor import RedundantEdgeCollapser


class TestRedundantEdgeCollapser(unittest.TestCase):
    """Tests for `RedundantEdgeCollapser` class."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_get_description(self):
        collapser = RedundantEdgeCollapser()
        self.assertEqual('Collapses redundant edges',
                         collapser.get_description())

    def test_get_citation_html_frag(self):
        collapser = RedundantEdgeCollapser()
        res = collapser._get_citation_html_frag('pubmedurl/', 'pubmedid')
        self.assertEqual('<a target="_blank" href="pubmedurl/pubmedid">'
                         'pubmed:pubmedid</a>',
                         res)

    def test_set_pubmedurl_from_network(self):
        collapser = RedundantEdgeCollapser()
        net = NiceCXNetwork()
        # net.set_network_attribute('@context', values=)
        pass

    def test_remove_edge(self):
        collapser = RedundantEdgeCollapser()
        net = NiceCXNetwork()

        # test remove on non existant edge
        collapser._remove_edge(net, 10)

        # test removing edge with no attributes
        eid = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='needs')
        self.assertEqual('needs',
                         net.get_edge(eid)['i'])
        collapser._remove_edge(net, eid)
        self.assertEqual(None,
                         net.get_edge(eid))

        # test removing edge with attributes
        eid = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='needs')

        net.set_edge_attribute(eid, 'foo', 'someval')
        net.set_edge_attribute(eid, 'foo2', 'someval2')

        self.assertEqual('needs',
                         net.get_edge(eid)['i'])
        self.assertEqual('someval',
                         net.get_edge_attribute(eid, 'foo')['v'])
        self.assertEqual('someval2',
                         net.get_edge_attribute(eid, 'foo2')['v'])
        collapser._remove_edge(net, eid)
        self.assertEqual(None,
                         net.get_edge(eid))
        self.assertEqual((None, None),
                         net.get_edge_attribute(eid, 'foo'))
        self.assertEqual((None, None),
                         net.get_edge_attribute(eid, 'foo2'))

    def test_add_edge_to_map(self):
        collapser = RedundantEdgeCollapser()

        # test adding new entry
        edge_map = {}
        collapser._add_to_edge_map(edge_map, 0, 1, 2)
        self.assertEqual({0}, edge_map[1][2])

        # test adding duplicate
        collapser._add_to_edge_map(edge_map, 0, 1, 2)
        self.assertEqual({0}, edge_map[1][2])

        # test adding new entry to existing dict
        collapser._add_to_edge_map(edge_map, 3, 1, 2)
        self.assertEqual({0, 3}, edge_map[1][2])

    def test_build_edge_map(self):
        collapser = RedundantEdgeCollapser()

        # try on empty network
        net = NiceCXNetwork()
        edge_dict = collapser._build_edge_map(net)
        self.assertEqual({}, edge_dict)

        # try on single edge network
        net.create_edge(edge_source=0, edge_target=1,
                        edge_interaction='something')

        edge_dict = collapser._build_edge_map(net)
        self.assertEqual({'something': {0: {1: {0}}}}, edge_dict)

        # add another edge same interaction
        net.create_edge(edge_source=0, edge_target=1,
                        edge_interaction='something')
        edge_dict = collapser._build_edge_map(net)
        self.assertEqual({'something': {0: {1: {0, 1}}}}, edge_dict)

        # add another edge different interaction
        net.create_edge(edge_source=0, edge_target=1,
                        edge_interaction='foo')
        edge_dict = collapser._build_edge_map(net)
        self.assertEqual({0: {1: {0, 1}}}, edge_dict['something'])
        self.assertEqual({0: {1: {2}}}, edge_dict['foo'])

    def test_convert_attributes_to_dict(self):
        collapser = RedundantEdgeCollapser()

        # test on single item attribute list
        attr_list = [{'n': 'name1', 'v': 'value1',
                      'd': 'string'}]
        attr_dict = collapser._convert_attributes_to_dict(attr_list)

        self.assertEqual(('value1', 'string'), attr_dict['name1'])

        # try a second item
        attr_list.append({'n': 'name2', 'v': ['value2'],
                          'd': 'list_of_string'})

        attr_dict = collapser._convert_attributes_to_dict(attr_list)

        self.assertEqual(('value1', 'string'), attr_dict['name1'])
        self.assertEqual((['value2'], 'list_of_string'),
                         attr_dict['name2'])

    def test_convert_attributes_to_dict_with_set(self):
        collapser = RedundantEdgeCollapser()

        # test on single item attribute list
        edge_dict = {'name1': ('value1', 'string')}
        attr_dict = collapser._convert_attributes_to_dict_with_set(edge_dict)

        self.assertEqual(({'value1'}, 'string'), attr_dict['name1'])

        # try a second item
        edge_dict['name2'] = (['value2'], 'list_of_string')

        attr_dict = collapser._convert_attributes_to_dict_with_set(edge_dict)

        self.assertEqual(({'value1'}, 'string'), attr_dict['name1'])
        self.assertEqual(({'value2'}, 'list_of_string'),
                         attr_dict['name2'])



