"""Module used to manipulate gcode file for processing"""
import os

class Modifier:
    '''Object used to manipulate gcode job file'''
    def __init__(self):
        '''modifier object constructor'''
        self.file_path = "/opt/dsf/sd/gcodes/"
        self.tmp_file_path = "/opt/dsf/sd/gcodes/tmp/"

    def extract_file_name(self, file_name):
        '''Extract filename from file path WITH USER SUBDIRECTORIES'''
        try:
            f = file_name.split('/')
            f.pop(0)
            f.pop(0)
            filename_with_subdirs = ""
            for folder in f:
                filename_with_subdirs = filename_with_subdirs + folder
                filename_with_subdirs = filename_with_subdirs + "/"
            filename_with_subdirs = filename_with_subdirs[:-1]
            # full_filename = file_path + f[-1].split('.')[0] + ".gcode"
            full_filename = self.file_path + filename_with_subdirs
            return full_filename
        except Exception as e:
            print(e)
            return None

    # def create_file_path(self, file_name, file_path="/opt/dsf/sd/gcodes"):
    #     '''Create full filepath from file name'''
    #     try:
    #         filename_with_subdirs = self.extract_file_name(file_name)
    #         full_filename = file_path + f[-1].split('.')[0] + ".gcode"
    #         full_filename = file_path + filename_with_subdirs
    #         return full_filename
    #     except Exception as e:
    #         print(e)
    #         return None

    def modify_job_file(self, file_path, tool_to_change, new_tool):
        '''Modify original gcode file and save as temporary file'''
        try:
            f = file_path.split('/')
            # f.pop(0)
            # f.pop(0)
            # filename_with_subdirs = ""
            # for folder in f:
            #     filename_with_subdirs = filename_with_subdirs + folder
            #     filename_with_subdirs = filename_with_subdirs + "/"
            # filename_with_subdirs = filename_with_subdirs[:-1]

            # tmp_filename = f[-1].split('.')[0] + ".gcode"
            tmp_file_name = self.tmp_file_path +  f[-1].split('.')[0].replace(" ", "\ ") + ".gcode"
            message = 'sudo cp {} {}'.format(file_path.replace(" ", "\ "), tmp_file_name)
            os.system(message)
            # Grant ourself write permission
            os.system("sudo chmod 777 " + tmp_file_name)
            # Read in the file
            filedata = None
            new_tool_it = 0
            for tool in tool_to_change:
                with open(tmp_file_name, 'r', encoding="utf-8") as file:
                    filedata = file.read()
                # Replace the target string
                    filedata = filedata.replace(tool, new_tool[new_tool_it])
                # Write the file out again
                with open(tmp_file_name, 'w', encoding="utf-8") as file:
                    file.write(filedata)
                new_tool_it += 1
            return tmp_file_name
        except Exception as e:
            print(e)
            return None
