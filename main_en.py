"""
Recipelity - Intelligent Recipe Management System
Main Program Entry
"""

import sys
import os
import logging
from pathlib import Path

# Add project root directory to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'recipelity.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function"""
    try:
        logger.info("Starting Recipelity - Intelligent Recipe Management System")
        
        # Check dependencies
        check_dependencies()
        
        # Import and run main window
        from ui.main_window_en import main as run_app
        run_app()
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        print(f"Application startup failed: {e}")
        sys.exit(1)

def check_dependencies():
    """Check dependency libraries"""
    try:
        # Check Qt
        from PyQt6.QtWidgets import QApplication
        
        # Check SQLAlchemy
        import sqlalchemy
        
        # Check requests
        import requests
        
        # Check BeautifulSoup
        from bs4 import BeautifulSoup
        
        # Check matplotlib
        import matplotlib.pyplot
        
        # Check OpenCV
        import cv2
        
        logger.info("All dependency libraries checked passed")
        
    except ImportError as e:
        logger.error(f"Missing dependency library: {e.name}")
        raise ImportError(f"Missing dependency library: {e.name}\nPlease install with pip: pip install {e.name}") from e

if __name__ == "__main__":
    main()
