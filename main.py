"""Resolver main file"""
from dsf.connections import InterceptConnection, InterceptionMode
from dsf.commands.code import CodeType
from dsf.object_model import MessageType
from dsf.connections import CommandConnection
import time
import json
import os

from resolver import Resolver
from file_modifier import Modifier
from data import Data
from interface import Tools, RFID, Machine

def main_loop():
    '''Main loop for filament resolve program'''
    new_file = Resolver.intercept_print_start_mcode(Resolver())
    path_to_file = Modifier.extract_file_name(Modifier(), new_file)
    original_tools, materials = Data.get_data_from_gcode(Data(), path_to_file)
    current_tools_state = Tools.get_current_tools_state(Tools())
    current_filaments = RFID.get_current_loaded_filaments(RFID())
    new_tools = Resolver.resolve_filament(Resolver(), original_tools, current_tools_state ,materials, current_filaments)
    if new_tools[0] == None and new_tools[1] == None:
        # Send message indicating that we cant print,
        # but let user decide if he wants to proceed
        #res = write_message....
        # if res == 'ok':
        return -1
    
    new_tmp_file = Modifier.modify_job_file(Modifier(), path_to_file, original_tools, new_tools)
    current_tools_state = Tools.get_current_tools_state(Tools())
    continue_print = False
    for tool in new_tools:
        tool_number = int(tool[1:])
        if current_tools_state[tool_number] == 3:
            continue_print = True
        elif current_tools_state[tool_number] == 2:
            # Send prime command
            continue_print = True
        else:
            # Send info that there is no filament on tools we wish to use.
            continue_print = False
        
    # This is a code space to put additional functionality that should be implemented at the START of print
    
    # Start Print
    if continue_print:
        # Start print with tmp file
        command_connection = CommandConnection(debug=False).connect()
        command_connection.perform_simple_code("M32 "'"{}"'"".format(new_tmp_file))
        time.sleep(5)
        status = 'processing'
        # Wait for print to finish/stop
        while status != 'idle':
            status = command_connection.perform_simple_code("""M409 K"'state.status"'""")
            status = json.loads(status)["result"]
            time.sleep(5)
    else:
        return -1
        
    # This is a code space for additional functionality that should be implemented at the END of print
    machine = Machine()

    machine.home_x_y()
    machine.move_platform_down()
    machine.lower_temperatures()
    machine.clean_extruder_a()
    machine.turn_off_fans()
    machine.reset_tool_configuration()

    return 0

if __name__ == "__main__":
    '''Main function'''
    print("Resolver started!")
    # Clear tmp files
    os.system("sudo rm -rf /opt/dsf/sd/gcodes/tmp")
    os.system("mkdir /opt/dsf/sd/gcodes/tmp")
    os.system("sudo chown -R dsf:dsf /opt/dsf/sd/gcodes")
    os.system("sudo chmod 777 /opt/dsf/sd/gcodes/tmp")

    while (True):
        main_loop()
