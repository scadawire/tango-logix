import time
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, Attr, CmdArgType, UserDefaultAttrProp
from tango.server import Device, attribute, command, DeviceMeta
from tango.server import class_property, device_property
from tango.server import run
import os
import json
from threading import Thread
from threading import Lock
import datetime
from json import JSONDecodeError
from pylogix import PLC

class LogixDevice(Device, metaclass=DeviceMeta):

    host = device_property(dtype=str, default_value="192.168.1.10")
    processor_slot = device_property(dtype=int, default_value=0)
    micro800 = device_property(dtype=bool, default_value=False)
    init_dynamic_attributes = device_property(dtype=str, default_value="")
    client = None

    @attribute
    def time(self):
        return time.time()

    @command(dtype_in=str)
    def add_dynamic_attribute(self, tagName,
            variable_type_name="DevString", min_value="", max_value="",
            unit="", write_type_name="", label="", min_alarm="", max_alarm="",
            min_warning="", max_warning=""):
        if tagName == "":
            return

        prop = UserDefaultAttrProp()
        variableType = self.stringValueToVarType(variable_type_name)
        writeType = self.stringValueToWriteType(write_type_name)

        if(min_value != "" and min_value != max_value): prop.set_min_value(min_value)
        if(max_value != "" and min_value != max_value): prop.set_max_value(max_value)
        if(unit != ""): prop.set_unit(unit)
        if(label != ""): prop.set_label(label)
        if(min_alarm != ""): prop.set_min_alarm(min_alarm)
        if(max_alarm != ""): prop.set_max_alarm(max_alarm)
        if(min_warning != ""): prop.set_min_warning(min_warning)
        if(max_warning != ""): prop.set_max_warning(max_warning)

        attr = Attr(tagName, variableType, writeType)
        attr.set_default_properties(prop)

        self.add_attribute(attr, r_meth=self.read_dynamic_attr, w_meth=self.write_dynamic_attr)
        self.info_stream("Added dynamic attribute: " + tagName)

    def stringValueToVarType(self, variable_type_name) -> CmdArgType:
        if variable_type_name == "DevBoolean":
            return CmdArgType.DevBoolean
        if variable_type_name == "DevLong":
            return CmdArgType.DevLong
        if variable_type_name == "DevDouble":
            return CmdArgType.DevDouble
        if variable_type_name == "DevFloat":
            return CmdArgType.DevFloat
        if variable_type_name == "DevString":
            return CmdArgType.DevString
        if variable_type_name == "":
            return CmdArgType.DevString
        raise Exception("Unsupported variable_type: " + variable_type_name)

    def stringValueToWriteType(self, write_type_name) -> AttrWriteType:
        if write_type_name == "READ":
            return AttrWriteType.READ
        if write_type_name == "WRITE":
            return AttrWriteType.WRITE
        if write_type_name == "READ_WRITE":
            return AttrWriteType.READ_WRITE
        if write_type_name == "READ_WITH_WRITE":
            return AttrWriteType.READ_WITH_WRITE
        if write_type_name == "":
            return AttrWriteType.READ_WRITE
        raise Exception("Unsupported write_type: " + write_type_name)

    def read_dynamic_attr(self, attr):
        name = attr.get_name()
        value = self.client.Read(name).Value
        self.debug_stream(f"Read value from tag {name}: {value}")
        attr.set_value(value)

    def write_dynamic_attr(self, attr):
        value = attr.get_write_value()
        name = attr.get_name()
        self.client.Write(name, value)
        self.debug_stream(f"Wrote value to tag {name}: {value}")

    def init_device(self):
        self.set_state(DevState.INIT)
        self.get_device_properties(self.get_device_class())

        self.info_stream(f"Connecting to PLC at {self.host}")
        self.client = PLC()
        self.client.IPAddress = self.host
        self.client.ProcessorSlot = self.processor_slot
        self.client.Micro800 = self.micro800

        if self.init_dynamic_attributes != "":
            try:
                attributes = json.loads(self.init_dynamic_attributes)
                for attributeData in attributes:
                    self.add_dynamic_attribute(
                        attributeData["name"],
                        attributeData.get("data_type", ""),
                        attributeData.get("min_value", ""),
                        attributeData.get("max_value", ""),
                        attributeData.get("unit", ""),
                        attributeData.get("write_type", ""),
                        attributeData.get("label", ""),
                        attributeData.get("min_alarm", ""),
                        attributeData.get("max_alarm", ""),
                        attributeData.get("min_warning", ""),
                        attributeData.get("max_warning", "")
                    )
            except JSONDecodeError as e:
                raise e

        self.set_state(DevState.ON)

if __name__ == "__main__":
    deviceServerName = os.getenv("DEVICE_SERVER_NAME")
    run({deviceServerName: LogixDevice})
