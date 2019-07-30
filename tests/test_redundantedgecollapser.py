#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `RedundantEdgeCollapser` class."""

import os
import tempfile
import shutil
import json
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

    def test_get_citation_from_edge_dict(self):
        collapser = RedundantEdgeCollapser()

        # single citation pubmedurl is None
        edge_dict = {'citation': (['pubmed:123'], 'list_of_string')}
        res = collapser._get_citation_from_edge_dict(edge_dict)
        self.assertEqual(' ', res)

        # multiple citation pubmedurl is None
        edge_dict = {'citation': (['pubmed:123',
                                   'pubmed:456'], 'list_of_string')}
        res = collapser._get_citation_from_edge_dict(edge_dict)
        self.assertEqual('  ', res)

        # single citation pubmedurl is set
        net = NiceCXNetwork()
        ctext = {'pubmed': 'http://p/'}
        net.set_network_attribute('@context', values=json.dumps(ctext))
        edge_dict = {'citation': (['pubmed:123'], 'list_of_string')}
        collapser._set_pubmedurl_from_network(net)
        res = collapser._get_citation_from_edge_dict(edge_dict)
        self.assertEqual('<a target="_blank" '
                         'href="http://p/123">pubmed:123</a> ', res)

        # multiple citation pubmedurl is set
        edge_dict = {'citation': (['pubmed:123',
                                   'pubmed:456'], 'list_of_string')}
        res = collapser._get_citation_from_edge_dict(edge_dict)
        self.assertEqual('<a target="_blank" '
                         'href="http://p/123">pubmed:123</a> '
                         '<a target="_blank" href="http://p/456">pubmed:'
                         '456</a> ', res)

    def test_prepend_citation_to_sentences(self):
        collapser = RedundantEdgeCollapser()
        net = NiceCXNetwork()
        ctext = {'pubmed': 'http://p/'}
        net.set_network_attribute('@context', values=json.dumps(ctext))
        collapser._set_pubmedurl_from_network(net)

        res = collapser._prepend_citation_to_sentences({})
        self.assertEqual({}, res)
        res = collapser._prepend_citation_to_sentences({'sentence':
                                                        ('hi', 'string')})
        self.assertEqual({'sentence':
                          ('hi', 'string')}, res)
        edge_dict = {'citation': (['pubmed:123'], 'list_of_string'),
                     'sentence': ('sentence2', 'string')}
        res = collapser._prepend_citation_to_sentences(edge_dict)
        self.assertEqual('<a target="_blank" href="http://p/123">'
                         'pubmed:123</a> sentence2',
                         res['sentence'][0])
        self.assertEqual('string', res['sentence'][1])

    def test_update_edge_with_dict(self):
        collapser = RedundantEdgeCollapser()
        net = NiceCXNetwork()

        eid = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='something')
        net.set_edge_attribute(eid, 'sentence', 'hi', type='string')

        edge_dict = {'citation': (set(['pubmed:123']), 'list_of_string'),
                     'sentence': (set(['sentence1', 'sentence2']), 'string'),
                     'direct': (set([True, False]), 'boolean')}

        res = collapser._update_edge_with_dict(net, eid, edge_dict)

        self.assertTrue('direct attribute has multiple values:' in res[0])

        edata = net.get_edge_attribute(eid, 'citation')
        self.assertEqual('list_of_string', edata['d'])
        self.assertEqual(['pubmed:123'], edata['v'])

        edata = net.get_edge_attribute(eid, 'sentence')
        self.assertEqual('list_of_string', edata['d'])
        self.assertTrue('sentence1' in edata['v'])
        self.assertTrue('sentence2' in edata['v'])
        self.assertEqual(2, len(edata['v']))

        edata = net.get_edge_attribute(eid, 'direct')
        self.assertEqual('boolean', edata['d'])
        self.assertEqual(False, edata['v'])

    def test_collapse_edgeset(self):
        collapser = RedundantEdgeCollapser()

        net = NiceCXNetwork()
        ctext = {'pubmed': 'http://p/'}
        net.set_network_attribute('@context', values=json.dumps(ctext))
        collapser._set_pubmedurl_from_network(net)

        eid = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='something')

        net.set_edge_attribute(eid, 'sentence', 'sent1', type='string')
        net.set_edge_attribute(eid, 'direct', True, type='boolean')
        net.set_edge_attribute(eid, 'citation', 'pubmed:123', type='string')

        eidtwo = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='something')
        net.set_edge_attribute(eidtwo, 'sentence', 'sent2', type='string')
        net.set_edge_attribute(eidtwo, 'direct', True, type='boolean')
        net.set_edge_attribute(eidtwo, 'citation', 'pubmed:456', type='string')

        issues = collapser._collapse_edgeset(net, set([eid, eidtwo]))
        self.assertEqual([], issues)

        edata = net.get_edge_attribute(eid, 'sentence')
        self.assertEqual(2, len(edata['v']))

        self.assertTrue('<a target="_blank" href="http://p/456">'
                        'pubmed:456</a>  sent2' in edata['v'])
        self.assertTrue('<a target="_blank" href="http://p/123">'
                        'pubmed:123</a> sent1' in edata['v'])

    def test_update_none_passed_in(self):
        collapser = RedundantEdgeCollapser()
        res = collapser.update(None)
        self.assertEqual(['Network passed in is None'], res)

    def test_update(self):
        collapser = RedundantEdgeCollapser()
        net = NiceCXNetwork()
        ctext = {'pubmed': 'http://p/'}
        net.set_network_attribute('@context', values=json.dumps(ctext))
        collapser._set_pubmedurl_from_network(net)

        eid = net.create_edge(edge_source=0, edge_target=1,
                              edge_interaction='something')

        net.set_edge_attribute(eid, 'sentence', 'sent1', type='string')
        net.set_edge_attribute(eid, 'direct', True, type='boolean')
        net.set_edge_attribute(eid, 'citation', 'pubmed:123', type='string')

        eidtwo = net.create_edge(edge_source=0, edge_target=1,
                                 edge_interaction='something')
        net.set_edge_attribute(eidtwo, 'sentence', 'sent2', type='string')
        net.set_edge_attribute(eidtwo, 'direct', True, type='boolean')
        net.set_edge_attribute(eidtwo, 'citation', 'pubmed:456', type='string')
        res = collapser.update(net)

        self.assertEqual([], res)

        edata = net.get_edge_attribute(eid, 'sentence')
        self.assertEqual(2, len(edata['v']))

        self.assertTrue('<a target="_blank" href="http://p/456">'
                        'pubmed:456</a>  sent2' in edata['v'])
        self.assertTrue('<a target="_blank" href="http://p/123">'
                        'pubmed:123</a> sent1' in edata['v'])



