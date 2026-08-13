import logging
from utils import config


# config logging
logging.basicConfig(filename='running_log.log',
                    filemode='w',  # there are two modes: 'a' and 'w'
                    format='%(levelname)s - %(message)s',
                    level=config.LOGGING_LEVEL
                    )

logger = logging.getLogger()