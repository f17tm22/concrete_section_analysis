import sys
import os
from PyQt5.QtWidgets import QApplication

# 设置macOS平台插件
if sys.platform == 'darwin':
    os.environ['QT_QPA_PLATFORM'] = 'cocoa'

sys.path.append(os.path.dirname(__file__))
from gui_irregular import RCSectionAnalysisGUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RCSectionAnalysisGUI()
    sys.exit(app.exec_())