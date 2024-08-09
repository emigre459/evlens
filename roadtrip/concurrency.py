from typing import List, Union, Any
import math

import multiprocessing
import numpy as np
import ray
import ray.exceptions
import pandas as pd

from roadtrip.logs import setup_logger
logger = setup_logger(__name__)


def parse_n_jobs(n_jobs: Union[int, None]) -> int:
    '''
    Parses the possible_n_jobs argument and returns an integer representing
    how many jobs should be run in parallel. If None, returns the number of
    available CPUs minus one so the parent process has a CPU to itself.
    '''
    num_cpus = multiprocessing.cpu_count() - 1
    if  n_jobs == -1 or n_jobs is None:
        n_jobs = num_cpus
    elif n_jobs > num_cpus:
        logger.warning("`n_jobs` (%s) is greater than the number of available CPUs (%s). Setting n_jobs to %s", n_jobs, num_cpus, num_cpus)
        n_jobs = num_cpus
    elif n_jobs < -1 or n_jobs == 0:
        raise ValueError("`n_jobs` must be -1 or a positive integer")
    
    logger.info("Parallelizing across %s workers", n_jobs)
    return n_jobs


def get_batches_by_worker(
    data: Any,
    n_jobs: int,
    checkpoint_indices: List[Any] = None
) -> List[Any]:
    data_size = len(data)
    
    batch_size = math.floor(data_size / n_jobs)
    leftovers = data_size % n_jobs

    even_batch_sizes = np.ones(n_jobs) * batch_size

    # Format is (num_add_before_original_array, num_add_after...)
    num_zeroes_for_padding = (0, n_jobs - leftovers)
    adders = np.pad(np.ones(leftovers), num_zeroes_for_padding)
    
    # These should be integers for each element indicating how big the data slice is for each
    data_index_lengths = even_batch_sizes + adders
    
    ending_indices = np.cumsum(data_index_lengths).astype(int)
    starting_indices = (ending_indices  - data_index_lengths).astype(int)
    
    batches = []
    for start_idx, end_idx in zip(starting_indices, ending_indices):
        batches.append(data[start_idx:end_idx])
        
    # Check if we can make new batches based off of checkpoint values
    if checkpoint_indices is not None:
        # Assume that checkpoint values are not needed themselves, but just the values in each batch AFTER checkpoint values
        new_batches = []
        for idx, b in zip(checkpoint_indices, batches):
            new_batches.append(b.loc[idx+1:])
        batches = new_batches
        
    # Make sure we account for having more workers than batches needed
    if n_jobs > len(data):
        return [batch for batch in batches if len(batch) > 0]
    
    return batches


def get_batch_indices_from_identifiers(
    data: pd.DataFrame,
    checkpoint_values: List[Any],
    checkpoint_identifier: str
) -> List[Any]:
    
    last_ones = data[data[checkpoint_identifier].isin(checkpoint_values)].copy()
    return last_ones.index.tolist()
    

#TODO: make it so you don't need to assume `run()` method name and can feed run()-ish method more than one arg
#TODO: enable different kwarg config for each actor
def parallelized_data_processing(
    actor: Any,
    run_args: List[Any],
    n_jobs: int = -1,
    checkpoint_indices: List[Any] = None,
    **kwargs
) -> pd.DataFrame:
    
    # Just in case
    ray.shutdown()
    n_jobs = parse_n_jobs(n_jobs)
    
    ray_context = ray.init(
        num_cpus=n_jobs,
        # num_gpus=0,
        include_dashboard=False
    )
    
    # Batch up in n_actors-sized batches across all run_args
    run_arg_batches = get_batches_by_worker(
        run_args,
        n_jobs,
        checkpoint_indices=checkpoint_indices
    )
    
    # Make unique copies of each actor
    parallel_actors = [actor.remote(**kwargs) for _ in range(len(run_arg_batches))]
    
    logger.info(
        "Generated %s batches of sizes %s",
        len(run_arg_batches),
        [len(batch) for batch in run_arg_batches]
    )
    try:    
        results = ray.get([
            parallel_actors[i].run.remote(batch) for i, batch in enumerate(run_arg_batches)
        ])
    except (ray.exceptions.RayTaskError, ray.exceptions.RayActorError) as e:
        logger.error("Ray had an error. See the dashboard for more information.")
        raise e
        
    
    # Make sure we have no ray processes already running
    ray.shutdown()
    
    return results