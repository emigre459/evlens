import time
from evlens.data.plugshare import MainMapScraper

from evlens.logs import setup_logger
logger = setup_logger(__name__)

   
if __name__ == '__main__':
    s = MainMapScraper("./data/external/plugshare/06-16-2024/", timeout=3, headless=True)

    #TODO: can I remove one or more of these save calls? Seems duplicative.
    df = s.run(0, 100)
