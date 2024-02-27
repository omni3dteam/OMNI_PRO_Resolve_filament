#!/usr/bin/python3
#Libraries
import time
import json
import linecache
from enum import IntEnum, Enum
from pathlib import Path
import os, stat, glob
# Python dsf API
from dsf.connections import InterceptConnection, InterceptionMode
from dsf.commands.code import CodeType
from dsf.object_model import MessageType
from dsf.connections import CommandConnection
from dsf.connections import SubscribeConnection, SubscriptionMode
##################################### Abstarct ###########################################
### This program is designed to resolve tool assigment when file is selected for printing.
### It takes input from three subsystems: tray management,  rfid management, and meta-data from gcode file.
### knowledge from these subsystems is then run through resolve_filament algorithm.
### algorithm outputs a tool change object, that describes which tool should be changed.
### Tool change is then applied to gcode file, and sendt to printer for processing.
file_path = "/opt/dsf/sd/gcodes/"
# Connect to dsf socket
command_connection = CommandConnection(debug=False)
command_connection.connect()
# function to return neighbouring tool number from tool number
def return_tools_as_string(tools):
    string_tools = []
    for i in range(0, len(tools)):
        if tools[i] == 0:
            string_tools.append("T0")
        elif tools[i] == 1:
            string_tools.append("T1")
        elif tools[i] == 2:
            string_tools.append("T2")
        elif tools[i] == 3:
            string_tools.append("T3")
    return string_tools
# function to return neighbouring tool
def return_neighbour_tool(tool):
    if tool > 1:
        return tool - 2
    else:
        return tool + 2
# function used to return meta data parsed from gcode file
def get_data_from_gcode(file_path):
    extruders_data = []
    material_data = []
    with open(file_path) as f:
        lines = f.readlines()
        for line in lines:
            arr = line.split(',')
            if arr[0] == ";   autoConfigureMaterial":
                arr.pop(0)
                for material in arr:
                     material_data.append(material.rstrip())
            elif arr[0] == ";   autoConfigureExtruders":
                arr.pop(0)
                if arr[0].rstrip() == "Both Extruders (HIPS-20)":
                    extruders_data.append(0)
                    extruders_data.append(1)
                    material_data.append("HIPS-20")
                else:
                    extruders_data.append(0)
                break
    return extruders_data, material_data
# TODO Design algorithm to resolve filament <-> tool relation at the start of print
def resolve_filament(original_tools, materials):
    job_original_toolheads = original_tools
    job_materials = materials
    # Get tray states
    res = command_connection.perform_simple_code("M1102")
    tray_state = json.loads(res)
    tools_tray_array = [tray_state['T0'], tray_state['T1'], tray_state['T2'], tray_state['T3']]
    # Get current filaments loaded
    # tools_rfid_array = []
    # for i in range (0,4):
    #     res = command_connection.perform_simple_code("M1002 S{}".format(i))
    #     rfid_data = json.loads(res)
    #     tools_rfid_array.append(rfid_data)
    # All data gathered, now try to resolve tool number
    new_tools = [0,0]
    tool_iterator = 0
    for tool in job_original_toolheads:
    ## First check if selected tool have proper or any filament present
        if tools_tray_array[tool] == 2:
            # i.e we have filament present
            ## for now just pass same tool number. later TODO: check material, colour and amount left
            new_tools[tool_iterator] = tool
        else:
        # check if filament is present on other tool
            neighbour_tool = return_neighbour_tool(tool)
            if  tools_tray_array[neighbour_tool] == 1:
                new_tools[tool_iterator] = tool
            else:
                print("No filament present for tool{}".format(tool))
                new_tools[tool_iterator] = tool
        tool_iterator += 1
    return return_tools_as_string(new_tools)

def create_full_file_path(file_path, filename):
    try:
        f = filename.split('/')
        f.pop(0)
        f.pop(0)
        filename_with_subdirs = ""
        for folder in f:
            filename_with_subdirs = filename_with_subdirs + folder
            filename_with_subdirs = filename_with_subdirs + "/"
        filename_with_subdirs = filename_with_subdirs[:-1]
        full_filename = (file_path + f[-1].split('.')[0] + ".gcode")
        return full_filename
    except Exception as e:
        print(e)
        return ""

def modify_job_file(file_path, filename, tool_to_change, new_tool):
    try:
        f = filename.split('/')
        f.pop(0)
        f.pop(0)
        filename_with_subdirs = ""
        for folder in f:
            filename_with_subdirs = filename_with_subdirs + folder
            filename_with_subdirs = filename_with_subdirs + "/"
        filename_with_subdirs = filename_with_subdirs[:-1]

        tmp_filename = "tmp/" + f[-1].split('.')[0] + "_tmp.gcode"
        # tmp_filename = tmp_filename.replace(" ", "_")
        # filename_with_subdirs = filename_with_subdirs.replace(" ", "_")
        # file_path = file_path.replace(" ", "_")

        message = 'sudo cp {} {}'.format((file_path + filename_with_subdirs).replace(" ", "\ "), file_path + tmp_filename.replace(" ", "\ "))
        full_filename = (file_path + tmp_filename)

        os.system(message)
        # Grant ourself write permission
        full_filename = (file_path + tmp_filename)
        os.system("sudo chmod 777 " + full_filename.replace(" ", "\ "))
        # os.chmod(full_filename, (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO))
        # Read in the file
        filedata = None
        new_tool_it =  0
        for tool in tool_to_change:
            with open(full_filename, 'r') as file :
                filedata = file.read()
            # Replace the target string
                filedata = filedata.replace(tool, new_tool[new_tool_it])
            # Write the file out again
            with open(full_filename, 'w') as file :
                file.write(filedata)
            new_tool_it += 1
        return tmp_filename
    except Exception as e:
        print(e)

def intercept_start_print_request():
    filters = ["M32"]
    intercept_connection = InterceptConnection(InterceptionMode.PRE, filters=filters, debug=False)
    intercept_connection.connect()
    try:
        # Wait for a code to arrive.
        cde = intercept_connection.receive_code()
        # Tray 0 command handling:
        if cde.type == CodeType.MCode and cde.majorNumber == 32:
            intercept_connection.resolve_code(MessageType.Success)
            filename = cde.parameters[0].string_value
            folder_path = "/opt/dsf/sd/gcodes/"
            file_path = create_full_file_path(folder_path, filename)
            original_tools, materials = get_data_from_gcode(file_path)
            new_tools = resolve_filament(original_tools, materials)
            # new_tools = ["T0", "T2"]
            new_file = modify_job_file(folder_path, filename, return_tools_as_string(original_tools), new_tools)
            intercept_connection.close()
            return new_file, new_tools
    except Exception as e:
        print("Closing connection: ", e)
        intercept_connection.resolve_code(MessageType.Success)
        intercept_connection.close()

if __name__ == "__main__":
    #Configure everything on entry
    subscribe_connection = SubscribeConnection(SubscriptionMode.FULL)
    subscribe_connection.connect()
    previous_file = "none"
    tool_Value = ""
    os.system("sudo rm -rf /opt/dsf/sd/gcodes/tmp")
    os.system("mkdir /opt/dsf/sd/gcodes/tmp")
    os.system("sudo chown -R dsf:dsf /opt/dsf/sd/gcodes")
    os.system("sudo chmod 777 /opt/dsf/sd/gcodes/tmp")

    res = command_connection.perform_simple_code("G28 XY")

    while(True):
        # Wait for M32 to be sendt
        new_file, new_tools = intercept_start_print_request()
        if previous_file != new_file:
            pass
            # os.system('rm {}{}'.format(file_path, previous_file.replace(" ", "\ ")))
        # Before we start print, check if we loaded filamnents.
        filament_status = command_connection.perform_simple_code("M1102")
        tool_state = json.loads(filament_status)[new_tools[0]]

        # for tool in new_tools:
        #     # Filament present
        #     if json.loads(filament_status)[tool] == 0:
        #         pass
        #     # Filament not present
        #     elif json.loads(filament_status)[tool] == 1:
        #         pass
        #     # filament loaded
        #     elif json.loads(filament_status)[tool] == 2:
        #         tool_numeric_value = [int(i) for i in tool if i.isdigit()]
        #         message = "M1101 P{} S1".format(tool_numeric_value[0])
        #         command_connection.perform_simple_code(message)
        #         time.sleep(30)
        #         pass
        #     # filament primed
        #     elif json.loads(filament_status)[tool] == 3:
        #         pass

        message = "M32 "'"{}"'"".format(new_file)
        res = command_connection.perform_simple_code(message)
        time.sleep(5)
        status = 'processing'
        # Wait for print to finish
        while status != 'idle':
            status = command_connection.perform_simple_code("""M409 K"'state.status"'""")
            status = json.loads(status)["result"]
            tool = command_connection.perform_simple_code("T")
            tool = tool.split(" ")
            if tool[0] != "No":
                tool_Value = tool[1]
            else:
                pass
            time.sleep(1)
        # Retract filament
        # if tool_Value != "No tool is selected":
        #     print(tool_Value[:1])
        #     command_connection.perform_simple_code("M1101 P{} S2".format(tool_Value[:1]))
        # Allow use of print again button
        # command_connection.perform_simple_code("G28 XY")
        command_connection.perform_simple_code("M0")
        command_connection.perform_simple_code("M98 P""'/sys/stop.g'""")
        previous_file = new_file