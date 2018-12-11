import inspect
import re
from PyQt5 import QtWidgets

def parse_plan_parameters(plan_func):
    def create_parameter(description, annotation):

        param1 = None
        param2 = None
        def_val = ''
        if description.find('=') != -1:
            def_val = re.sub(r'.*=', '', description)
        if annotation == int:
            param1 = QtWidgets.QSpinBox()
            param1.setMaximum(100000)
            param1.setMinimum(-100000)
            def_val = int(def_val)
            param1.setValue(def_val)
        elif annotation == float:
            param1 = QtWidgets.QDoubleSpinBox()
            param1.setMaximum(100000)
            param1.setMinimum(-100000)
            def_val = float(def_val)
            param1.setValue(def_val)
        elif annotation == bool:
            param1 = QtWidgets.QCheckBox()
            if def_val == 'True':
                def_val = True
            else:
                def_val = False
            param1.setCheckState(def_val)
            param1.setTristate(False)
        elif annotation == str:
            param1 = QtWidgets.QLineEdit()
            def_val = str(def_val)
            param1.setText(def_val)

        if param1 is not None:
            param2 = QtWidgets.QLabel(description)

        return param1, param2

    parameter_values = []
    parameter_descriptions = []
    parameter_types = []

    signature = inspect.signature(plan_func)
    for i in range(0, len(signature.parameters)):

        description = re.sub(r':.*?=', '=', str(signature.parameters[list(signature.parameters)[i]]))
        if description == str(signature.parameters[list(signature.parameters)[i]]):
            description = re.sub(r':.*', '', str(signature.parameters[list(signature.parameters)[i]]))
        parameter_type = signature.parameters[list(signature.parameters)[i]].annotation
        [parameter_value, parameter_description] = create_parameter(description, parameter_type)

        if parameter_value:
            parameter_values.append(parameter_value)
            parameter_descriptions.append(parameter_description)
            parameter_types.append(parameter_type)

    return parameter_values, parameter_descriptions, parameter_types


def  parse_grid_parameters(parameter_descriptions, parameter_values, parameter_types):
    run_params = {}
    for i in range(len(parameter_values)):
        if (parameter_types[i] == int):
            run_params[parameter_descriptions[i].text().split('=')[0]] = parameter_values[i].value()
        elif (parameter_types[i] == float):
            run_params[parameter_descriptions[i].text().split('=')[0]] = parameter_values[i].value()
        elif (parameter_types[i] == bool):
            run_params[parameter_descriptions[i].text().split('=')[0]] = bool(parameter_values[i].checkState())
        elif (parameter_types[i] == str):
            run_params[parameter_descriptions[i].text().split('=')[0]] = parameter_values[i].text()

