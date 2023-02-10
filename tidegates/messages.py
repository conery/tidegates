# 
# Module for printing status messages, either using the Panel logging
# facility when running the web app in a container or printing to the
# terminal when running from the command line.
#

import panel as pn
import logging

class Logging:

    logger = 'none'

    @staticmethod
    def setup(app):
        if app not in ['panel', 'api']:
            raise Exception(f'unknown app: {app}')
        if app == 'api':
            logging.basicConfig(
                format='%(asctime)s %(message)s',
                datefmt='%I:%M:%S',
                level=logging.INFO,
            )
        Logging.logger = app

    @staticmethod
    def null(*_):
        print('logging not initialized')

    @staticmethod
    def api_log(*args):
        logging.info(' '.join([str(s) for s in args]))

    dispatch = {
        'none':   null,
        'panel':  pn.state.log,
        'api':    api_log,
    }

    def log(*args):
        Logging.dispatch[Logging.logger](*args)
