#! /usr/bin/env python

import os
import argparse
import sys
import requests
import logging
import csv
import pandas as pd
from logging import config
from ndexutil.config import NDExUtilConfig
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

    def _get_pathways_map(self):
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
        path_map = self._get_pathways_map()
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


class LoadSignorIntoNDEx(object):
    """
    Class to load content
    """
    def __init__(self, args):
        """

        :param args:
        """
        self._conf_file = args.conf
        self._profile = args.profile
        self._outdir = os.path.abspath(theargs.datadir)
        self._user = None
        self._pass = None
        self._server = None

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

    def _get_signor_pathway_relations_df(self, pathway_id):

        pathway_file_path = os.path.join(self._outdir, pathway_id + '.txt')
        if not os.path.isfile(pathway_file_path):
            raise NDExLoadSignorError(pathway_file_path + ' file missing.')

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

    def run(self):
        """
        Runs content loading for NDEx Signor Content Loader
        :param theargs:
        :return:
        """
        self._parse_config()
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
        if theargs.skipdownload is False:
            downloader = SignorDownloader(theargs.signorurl,
                                          datadir)
            downloader.download_data()
        loader = LoadSignorIntoNDEx(theargs)
        return loader.run()
    except Exception as e:
        logger.exception('Caught exception')
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
