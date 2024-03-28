from dsf.connections import InterceptConnection, InterceptionMode
from dsf.commands.code import CodeType
from dsf.object_model import MessageType
from dsf.connections import CommandConnection

class Resolver:
    '''Main object used to resolve filament at the start of a print'''
    def __init__(self):
        '''Resolver object constructor'''
        self.command_connection = CommandConnection(debug=False)
        self.command_connection.connect()

    def intercept_print_start_mcode(self):
        '''Intercept incoming M32 code'''
        filters = ["M32"]
        intercept_connection = InterceptConnection(InterceptionMode.PRE, filters=filters, debug=False)
        intercept_connection.connect()
        try:
            # Wait for a code to arrive.
            cde = intercept_connection.receive_code()
            if cde.type == CodeType.MCode and cde.majorNumber != 32:
                return None
            file_name = cde.parameters[0].string_value
            intercept_connection.resolve_code(MessageType.Success)
            return file_name
        except Exception as e:
            print("Closing connection: ", e)
            intercept_connection.resolve_code(MessageType.Error)
            intercept_connection.close()
            return None

    def resolve_filament(self, original_tools, tray_state, materials, filaments):
        # Get tray states
        tools_tray_array = [(tray_state['T0'], "T0") , (tray_state['T2'], "T2"), (tray_state['T1'], "T1"), (tray_state['T3'], "T3")]
        # try to resolve filaments
        new_tools = [None, None]
        original_tools = ["T0", "T1"]
        tool_iterator = 0
        special_mode = False
        # Check if we are printing with both extruders
        if len(original_tools) < 2:
            # If we are printing with only one extruder, check whole range of tools.
            for tool_condition in range(2, 4):
                for tool_iterator in range(3,-1, -1):
                    if tools_tray_array[tool_iterator][0] == tool_condition:
                        new_tools[0] = tools_tray_array[tool_iterator][1]
            # After resolving, check if extruder A have tool assigned, if not - show error.
            if (new_tools[0] == None):
                # Send Error message and exit
                return [None, None]
        else:
            # else, choose only from tools belonging to extruder
                for tool_condition in range(2, 4):
                    for tool_iterator in range(1,-1, -1):
                        if tools_tray_array[tool_iterator][0] == tool_condition:
                            if new_tools[0] != tools_tray_array[tool_iterator][1]:
                                new_tools[0] = tools_tray_array[tool_iterator][1]

                for tool_condition in range(2, 4):
                    for tool_iterator in range(3, 1, -1):
                        if tools_tray_array[tool_iterator][0] == tool_condition:
                            if new_tools[0] != tools_tray_array[tool_iterator][1]:
                                new_tools[1] = tools_tray_array[tool_iterator][1]

                # After resolving, check if extruder A and B have tools assigned, if not check for 'special mode' or show error.
                # Special mode means using same extruder for two different materials. For example if one of extruders is broken.
                # But first check for some logic errors and [None, None] output
                if (new_tools[0] == new_tools[1]):
                    # exit with error
                    return [None, None]
                if (new_tools[0] == None) and (special_mode):
                    # Check if we can use T3 or T1 for this job.
                    pass
                if (new_tools[1] == None) and (special_mode):
                    # Check if we can use T2 or T0 for this job.
                    pass
        return new_tools