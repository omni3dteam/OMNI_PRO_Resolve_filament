#!/usr/bin/python3
#Libraries
import time
import json
import linecache
from enum import IntEnum, Enum
from pathlib import Path
import os, stat
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
# simple wrapper class for returning tool name as string
# class tool_name(str, Enum):
#     TOOL_0 = "Left Extruder Spool 0",
#     TOOL_1 = "Right Extruder Spool 0",
#     TOOL_2 = "Left Extruder Spool 1",
#     TOOL_3 = "Right Extruder Spool 1"
#     def return_tool_name(tool):
#         if tool == 0:
#             return tool_name.TOOL_0
#         elif tool == 1:
#              return tool_name.TOOL_1
#         elif tool == 2:
#              return tool_name.TOOL_2
#         elif tool == 3:
#              return tool_name.TOOL_3
# function to return neighbouring tool number from tool number
def return_neighbour_tool(tool):
    if tool > 1:
        return tool - 2
    else:
        return tool + 2
# function to return drives corresponding to tool number
# def return_drives(tool):
#     if tool == 0:
#         return [0,2]
#     elif tool == 1:
#         return [1,4]
#     elif tool == 2:
#         return [0,3]
#     elif tool == 3:
#         return [1,5]
# TODO Design algorithm to resolve filament <-> tool relation at the start of print
def resolve_filament(job_original_toolheads):
    # Get tray states
    res = command_connection.perform_simple_code("M1102")
    tray_state = json.loads(res)
    tools_tray_array = [tray_state['Tool_0'], tray_state['Tool_1'], tray_state['Tool_2'], tray_state['Tool_3']]
    # Get RFID states
    tools_rfid_array = []
    for i in range (0,4):
        res = command_connection.perform_simple_code("M1002 S{}".format(i))
        rfid_data = json.loads(res)
        tools_rfid_array.append(rfid_data)
    # All data gathered, now try to resolve tool number
    new_tools = [0,0]
    tool_iterator = 0
    for tool in job_original_toolheads:
    ## First check if selected tool have proper any filament present
        if tools_tray_array[tool] == 1:
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
    return new_tools

# def change_drives(job_original_toolheads, new_toolheads):
#     new_tool_it = 0
#     for tool in job_original_toolheads:
#         # M563 P0 S"Left Extruder Spool 0" D0:2 H0 F0             ; define tool 0
#         drives_to_write = return_drives(new_toolheads[new_tool_it])
#         m563 = """M563 P{} S"{}" D{}:{} H{} F{}""".format(tool, tool_name.return_tool_name(tool) ,drives_to_write[0], drives_to_write[1], tool, tool)
#         res = command_connection.perform_simple_code(m563)
#         res = command_connection.perform_simple_code("M567 P{} E1.0:1.05".format(tool))
#         res = command_connection.perform_simple_code("G10 P{} R0 S0".format(tool))
#         print(m563)
#         new_tool_it += 1
class lines_to_read(IntEnum):
    Material = 9,
    tool_head_number = 13

def modify_job_file(file_path, filename, tool_to_change, new_tool):
    try:
        # Create copy of job file
        f = filename.split('.')
        tmp_filename = f[0] + "_tmp." + f[1]
        # Path(file_path + tmp_filename).touch()
        os.system('cp {}{} {}{}'.format(file_path, filename, file_path, tmp_filename))
        # file.write_text(file.read_text().replace('T0', 'T1'))
        # Grant ourself write permission
        os.chmod(file_path + tmp_filename, (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO))
        file = Path(file_path + filename)
        file.write_text(file.read_text().replace(tool_to_change, new_tool))
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
            filename = cde.parameters[0].string_value
            file_path = "/opt/dsf/sd/gcodes/"
            new_file = modify_job_file(file_path, filename, "T0", "T1")
            # # Open file and get tool head number and material
            # job_original_toolheads = [int(linecache.getline(file_path+filename, lines_to_read.tool_head_number).split(',',3)[1]), int(linecache.getline(file_path+filename, lines_to_read.tool_head_number).split(',',3)[2])]
            # job_materials = [str(linecache.getline(file_path+filename, lines_to_read.Material).split(',',3)[1]).rstrip(), str(linecache.getline(file_path+filename, lines_to_read.tool_head_number).split(',',3)[2]).rstrip()]
            # new_toolheads = resolve_filament(job_original_toolheads)
            # file.write_text(file.read_text().replace('T0', 'T1'))
            # material = linecache.getline(file_path, lines_to_read.Material).split(',', 3)[1]
            # print(material)
            #intercept_connection.ignore_code()
            intercept_connection.resolve_code(MessageType.Success)
            return new_file
    except Exception as e:
        print("Closing connection: ", e)
        intercept_connection.resolve_code(MessageType.Success)
        intercept_connection.close()

if __name__ == "__main__":
    #Configure everything on entry
    subscribe_connection = SubscribeConnection(SubscriptionMode.FULL)
    subscribe_connection.connect()
    while(True):
        # Wait for M32 to be sendt
        new_file = intercept_start_print_request()
        time.sleep(5)
        message = "M32 {}".format(new_file)
        res = command_connection.perform_simple_code(message)
        time.sleep(5)
        status = 'processing'
        # Wait for print to finish
        while status != 'idle':
            status = command_connection.perform_simple_code("""M409 K"'state.status"'""")
            status = json.loads(status)["result"]
            time.sleep(5)
        # Delete temporary copy and end loop
        os.system('rm {}{}'.format(file_path, new_file))
