"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import os
import sys
# Set the top directory to be two levels higher than the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, top_dir)
from libsrc.rtiUtil.logger import *
from HLA1516_2025.RTI.enums import Enums
from examples.simpleFedPro.simpleFederate import simpleFederate
from libsrc.fedProWrapper.rtiAmbassadorFedPro import Configuration

"""
    RTI Simple Federate Example using Federate Protocol
"""

def processArguments(argc:int , argv:list, configuration:Configuration)-> bool:
    """
        Parse command-line style arguments to update Configuration fields; supports clearing and adding FOM modules.

        Args:
            argc (int): Count of arguments provided (len(argv)).
            argv (list): Argument vector (script name followed by flags and values).
            configuration (Configuration): Mutable configuration object to update.
        Returns:
            bool: True if arguments processed without help (-h) request or errors; False triggers early exit.
        Notes:
            Relies on bounds checks to avoid index errors; does not raise exceptions explicitly.
    """
    doHelp = False
    helpMessage = "Usage: "
    helpMessage += argv[0] if len(argv) > 0 else "FederateProtocol_Python.py"
    helpMessage += " [-F <federation name>][-t <federate type>] [-c] [-m <FOM Module>]+ \n" \
        "\t[-u] [-o] [-p <password>] [-n <configuration name>] [-r <RTI address>] [-a <additional settings>] [-h]\n"
    helpMessage += "\n\tDuplicate arguments overwrite previous ones except FOM modules which are added to existing list\n"
    helpMessage += "\t-c clears FOM module list (erasing any previous arguments also)\n"
    helpMessage += "\t-i use immediate callback\n"
    helpMessage += "\t-u subscribe directed interactions universally\n"
    helpMessage += "\t-o use MOM\n"
    helpMessage += "\t-h prints this message and exits\n"
    helpMessage += "\tFormat and default values (string values must be either quoted or without whitespace):"
    helpMessage += "\n\tfederation name (string): " + configuration.federation_name
    helpMessage += "\n\tfederate type (string): " + configuration.federate_type
    helpMessage += "\n\tfederate name (string): " + configuration.federate_name
    helpMessage += "\n\tpassword (string): " + configuration.plain_text_password
    helpMessage += "\n\tFOM module (string - default list): "
    for module in configuration.fom_modules:
        helpMessage += " \"" + module + "\""
    helpMessage += "\n"

    # Process arguments starting from index 1 (skip script name)
    argvToken = 0
    while argvToken < len(argv) - 1:
        argvToken += 1
        argument = argv[argvToken]
        if (argument == "-c"):
            configuration.fom_modules.clear()
        elif (argument == "-i"):
            configuration.callback_model = Enums.CallbackModel.HLA_IMMEDIATE
        elif (argument == "-h"):
            doHelp = True
            configuration.fom_modules.clear()
        elif (argvToken >= len(argv) - 1):
            doHelp = True
            log_info("Argument " + argument + " missing value\n")
        else:
            if (argument == "-F"):
                argvToken += 1
                configuration.federation_name = argv[argvToken]
            elif (argument == "-t"):
                argvToken += 1
                configuration.federate_type = argv[argvToken]
            elif (argument == "-m"):
                argvToken += 1
                configuration.fom_modules.append(argv[argvToken])
            elif (argument == "-p"):
                argvToken += 1
                configuration.plain_text_password = argv[argvToken]
            elif (argument == "-n"):
                argvToken += 1
                log_info(f"Configuration name: {argv[argvToken]}")
            elif (argument == "-r"):
                argvToken += 1
                log_info(f"RTI address: {argv[argvToken]}")
            elif (argument == "-a"):
                argvToken += 1
                log_info(f"Additional settings: {argv[argvToken]}")

    if (doHelp):
        log_info(helpMessage)

    return not doHelp

def main(argc: int, argv: list):
    """
        Execute standardized federate lifecycle: configure, connect, create/join federation, publish/subscribe, run, resign.

        Args:
            argc (int): Number of command-line arguments.
            argv (list): List of argument strings including program name.
        Returns:
            int: Exit code (0 success, 1 on failure paths).
        Exceptions:
            Catches KeyboardInterrupt and generic Exception to ensure cleanup; returns corresponding codes.
    """

    aConfig = Configuration()
    aConfig.federation_name = "MAKsimple"
    aConfig.federate_type = "Aircraft"
    aConfig.federate_name = "Aircraft_" + str(os.getpid())
    aConfig.fom_modules.append("MAKsimple1516_2025.xml")
    aConfig.fom_modules.append("MAKsimpleExtension1516_2025.xml")
    
    if (not processArguments(argc, argv, aConfig)):
        exit(0)

    if aConfig.federate_type != "Aircraft" and aConfig.federate_name == ("Aircraft_" + str(os.getpid())):
        aConfig.federate_name = aConfig.federate_type + str(os.getpid())

    federate = simpleFederate(aConfig)

    try:
        if not federate.my_rti_ambassador.my_msg_handler.is_connected():
            # Step 1: Connect to RTI
            if not federate.connect():
                log_error("Failed to connect to RTI")
                return 1
            
            if not federate.list_federation_executions():
                log_error("Failed to list federation executions")
                return 1
            
            # Step 2: Create federation execution
            if not federate.create_fed_ex():
                log_error("Failed to create federation execution")
                return 1
            
            # Step 3: Join federation execution
            if not federate.join():
                log_error("Failed to join federation execution")
                federate.resign_and_destroy()
                return 1
            
            # Step 4: Publish, subscribe, and register objects
            if not federate.publish_subscribe_and_register_object():
                log_error("Failed to set up publications and subscriptions")
                federate.resign_and_destroy()
                return 1
            
            if not federate.publish_subscribe_interaction():
                log_error("Failed to set up interaction publications and subscriptions")
                federate.resign_and_destroy()
                return 1
        
        # Step 6: Run the main federate loop
        federate.run_federate(run_time_seconds=60)
        
        # Step 7: Clean up
        federate.resign_and_destroy()
        
        print("Federate execution completed successfully!")
        return 0
            
    except KeyboardInterrupt:
        log_error("\nFederate execution interrupted by user")
        federate.resign_and_destroy()
        return 0
    except Exception as e:
        log_error(f"Error during federate execution: {e}")
        federate.resign_and_destroy()
        return 1
                

#Execution Begin
if __name__ == "__main__":
    import sys
    argc = len(sys.argv)
    argv = sys.argv[0] if argc > 0 else ""
    exit_code = main(argc, sys.argv)
    sys.exit(exit_code)