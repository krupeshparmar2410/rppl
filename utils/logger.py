import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def get_logger(name):
    """
    Creates or retrieves a logger configured with both console and 
    rotating file handlers in the format: Timestamp | Level | Module | Message
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        
        # Centralized format matching the task requirements:
        # Timestamp | Level | Module | Message
        log_format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
        
        # Console stream handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Rotating file handler (5 MB size limit per file, keeping up to 5 backups)
        try:
            os.makedirs('logs', exist_ok=True)
            file_handler = RotatingFileHandler(
                os.path.join('logs', 'app.log'),
                maxBytes=5*1024*1024,  # 5 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback prints to stderr if the logs directory is locked or unavailable
            print(f"[LOGGER] Error creating file handler for logs/app.log: {e}", file=sys.stderr)
            
    return logger
