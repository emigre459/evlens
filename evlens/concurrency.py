from typing import List, Union, Any

import multiprocessing
import ray
import ray.exceptions

from evlens.logs import setup_logger
logger = setup_logger(__name__)


def parse_n_jobs(n_jobs: Union[int, None]) -> int:
    '''
    Parses the possible_n_jobs argument and returns an integer representing
    how many jobs should be run in parallel. If None, returns the number of
    available CPUs minus one so the parent process has a CPU to itself.
    '''
    num_cpus = multiprocessing.cpu_count() - 1
    if  n_jobs == -1 or n_jobs is None:
        logger.info("Parallelizing across %s jobs", num_cpus)
        n_jobs = num_cpus
    elif n_jobs > num_cpus:
        logger.warning("`n_jobs` (%s) is greater than the number of available CPUs (%s). Setting n_jobs to %s", n_jobs, num_cpus, num_cpus)
        n_jobs = num_cpus
    elif n_jobs < -1 or n_jobs == 0:
        raise ValueError("`n_jobs` must be -1 or a positive integer")
    
    return n_jobs
    

#TODO: make it so you don't need to assume `run()` method name and can feed run()-ish method more than one arg
#TODO: enable different kwarg config for each actor
def parallelized_data_processing(
    actors: List[Any],
    run_args: List[Any],
    n_jobs: int = -1,
    **kwargs
):
    
    n_jobs = parse_n_jobs(n_jobs)
    ray_context = ray.init(
        num_cpus=n_jobs,
        # num_gpus=0,
        include_dashboard=True
    )
    logger.info("Ray dashboard can be found at %s",
                ray_context.dashboard_url)
    
    parallel_actors = [actor.remote(**kwargs) for actor in actors]
    
    try:    
        results = ray.get([
            parallel_actors[i].run.remote(run_arg) for i, run_arg in enumerate(run_args)
        ])
    except (ray.exceptions.RayTaskError, ray.exceptions.RayActorError) as e:
        logger.error("Ray had an error. See the dashboard for more information.")
        raise e
        
    
    # Make sure we have no ray processes already running
    ray.shutdown()
    
    return results