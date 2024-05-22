import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

GATT_SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
GATT_CHARACTERISTIC_UUID = '12345678-1234-5678-1234-56789abcdef1'
TEXT_TO_SHARE = "Hello from Raspberry Pi"

class TextCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags):
        self.path = f'/org/bluez/example/service{index}/char{index}'
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ssv', out_signature='')
    def Set(self, interface, prop, value):
        pass

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        if interface != 'org.bluez.GattCharacteristic1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        if prop == 'UUID':
            return self.uuid
        elif prop == 'Value':
            return [dbus.Byte(ord(c)) for c in TEXT_TO_SHARE]
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
            'Value': [dbus.Byte(ord(c)) for c in TEXT_TO_SHARE],
            'Flags': self.flags,
        }

class TextService(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f'/org/bluez/example/service{index}'
        self.bus = bus
        self.index = index
        self.uuid = GATT_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_characteristic(TextCharacteristic(bus, 0, GATT_CHARACTERISTIC_UUID, ['read']))

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
        self.add_service(TextService(bus, 0))

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        return {}

    @dbus.service.method('org.freedesktop.DBus.ObjectManager', in_signature='', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            service_path = service.path
            response[service_path] = service.GetAll('org.bluez.GattService1')
            for characteristic in service.characteristics:
                char_path = characteristic.path
                response[char_path] = characteristic.GetAll('org.bluez.GattCharacteristic1')
        return response

def register_app_cb():
    print("GATT application registered")

def register_app_error_cb(error):
    print(f"Failed to register application: {error}")
    mainloop.quit()

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

mainloop.run()
