import torch

from evlens.logs import setup_logger
logger = setup_logger()

def get_mac_gpu_device() -> str:
    '''
    Checks if MPS (Metal Performance Shader, the M[X] chipset GPU) is 
    available and returns the device it can use (even if that is not 
    available).

    Returns
    -------
    str
        "mps" if the Mac GPU is available, "cpu" otherwise
    '''
    # Check PyTorch has access to MPS 
    # (Metal Performance Shader, Apple's GPU architecture)
    logger.info("MPS is built: %s", torch.backends.mps.is_built())
    logger.info("MPS available: %s", torch.backends.mps.is_available())

    # Set the device      
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info("Using device: %s", device)
    
    return device


def empty_mac_gpu_cache():
    '''
    Logs the current memory being used on the MPS by PyTorch and clears it.
    '''
    logger.info("MPS memory used: %s", torch.mps.current_allocated_memory())
    torch.mps.empty_cache()
