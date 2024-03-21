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
from dsf.object_model import MessageType, LogLevel
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
def get_data_from_cura_gcode(file_path):
    extruders_data = []
    material_data = []
    try:
        with open(file_path) as f:
            lines = f.readlines()
            counter = 0
            for line in lines:
                arr = line.split(':')
                if arr[0].rstrip() == ";Filament used":
                    arr.pop(0)
                    arr = arr[0].split(',')
                    second_extruder = float(arr[1].rstrip()[:-1])
                    if second_extruder > 0:
                        extruders_data.append(0)
                        extruders_data.append(1)
                        material_data.append("Default")
                        material_data.append("Default")
                    else:
                        extruders_data.append(0)
                        material_data.append("Default")
                    break
                elif counter > 500:
                   return [-1,-1], [-1,-1]
                counter  = counter + 1
    except Exception as e:
        print(e)
    return extruders_data, material_data
def get_data_from_gcode(file_path):
     with open(file_path) as f:
        lines = f.readlines()
        if lines[0] == ";FLAVOR:RepRap\n":
            return get_data_from_cura_gcode(file_path)
        else:
            return get_data_from_default_slicer(file_path)

def get_data_from_default_slicer(file_path):
    extruders_data = []
    material_data = []
    try:
        line_counter = 0
        with open(file_path) as f:
            lines = f.readlines()
            for line in lines:
                if line == "; thumbnail end\n":
                    break
                else:
                    line_counter += 1

        with open(file_path) as f:
            lines = f.readlines()
            lines = lines[line_counter:]
            counter = 0
            for line in lines:
                arr = line.split(',')
                if arr[0].rstrip() == ";   autoConfigureMaterial":
                    arr.pop(0)
                    for material in arr:
                         material_data.append(material.rstrip())
                elif arr[0].rstrip() == ";   autoConfigureExtruders":
                    arr.pop(0)
                    if arr[0].rstrip() == "Both Extruders (HIPS-20)":
                        extruders_data.append(0)
                        extruders_data.append(1)
                        material_data.append("HIPS-20")
                    else:
                        extruders_data.append(0)
                    break
                elif counter > 500:
                   res = command_connection.write_message(MessageType.Error, "Wrong slicer version please use slicer version >= 5.1", True, LogLevel.Warn)
                   return [-1,-1], [-1,-1]
                counter  = counter + 1
    except Exception as e:
        print(e)
    return extruders_data, material_data
# TODO Design algorithm to resolve filament <-> tool relation at the start of print
def resolve_filament(original_tools, materials):
    job_original_toolheads = original_tools
    job_materials = materials
    # Get tray states
    res = command_connection.perform_simple_code("M1102")
    tray_state = json.loads(res)
    tools_tray_array = [tray_state['T0'], tray_state['T1'], tray_state['T2'], tray_state['T3']]
    
    # try to resolve filaments
    new_tools = [-1,-1]
    tool_iterator = 0
    for tool in job_original_toolheads:
    ## First check if selected tool have proper or any filament present
        if (tools_tray_array[tool] == 2) or (tools_tray_array[tool] == 3):
            # i.e we have filament present
            ## for now just pass same tool number. later TODO: check material, colour and amount left
            new_tools[tool_iterator] = tool
        else:
        # check if filament is present on other tool
            neighbour_tool = return_neighbour_tool(tool)
            if  (tools_tray_array[neighbour_tool] == 3) or (tools_tray_array[neighbour_tool] == 2):
                new_tools[tool_iterator] = neighbour_tool
            else:
                print("No filament present for tool{}".format(tool))
                new_tools[tool_iterator] = tool
        tool_iterator += 1
    # ovverride resolving by user
    if tools_tray_array[0] == 3:
        new_tools[0] = 0
    elif tools_tray_array[2] == 3:
        new_tools[0] = 2
    if new_tools[1] != -1:
        if tools_tray_array[1] == 3:
            new_tools[1] = 1
        elif tools_tray_array[3] == 3:
            new_tools[1] = 3

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
        full_filename = (file_path + filename_with_subdirs)
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

        tmp_filename = "tmp/" + f[-1].split('.')[0] + ".gcode"
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
def is_it_print_again_file(file_path):
    f = file_path.split('/')
    if f[-1].endswith('.gcode'):
        f[-1] = f[-1][:-6]
    if f[-1].find("_tmp") != -1:
        return True
    else:
        return False

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
            intercept_connection.close()
            filename = cde.parameters[0].string_value
            folder_path = "/opt/dsf/sd/gcodes/"
            file_path = create_full_file_path(folder_path, filename)
            original_tools, materials = get_data_from_gcode(file_path)
            if original_tools[0] == -1:
                return "", [-1,-1]
            new_tools = resolve_filament(original_tools, materials)
            # new_tools = ["T0", "T2"]
            new_file = modify_job_file(folder_path, filename, return_tools_as_string(original_tools), new_tools)
            return new_file, new_tools
    except Exception as e:
        print("Closing connection: ", e)
        intercept_connection.resolve_code(MessageType.Success)
        intercept_connection.close()

if __name__ == "__main__":
    #Configure everything on entry
    previous_file = "none"
    tool_Value = ""
    os.system("sudo rm -rf /opt/dsf/sd/gcodes/tmp")
    os.system("mkdir /opt/dsf/sd/gcodes/tmp")
    os.system("sudo chown -R dsf:dsf /opt/dsf/sd/gcodes")
    os.system("sudo chmod 777 /opt/dsf/sd/gcodes/tmp")

    while(True):
        # Wait for M32 to be sendt
        new_file, new_tools = intercept_start_print_request()
        if new_file != "":
            # Before we start print, check if we loaded filamnents.
            filament_status = command_connection.perform_simple_code("M1102")
            tool_state = json.loads(filament_status)[new_tools[0]]

            continue_print = False

            for tool in new_tools:
                # Filament present
                if json.loads(filament_status)[tool] == 0:
                    res = command_connection.write_message(MessageType.Error, "No filament needed to print", True, LogLevel.Warn)
                    continue_print = False
                # Filament not present
                elif json.loads(filament_status)[tool] == 1:
                    res = command_connection.write_message(MessageType.Error, "No filament needed to print", True, LogLevel.Warn)
                    continue_print = False
                # filament loaded
                elif json.loads(filament_status)[tool] == 2:
                    tool_numeric_value = [int(i) for i in tool if i.isdigit()]
                    message = "M1101 P{} S1 A1".format(tool_numeric_value[0])
                    res = command_connection.perform_simple_code(message)
                    time.sleep(30)
                    continue_print = True
                    pass
                # filament primed
                elif json.loads(filament_status)[tool] == 3:
                    continue_print = True
                    pass


            if continue_print == True:
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
                    time.sleep(5)

                time.sleep(1)

                subscribe_connection = SubscribeConnection(SubscriptionMode.FULL)
                subscribe_connection.connect()

                object_model = subscribe_connection.get_object_model()
                z_position = object_model.move.axes[2].machine_position

                command_connection.perform_simple_code("G28 XY")

                if z_position < 150.0:
                    command_connection.perform_simple_code("G90")
                    command_connection.perform_simple_code("G0 Z250 F1500")
                else:
                    command_connection.perform_simple_code("G91")
                    command_connection.perform_simple_code("G1 Z100 F1500")
                command_connection.perform_simple_code("G90")

                command_connection.perform_simple_code("M106 P0 S0")
                command_connection.perform_simple_code("M106 P0 S0")

                command_connection.perform_simple_code("T1")
                command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/goto-clean-t1.g"'"")
                command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/clean.g"'"")

                command_connection.perform_simple_code("T0")
                command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/goto-clean-t0.g"'"")
                command_connection.perform_simple_code("M98 P"'" /sys/machine-specific/clean.g"'"")

                command_connection.perform_simple_code("M42 P9  S0")
                command_connection.perform_simple_code("M42 P10 S0")
                command_connection.perform_simple_code("M42 P11 S0")

                command_connection.perform_simple_code("""M98 P"'/sys/configure-tools.g"'""")

