#! /usr/bin/env python

import os
import argparse
import sys
import requests
import logging
import csv
import json
from datetime import datetime

import pandas as pd
from logging import config
import networkx

import ndex2
from ndex2.client import Ndex2
import ndexutil.tsv.tsv2nicecx2 as t2n
from ndexutil.config import NDExUtilConfig
from ndexutil.tsv.loaderutils import NetworkIssueReport
from ndexutil.tsv.loaderutils import NetworkUpdator

import ndexsignorloader

logger = logging.getLogger(__name__)

TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"


LOAD_PLAN = 'loadplan.json'
"""
Name of file containing json load plan
stored within this package
"""

STYLE = 'style.cx'
"""
Name of file containing CX with style
stored within this package
"""

SIGNOR_URL = 'https://signor.uniroma2.it/'
"""
Base Signor URL
"""

SPECIES_MAPPING = {'9606': 'Human', '10090': 'Mouse', '10116': 'Rat'}


class NDExLoadSignorError(Exception):
    """
    Base exception for this module
    """
    pass


def get_package_dir():
    """
    Gets directory where package is installed
    :return:
    """
    return os.path.dirname(ndexsignorloader.__file__)


def get_load_plan():
    """
    Gets the load plan stored with this package

    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), LOAD_PLAN)


def get_style():
    """
    Gets the style stored with this package

    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), STYLE)


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    help_fm = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=help_fm)
    parser.add_argument('datadir', help='Directory where signor '
                                        'data is downloaded to '
                                        'and processed from')
    parser.add_argument('--profile', help='Profile in configuration '
                                          'file to use to load '
                                          'NDEx credentials which means'
                                          'configuration under [XXX] will be'
                                          'used '
                                          '(default '
                                          'ndexsignorloader)',
                        default='ndexsignorloader')
    parser.add_argument('--logconf', default=None,
                        help='Path to python logging configuration file in '
                             'this format: https://docs.python.org/3/library/'
                             'logging.config.html#logging-config-fileformat '
                             'Setting this overrides -v parameter which uses '
                             ' default logger. (default None)')

    parser.add_argument('--conf', help='Configuration file to load '
                                       '(default ~/' +
                                       NDExUtilConfig.CONFIG_FILE)
    parser.add_argument('--loadplan', help='Use alternate load plan file',
                        default=get_load_plan())
    parser.add_argument('--style',
                        help='Path to NDEx CX file to use for styling'
                             'networks',
                        default=get_style())
    parser.add_argument('--skipdownload', action='store_true',
                        help='If set, skips download of data from signor'
                             'and assumes data already resides in <datadir>'
                             'directory')
    parser.add_argument('--signorurl', default=SIGNOR_URL,
                        help='URL to signor pathways (default ' +
                        SIGNOR_URL + ')')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increases verbosity of logger to standard '
                             'error for log messages in this module and'
                             'in ' + TSV2NICECXMODULE + '. Messages are '
                             'output at these python logging levels '
                             '-v = ERROR, -vv = WARNING, -vvv = INFO, '
                             '-vvvv = DEBUG, -vvvvv = NOTSET (default no '
                             'logging)')
    parser.add_argument('--version', action='version',
                        version=('%(prog)s ' +
                                 ndexsignorloader.__version__))

    return parser.parse_args(args)


def _setup_logging(args):
    """
    Sets up logging based on parsed command line arguments.
    If args.logconf is set use that configuration otherwise look
    at args.verbose and set logging for this module and the one
    in ndexutil specified by TSV2NICECXMODULE constant
    :param args: parsed command line arguments from argparse
    :raises AttributeError: If args is None or args.logconf is None
    :return: None
    """

    if args.logconf is None:
        level = (50 - (10 * args.verbose))
        logging.basicConfig(format=LOG_FORMAT,
                            level=level)
        logging.getLogger(TSV2NICECXMODULE).setLevel(level)
        logger.setLevel(level)
        return

    # logconf was set use that file
    logging.config.fileConfig(args.logconf,
                              disable_existing_loggers=False)


class SignorDownloader(object):
    """
    Downloads signor data from site
    """
    PATHWAYDATA_SCRIPT = 'getPathwayData.php?list'

    PATHWAY_LIST_FILE = 'pathway_list.txt'
    PATHWAYDATA_DOWNLOAD_SCRIPT = 'getPathwayData.php?pathway='
    GETDATA_SCRIPT = 'getData.php?organism='

    def __init__(self, signorurl, outdir):
        """
        Constructor
        :param signorurl: base SIGNOR URL
        :type signorurl: string
        :param outdir: directory where files will be downloaded to
        :type outdir: string
        """
        self._signorurl = signorurl
        self._outdir = outdir

    def get_pathway_list_file(self):
        """
        gets pathway list file
        :return:
        """
        return os.path.join(self._outdir,
                            SignorDownloader.PATHWAY_LIST_FILE)

    def _download_pathways_list(self):
        """
        Gets map of pathways
        :return: dict
        """
        logger.info("Downloading pathways list")
        resp = requests.get(SIGNOR_URL + '/' + SignorDownloader.PATHWAYDATA_SCRIPT)
        if resp.status_code != 200:
            raise NDExLoadSignorError('Got status code of ' +
                                      str(resp.status_code) + ' from signor')
        with open(self.get_pathway_list_file(), 'w') as f:
            f.write(resp.text)
            f.flush()

    def get_pathways_map(self):
        """
        Gets map from :py:const:`SignorDownloader.PATHWAY_LIST_FILE` file
        :return:
        """
        path_map = {}
        with open(self.get_pathway_list_file(), 'r') as f:
            reader = csv.reader(f, delimiter='\t')
            for line in reader:
                path_map[line[0].replace('/', '')] = line[1]

        return path_map

    def _get_download_url(self, pathway_id, relationsonly=False):
        """

        :param pathway_id:
        :param relationsonly:
        :return:
        """
        if relationsonly is False:
            relationssuffix = ''
        else:
            relationssuffix = '&relations=only'

        return SIGNOR_URL + SignorDownloader.PATHWAYDATA_DOWNLOAD_SCRIPT +\
               pathway_id + relationssuffix

    def _download_file(self, download_url, destfile):
        """

        :param theurl:
        :param destfile:
        :return:
        """
        if os.path.isfile(destfile):
            logger.info(destfile + ' exists. Skipping...')
            return

        logger.info('Downloading ' + download_url + ' to ' + destfile)
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(destfile, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

    def _download_pathway(self, pathway_id, destfile, relationsonly=False):
        """

        :param pathway_id:
        :param destfile:
        :param relationsonly:
        :return:
        """
        download_url = self._get_download_url(pathway_id,
                                              relationsonly=relationsonly)
        self._download_file(download_url, destfile)

    def _get_fulldownload_url(self, species_id):
        """

        :param species_id:
        :return:
        """
        return SIGNOR_URL + SignorDownloader.GETDATA_SCRIPT + species_id

    def _download_fullspecies(self, species_id, destfile):
        """

        :param species_id:
        :param destfile:
        :return:
        """
        download_url = self._get_fulldownload_url(species_id)
        self._download_file(download_url, destfile)

    def download_data(self):
        """
        Downloads data
        :return:
        """
        if not os.path.isdir(self._outdir):
            os.makedirs(self._outdir, mode=0o755)

        self._download_pathways_list()
        path_map = self.get_pathways_map()
        for key in path_map.keys():
            self._download_pathway(key, os.path.join(self._outdir,
                                                     key + '.txt'),
                                   relationsonly=True)
            self._download_pathway(key, os.path.join(self._outdir,
                                                     key + '_desc.txt'),
                                   relationsonly=False)

        for key in SPECIES_MAPPING.keys():
            self._download_fullspecies(key,
                                       os.path.join(self._outdir,
                                                    'full_' +
                                                    SPECIES_MAPPING[key] +
                                                    '.txt'))


class DirectEdgeAttributeUpdator(NetworkUpdator):
    """
    Updates value of 'DIRECT' edge attribute
    """
    DIRECTED_ATTRIB = 'direct'

    def __init__(self):
        """
        Constructor

        """
        super(DirectEdgeAttributeUpdator, self).__init__()

    def get_description(self):
        """

        :return:
        """
        return 'Updates value of directed edge attribute to true and false'

    def update(self, network):
        """
        Iterates through all edges in network updating edge attribute
        'DIRECT' to 'YES' if value is 't' otherwise set it to 'NO'

        :param network: network to examine
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return: empty list
        :rtype: list
        """
        if network is None:
            return None

        issues = []
        directed_attr_name = DirectEdgeAttributeUpdator.DIRECTED_ATTRIB
        for edge_id, edge in network.get_edges():
            edge_attr = network.get_edge_attribute(edge_id,
                                                    directed_attr_name)
            if edge_attr == (None, None):
                continue
            network.remove_edge_attribute(edge_id, directed_attr_name)
            if edge_attr['v'] == 't':

                network.set_edge_attribute(edge_id,
                                           directed_attr_name, True,
                                           type='boolean')
            else:
                network.set_edge_attribute(edge_id,
                                           directed_attr_name, False,
                                           type='boolean')

        return issues


class UpdatePrefixesForNodeRepresents(NetworkUpdator):
    """
    Prefixes node represents with uniprot: or signor:
    """

    def __init__(self):
        """
        Constructor

        """
        super(UpdatePrefixesForNodeRepresents, self).__init__()

    def get_description(self):
        """

        :return:
        """
        return 'Updates value of DIRECT edge attribute to yes and no'

    def update(self, network):
        """
        Iterates through nodes and updates prefix for represents of
        node based on value of 'DATABASE' node attribute. If the
        value if 'UNIPROT' then 'uniprot:' is prefixed if not already there
        and if 'SIGNOR' then 'signor:' is prefixed. The 'DATABASE' is
        removed as well

        :param network: network to examine
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return: list of node names for which no replacement was found
        :rtype: list
        """
        if network is None:
            return None

        issues = []
        for node_id, node in network.get_nodes():
            database = network.get_node_attribute_value(node_id, "DATABASE")
            represents = node.get('r')
            if database == "UNIPROT":
                if 'uniprot:' not in represents:
                    represents = "uniprot:" + represents
                    node['r'] = represents
            elif database in ["SIGNOR"]:
                if 'signor:' not in represents:
                    represents = "signor:" + represents
                    node['r'] = represents
            # in all other cases, the identifier is already prefixed
            network.remove_node_attribute(node_id, "DATABASE")

        return issues


class NodeCompartmentUpdator(NetworkUpdator):
    """
    Replace any empty node Compartment attribute values with cytoplasm
    """
    CYTOPLASM = 'cytoplasm'
    COMPARTMENT = 'compartment'

    def __init__(self):
        """
        Constructor

        """
        super(NodeCompartmentUpdator, self).__init__()

    def get_description(self):
        """

        :return:
        """
        return 'Replace any empty node compartment attribute values with cytoplasm'

    def update(self, network):
        """
        Iterates through nodes and updates 'compartment' attribute
        if its empty by setting it to 'cytoplasm'

        :param network: network to examine
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return: list of node names for which no replacement was found
        :rtype: list
        """
        if network is None:
            return None

        issues = []
        for node_id, node in network.get_nodes():
            node_attr = network.get_node_attribute(node_id,
                                                   NodeCompartmentUpdator.COMPARTMENT)
            if node_attr == (None, None) or node_attr is None:
                issues.append('Node (' + str(node_id) +
                              ' did not have Compartment attribute')
                network.set_node_attribute(node_id, NodeCompartmentUpdator.COMPARTMENT,
                                           NodeCompartmentUpdator.CYTOPLASM)
                continue
            if node_attr['v'] is None or node_attr['v'] == '':
                node_attr['v'] = NodeCompartmentUpdator.CYTOPLASM
        return issues


class SpringLayoutUpdator(NetworkUpdator):
    """
    Applies Spring layout
    """
    CARTESIAN_LAYOUT = 'cartesianLayout'

    def __init__(self, scale=500.0):
        """
        Constructor

        :param scale: scale for networkx spring layout
        :type scale: float
        """
        super(SpringLayoutUpdator, self).__init__()

        self._scale = scale

    def get_description(self):
        """

        :return:
        """
        return 'Applies Spring layout to network'

    def _get_cartesian_aspect(self, net_x):
        """
        Converts coordinates from :py:class:`networkx.Graph`
        to NDEx aspect
        :param net_x: network with coordinates
        :type net_x: :py:class:`networkx.Graph`
        :return: coordinates as list of dicts ie [{'node': <id>, 'x': <xpos>, 'y': <ypos>}]
        :rtype: list
        """
        return [{'node': n,
                 'x': float(net_x.pos[n][0]),
                 'y': float(net_x.pos[n][1])} for n in net_x.pos]

    def update(self, network):
        """
        Applies spring layout to network

        :param network: network to examine
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return: list of node names for which no replacement was found
        :rtype: list
        """
        if network is None:
            return None

        issues = []
        net_x = network.to_networkx(mode='default')
        net_x.pos = networkx.drawing.spring_layout(net_x, scale=self._scale)

        network.set_opaque_aspect(SpringLayoutUpdator.CARTESIAN_LAYOUT,
                                  self._get_cartesian_aspect(net_x))
        return issues


class LoadSignorIntoNDEx(object):
    """
    Class to load content
    """
    def __init__(self, args,
                 downloader,
                 updators=None):
        """

        :param args:
        """
        self._conf_file = args.conf
        self._args = args
        self._profile = args.profile
        self._outdir = os.path.abspath(args.datadir)
        self._user = None
        self._pass = None
        self._server = None
        self._ndex = None
        self._loadplan = None
        self._template = None
        self._net_summaries = None
        self._downloader = downloader
        self._updators = updators

    def _parse_config(self):
            """
            Parses config
            :return:
            """
            ncon = NDExUtilConfig(conf_file=self._conf_file)
            con = ncon.get_config()
            self._user = con.get(self._profile, NDExUtilConfig.USER)
            self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
            self._server = con.get(self._profile, NDExUtilConfig.SERVER)

    def _get_user_agent(self):
        """
        Builds user agent string
        :return: user agent string in form of ncipid/<version of this tool>
        :rtype: string
        """
        return 'ndexsignorloader/' + self._args.version

    def _create_ndex_connection(self):
        """
        creates connection to ndex
        :return:
        """
        if self._ndex is None:
            self._ndex = Ndex2(host=self._server, username=self._user,
                               password=self._pass, user_agent=self._get_user_agent())

    def _parse_load_plan(self):
        """

        :return:
        """
        with open(self._args.loadplan, 'r') as f:
            self._loadplan = json.load(f)

    def _load_style_template(self):
        """
        Loads the CX network specified by self._args.style into self._template
        :return:
        """
        self._template = ndex2.create_nice_cx_from_file(os.path.abspath(self._args.style))

    def _load_network_summaries_for_user(self):
        """
        Gets a dictionary of all networks for user account
        <network name upper cased> => <NDEx UUID>
        :return: dict
        """
        net_summaries = self._ndex.get_network_summaries_for_user(self._user)
        self._net_summaries = {}
        for nk in net_summaries:
            if nk.get('name') is not None:
                self._net_summaries[nk.get('name').upper()] = nk.get('externalId')

    def _get_signor_pathway_relations_df(self, pathway_id):

        pathway_file_path = os.path.join(self._outdir, pathway_id + '.txt')
        if not os.path.isfile(pathway_file_path):
            raise NDExLoadSignorError(pathway_file_path + ' file missing.')
        if os.path.getsize(pathway_file_path) < 10:
            raise NDExLoadSignorError(pathway_file_path + ' looks to be empty')
        with open(pathway_file_path, 'r', encoding='utf-8') as pfp:
            signor_pathway_relations_df = pd.read_csv(pfp, dtype=str, na_filter=False, delimiter='\t',
                                                      engine='python')

            return signor_pathway_relations_df

    def _get_signor_pathway_description_df(self, pathway_id):
        pathway_file_path = os.path.join(self._outdir, pathway_id + '_desc.txt')
        if not os.path.isfile(pathway_file_path):
            raise NDExLoadSignorError(pathway_file_path + ' file missing.')

        with open(pathway_file_path, 'r', encoding='utf-8') as pfp:
            signor_pathway_relations_df = pd.read_csv(pfp, dtype=str, na_filter=False, delimiter='\t',
                                                      engine='python')

            return signor_pathway_relations_df

    def _process_pathway(self, pathway_id, pathway_name):
        """

        :param pathway_id:
        :return:
        """
        df = self._get_signor_pathway_relations_df(pathway_id)
        # upcase column names
        rename = {}
        for column_name in df.columns:
            rename[column_name] = column_name.upper()
        df = df.rename(columns=rename)

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df,
                                                               self._loadplan)
        report = NetworkIssueReport(pathway_name)

        if self._updators is not None:
            for updator in self._updators:
                issues = updator.update(network)
                report.addissues(updator.get_description(), issues)

        self._add_pathway_info(network, pathway_id)

        network_update_key = self._net_summaries.get(network.get_name().upper())

        if network_update_key is not None:
            network.update_to(network_update_key, self._server, self._user, self._pass,
                              user_agent=self._get_user_agent())
        else:
            network.upload_to(self._server, self._user,
                              self._pass,
                              user_agent=self._get_user_agent())
        return report

    def _add_pathway_info(self, network, pathway_id):
        """
        Adds network
        :param network:
        :param network_id:
        :param cytoscape_visual_properties_template_id: UUID of NDEx network to
               extract various network attributes such as description, rightsHolder,
               reference, rights

        :return:
        """
        dataframe = self._get_signor_pathway_description_df(pathway_id)
        if dataframe is None:
            logger.warning('Skipping ' + pathway_id)
            return
        if not pd.isnull(dataframe.iat[0, 1]):
            network.set_name(dataframe.iat[0, 1])
        if not pd.isnull(dataframe.iat[0, 0]):
            network.set_network_attribute("labels", [dataframe.iat[0, 0]], type='list_of_string')
        if not pd.isnull(dataframe.iat[0, 3]):
            network.set_network_attribute("author", dataframe.iat[0, 3])
        if not pd.isnull(dataframe.iat[0, 2]):
            network.set_network_attribute("description",
                                          '%s %s' % (dataframe.iat[0, 2],
                                                     self._template.get_network_attribute('description')['v']))

        network.set_network_attribute('rightsHolder', 'Prof. Gianni Cesareni ')
        network.set_network_attribute('rights', 'Attribution-ShareAlike 4.0 International (CC BY-SA 4.0')

        network.set_network_attribute("reference", '<div>Perfetto L., <i>et al.</i></div><div><b>SIGNOR: a database of causal relationships between biological entities</b><i>.</i></div><div>Nucleic Acids Res. 2016 Jan 4;44(D1):D548-54</div><div><span><a href=\"\\&#34;https://doi.org/10.1093/nar/gkv1048\\&#34;\" target=\"\\&#34;\\&#34;\">doi: 10.1093/nar/gkv1048</a></span></div>')

        network.set_network_attribute('dataSource',
                                      'https://signor.uniroma2.it/pathway_browser.php?organism=&pathway_list=' +
                                      str(pathway_id))

        network.set_network_attribute("version", f"{datetime.now():%d-%b-%Y}")

        disease_pathways = ['ALZHEIMER DISEASE', 'FSGS', 'NOONAN SYNDROME', 'PARKINSON DISEASE']

        cancer_pathways = ['ACUTE MYELOID LEUKEMIA', 'COLORECTAL CARCINOMA', 'GLIOBLASTOMA MULTIFORME',
                           'LUMINAL BREAST CANCER', 'MALIGNANT MELANOMA', 'PROSTATE CANCER',
                           'RHABDOMYOSARCOMA', 'THYROID CANCER']

        network.set_network_attribute("organism", "Human, 9606, Homo sapiens")

        if network.get_name().upper() in disease_pathways:
            network.set_network_attribute("networkType", "Disease Pathway")
        elif network.get_name().upper() in cancer_pathways:
            network.set_network_attribute("networkType", "Cancer Pathway")
        else:
            network.set_network_attribute("networkType", "Signalling Pathway")
        # TODO: set “networkType” property depending on network
        #    a. Signalling Pathway
        #    b. Disease Pathway
        #    c. Cancer Pathway

    def run(self):
        """
        Runs content loading for NDEx Signor Content Loader
        :param theargs:
        :return:
        """
        self._parse_config()
        logger.debug('Parsed config: ' + self._user)
        self._parse_load_plan()
        self._create_ndex_connection()
        self._load_network_summaries_for_user()
        self._load_style_template()

        pathway_map = self._downloader.get_pathways_map()
        if pathway_map is None:
            logger.error('Pathway map came back as None')
            return 1
        for key in pathway_map.keys():
            logger.info('Processing ' + key + ' => ' + pathway_map[key])
            try:
                self._process_pathway(key, pathway_map[key])
            except NDExLoadSignorError as ne:
                logger.exception('Unable to load pathway: ' + key +
                                 ' => ' + pathway_map[key])

        return 0


def main(args):
    """
    Main entry point for program
    :param args:
    :return:
    """
    desc = """
    Version {version}

    Loads NDEx Signor Content Loader data into NDEx (http://ndexbio.org).
    
    To connect to NDEx server a configuration file must be passed
    into --conf parameter. If --conf is unset the configuration 
    the path ~/{confname} is examined. 
         
    The configuration file should be formatted as follows:
         
    [<value in --profile (default ncipid)>]
         
    {user} = <NDEx username>
    {password} = <NDEx password>
    {server} = <NDEx server(omit http) ie public.ndexbio.org>
    
    
    """.format(confname=NDExUtilConfig.CONFIG_FILE,
               user=NDExUtilConfig.USER,
               password=NDExUtilConfig.PASSWORD,
               server=NDExUtilConfig.SERVER,
               version=ndexsignorloader.__version__)
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = ndexsignorloader.__version__

    try:
        _setup_logging(theargs)
        datadir = os.path.abspath(theargs.datadir)
        downloader = SignorDownloader(theargs.signorurl,
                                      datadir)
        if theargs.skipdownload is False:
            downloader.download_data()

        updators = [DirectEdgeAttributeUpdator(),
                    UpdatePrefixesForNodeRepresents(),
                    NodeCompartmentUpdator(),
                    SpringLayoutUpdator()]
        loader = LoadSignorIntoNDEx(theargs, downloader,
                                    updators=updators)
        return loader.run()
    except Exception as e:
        logger.exception('Caught exception')
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
