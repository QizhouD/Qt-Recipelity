"""
智能食谱管理系统
主程序入口
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'recipe_manager.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        logger.info("启动智能食谱管理系统")
        
        # 检查依赖
        check_dependencies()
        
        # 导入并运行主窗口
        from ui.main_window import main as run_app
        run_app()
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        print(f"应用启动失败: {e}")
        sys.exit(1)

def check_dependencies():
    """检查依赖库"""
    try:
        # 检查Qt
        from PyQt6.QtWidgets import QApplication
        
        # 检查SQLAlchemy
        import sqlalchemy
        
        # 检查requests
        import requests
        
        # 检查BeautifulSoup
        from bs4 import BeautifulSoup
        
        # 检查matplotlib
        import matplotlib.pyplot
        
        # 检查OpenCV
        import cv2
        
        logger.info("所有依赖库检查通过")
        
    except ImportError as e:
        logger.error(f"缺少依赖库: {e.name}")
        raise ImportError(f"缺少依赖库: {e.name}\n请使用pip安装: pip install {e.name}") from e

if __name__ == "__main__":
    main()
