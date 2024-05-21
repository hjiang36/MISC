#!/usr/bin/python3
import dbus
import dbus.mainloop.glib
import dbus.service
import logging
import os
from gi.repository import GLib

logging.basicConfig(level=logging.INFO)

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = '/test/agent'
CAPABILITY = 'NoInputNoOutput'

class Agent(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        logging.info("Release")
        mainloop.quit()

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        logging.info(f"AuthorizeService {device} {uuid}")
        return

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        logging.info(f"RequestPinCode {device}")
        return "0000"

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        logging.info(f"RequestPasskey {device}")
        return dbus.UInt32(0)

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        logging.info(f"DisplayPasskey {device} {passkey:06d} entered {entered}")

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        logging.info(f"RequestConfirmation {device} {passkey:06d}")
        return

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        logging.info(f"RequestAuthorization {device}")
        return

    @dbus.service.method(dbus_interface=AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        logging.info("Cancel")

def register_agent():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    agent = Agent(bus, AGENT_PATH)

    obj = bus.get_object(BUS_NAME, "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(AGENT_PATH, CAPABILITY)
    manager.RequestDefaultAgent(AGENT_PATH)

    logging.info("Agent registered")

def connection_handler(interface, changed, invalidated, path):
    if 'Connected' in changed:
        if changed['Connected']:
            logging.info("Device connected, stopping discoverable mode")
            os.system("btmgmt -i hci0 discoverable no")
        else:
            logging.info("Device disconnected, starting discoverable mode")
            os.system("btmgmt -i hci0 discoverable yes")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    bus.add_signal_receiver(connection_handler,
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="PropertiesChanged",
                            path_keyword="path")

    register_agent()
    mainloop = GLib.MainLoop()
    mainloop.run()
