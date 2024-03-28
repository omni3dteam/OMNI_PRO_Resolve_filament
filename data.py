from dsf.connections import CommandConnection
import json


class Data:
    '''object used to aquired data from printer and gcode files'''
    def __init__(self):
        self.command_connection = CommandConnection(debug=False)
        self.command_connection.connect()
    
    def get_data_from_gcode(self, file_path):
        '''Choose what parser to use'''
        with open(file_path) as f:
            lines = f.readlines()
            if lines[0] == ";flavor:reprap\n":
                return self.get_data_from_cura_gcode(file_path)
            else:
                return self.get_data_from_default_slicer(file_path)

    def get_data_from_default_slicer(self, file_path):
        '''Get data generated from default slicer'''
        extruders_data = []
        material_data = []
        # Skip thumbnail
        try:
            line_counter = 0
            with open(file_path) as f:
                lines = f.readlines()
                for line in lines:
                    if line == "; thumbnail end\n":
                        break
                    else:
                        line_counter += 1
        except Exception as e:
            print(e)
            return extruders_data, material_data
        # Parse data
        try:
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
                            extruders_data.append("T0")
                            extruders_data.append("T1")
                            material_data.append("HIPS-20")
                        else:
                            extruders_data.append("T0")
                        break
                    elif counter > 500:
                        # res = command_connection.write_message(MessageType.Error, "Wrong slicer version please use slicer version >= 5.1", True, LogLevel.Warn)
                        return [None, None], [None, None]
                    counter = counter + 1
        except Exception as e:
            print(e)
        return extruders_data, material_data

    def get_data_from_cura_gcode(self, file_path):
        '''Get data from cura generated file'''
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
                            extruders_data.append("T0")
                            extruders_data.append("T1")
                            material_data.append("Default")
                            material_data.append("Default")
                        else:
                            extruders_data.append("T0")
                            material_data.append("Default")
                        break
                    elif counter > 500:
                        return [None, None], [None, None]
                        counter = counter + 1
        except Exception as e:
            print(e)
        return extruders_data, material_data

    def get_current_tray_state(self):
        res = self.command_connection.perform_simple_code("M1102")
        tray_state = json.loads(res)
        # tools_tray_array = [tray_state['T0'], tray_state['T1'], tray_state['T2'], tray_state['T3']]
        return tray_state
