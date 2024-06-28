from evlens.data.plugshare import ParallelScraper
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import ray
import multiprocessing

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    num_cpus = multiprocessing.cpu_count() - 1
    logger.info("Parallelizing across %s jobs", num_cpus)
    
    # Make sure we have no ray processes already running
    ray.shutdown()
    
    ray_context = ray.init(
        num_cpus=num_cpus,
        num_gpus=0,
        include_dashboard=True
    )
    logger.info("Ray dashboard can be found at %s",
                ray_context.dashboard_url)
    
    parallel_scrapers = []
    locations = [TEST_LOCATION, TEST_LOCATION, TEST_LOCATION]
    
    # Setup as many scrapers as we have locations (not usually how it would work, since we can only setup n_jobs scrapers and have more locations than that...)
    #FIXME: WHY IS IT OPENING THE PAGES SEQUENTIALLY INSTEAD OF IN PARALLEL?
    parallel_scrapers = [ParallelScraper.remote(
            f"../data/external/plugshare/{TODAY_STRING}/",
            timeout=3,
            headless=False
        ) for _ in range(len(locations))]
    
    results = ray.get([
        parallel_scrapers[i].run.remote(location) for i, location in enumerate(locations)
    ])
    
    print(results)
    ray.shutdown()