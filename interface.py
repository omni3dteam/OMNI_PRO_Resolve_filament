import json
from dsf.connections import CommandConnection
from dsf.connections import SubscribeConnection, SubscriptionMode
class Tools:
    '''Object used to interact with printer filament tray'''
    def __init__(self):
        '''Tool constructor'''
        self.command_connection = CommandConnection(debug=False)
        self.command_connection.connect()

    def get_current_tools_state(self):
        res = self.command_connection.perform_simple_code("M1102")
        tray_state = json.loads(res)
        # tools_tray_array = [tray_state['T0'], tray_state['T1'], tray_state['T2'], tray_state['T3']]
        return tray_state
    
class RFID:
    '''Object used to interact with rfid'''
    def __init__(self):
        '''RFID constructor'''
        self.command_connection = CommandConnection(debug=False)
        self.command_connection.connect()
    
    def get_current_loaded_filaments(self):
        return [None, None, None, None]
    
class Machine:
    '''Object used to interact with core printer functions'''
    def __init__(self):
        '''Machine constructor'''
        self.command_connection = CommandConnection(debug=False).connect()
        self.subscribe_connection = SubscribeConnection(SubscriptionMode.FULL).connect()

    def home_x_y(self):
        '''Home machine'''
        self.command_connection.perform_simple_code("G28 XY")
    
    def move_platform_down(self):
        '''Move platform down'''
        object_model = self.subscribe_connection.get_object_model()
        z_position = object_model.move.axes[2].machine_position

        if z_position < 150.0:
            self.command_connection.perform_simple_code("G90")
            self.command_connection.perform_simple_code("G0 Z250 F1500")
        else:
            self.command_connection.perform_simple_code("G91")
            self.command_connection.perform_simple_code("G1 Z100 F1500")
        self.command_connection.perform_simple_code("G90")
    
    def lower_temperatures(self):
        self.command_connection.perform_simple_code("M106 P0 S0")
        self.command_connection.perform_simple_code("M106 P0 S0")

    def clean_extruder_a(self):
        self.command_connection.perform_simple_code("T0")
        self.command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/goto-clean-t0.g"'"")
        self.command_connection.perform_simple_code("M98 P"'" /sys/machine-specific/clean.g"'"")

    def clean_extruder_b(self):
        self.command_connection.perform_simple_code("T1")
        self.command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/goto-clean-t1.g"'"")
        self.command_connection.perform_simple_code("M98 P"'"/sys/machine-specific/clean.g"'"")

    def clean_both_extruders(self):
        self.clean_extruder_a()
        self.clean_extruder_b()

    def turn_off_fans(self):
        self.command_connection.perform_simple_code("M42 P9  S0")
        self.command_connection.perform_simple_code("M42 P10 S0")
        self.command_connection.perform_simple_code("M42 P11 S0")

    def reset_tool_configuration(self):
        self.command_connection.perform_simple_code("""M98 P"'/sys/configure-tools.g"'""")




        
