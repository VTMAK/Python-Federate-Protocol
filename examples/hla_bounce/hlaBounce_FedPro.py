"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import sys
import os
# Set the top directory to be two levels higher than the current directory (needed for py imports)
current_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, top_dir)

from PyQt5.QtWidgets import QApplication
from examples.hla_bounce.ballData import BallMap
from examples.hla_bounce.regionData import DdmRegionMap
from examples.hla_bounce.hlaBounceGui import HlaBounceGui
from examples.hla_bounce.ballController import BallController

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """
        Main entry point - creates ball data, region data, controller and GUI.
    """
    # Create the data structures (equivalent to C++ new operations)
    ball_data = BallMap()
    region_data = DdmRegionMap()
    controller = BallController(ball_data, region_data)
    
    # Create and run GUI (equivalent to C++ HlaBounceGui constructor call)
    app = QApplication(sys.argv)
    gui = HlaBounceGui(controller, ball_data, region_data, "HLA Evolved Python")
    
    # Show the GUI and start the event loop
    gui.show()
    result = app.exec_()
    
    # Cleanup (equivalent to C++ delete operations)
    del controller
    del ball_data  
    del region_data
    
    sys.exit(result)

if __name__ == "__main__":
    main()