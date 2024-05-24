import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")

# Custom service UUID
SERVICE_UUID = "12345678-1234-5678-1234-567812345678"

# Characteristic to hold the "hello" message
CHARACTERISTIC_UUID = "9ABCDEF0-1234-5678-1234-567812345678"
HELLO_MESSAGE = "hello"

def register_service():
    adapter_path = list(manager.GetManagedObjects().keys())[0]

    # Register the custom service
    service_props = {
        "Type": dbus.String("gatt"),  # This line is crucial!
        "UUID": dbus.String(SERVICE_UUID),
        "Primary": dbus.Boolean(True)
    }
    service_path = bus.get_object("org.bluez", adapter_path).AddService(service_props)  # Change here
    
    # Register the characteristic
    char_props = {
        "UUID": dbus.String(CHARACTERISTIC_UUID),
        "Service": dbus.ObjectPath(service_path),
        "Value": dbus.Array([dbus.Byte(ord(c)) for c in HELLO_MESSAGE], signature=dbus.Signature('y')),
        "Flags": dbus.Array(["read"], signature=dbus.Signature('s'))
    }
    bus.get_object("org.bluez", service_path).AddCharacteristic(char_props)  # Change here

def start_advertising():
    adapter = dbus.Interface(bus.get_object("org.bluez", adapter_path), "org.bluez.Adapter1")
    adapter.StartDiscovery()
    adapter.SetProperty("Discoverable", dbus.Boolean(True))

register_service()
start_advertising()

GLib.MainLoop().run()
