import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import subprocess

GATT_SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
WIFI_CHARACTERISTIC_UUID = '87654321-4321-6789-4321-56789abcdef0'

class WiFiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, service):
        self.path = f'/org/bluez/example/service{index}/char{index}'
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = ['read']
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"WiFiCharacteristic initialized: {self.path}")

    def get_wifi_status(self):
        try:
            result = subprocess.run(['iwgetid'], capture_output=True, text=True)
            if result.returncode != 0:
                return "Not connected"
            ssid = result.stdout.strip().split('"')[1]
            ip_address = subprocess.run(['hostname', '-I'], capture_output=True, text=True).stdout.strip()
            return f"Connected to {ssid}, IP: {ip_address}"
        except Exception as e:
            return f"Error: {str(e)}"

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        if interface != 'org.bluez.GattCharacteristic1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        if prop == 'UUID':
            return self.uuid
        elif prop == 'Value':
            value = self.get_wifi_status()
            return dbus.Array([dbus.Byte(c) for c in value.encode()], signature='y')
        elif prop == 'Flags':
            return self.flags
        else:
            raise dbus.exceptions.DBusException("Invalid property", name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != 'org.bluez.GattCharacteristic1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        return {
            'UUID': self.uuid,
            'Value': dbus.Array([dbus.Byte(c) for c in self.get_wifi_status().encode()], signature='y'),
            'Flags': self.flags,
        }

class Service(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f'/org/bluez/example/service{index}'
        self.bus = bus
        self.uuid = GATT_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        self.type = "gatt"
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_characteristic(WiFiCharacteristic(bus, 0, WIFI_CHARACTERISTIC_UUID, self))
        print(f"Service initialized: {self.path}")

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        if interface != 'org.bluez.GattService1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        if prop == 'UUID':
            return self.uuid
        elif prop == 'Primary':
            return self.primary
        elif prop == 'Characteristics':
            return dbus.Array([char.path for char in self.characteristics], signature='o')
        else:
            raise dbus.exceptions.DBusException("Invalid property", name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != 'org.bluez.GattService1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        return {
            'UUID': self.uuid,
            'Primary': self.primary,
            'Characteristics': dbus.Array([char.path for char in self.characteristics], signature='o')
        }

class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/org/bluez/example'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(Service(bus, 0))
        print("Application initialized")

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        return {}

    @dbus.service.method('org.freedesktop.DBus.ObjectManager', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.path] = service.get_properties()
            for characteristic in service.characteristics:
                response[characteristic.path] = characteristic.get_properties()
        return response

def register_app_cb():
    print("GATT application registered")

def register_app_error_cb(error):
    print(f"Failed to register application: {error}")
    mainloop.quit()

def start_advertising():
    subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'])
    subprocess.run(['sudo', 'hciconfig', 'hci0', 'leadv', '3'])
    subprocess.run(['sudo', 'hciconfig', 'hci0', 'noscan'])
    subprocess.run(['sudo', 'bluetoothctl', 'advertise', 'on'])
    print("Advertising started")

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

adapter_path = '/org/bluez/hci0'
adapter = dbus.Interface(bus.get_object('org.bluez', adapter_path), 'org.freedesktop.DBus.Properties')
adapter.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(1))

service_manager = dbus.Interface(bus.get_object('org.bluez', adapter_path), 'org.bluez.GattManager1')
app = Application(bus)

mainloop = GLib.MainLoop()
service_manager.RegisterApplication(app.path, {},
                                    reply_handler=register_app_cb,
                                    error_handler=register_app_error_cb)

start_advertising()
mainloop.run()
