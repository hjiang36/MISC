import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

GATT_SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'

class Service(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f'/org/bluez/example/service{index}'
        self.bus = bus
        self.uuid = GATT_SERVICE_UUID
        self.primary = True
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"Service initialized: {self.path}")

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        print(f"Get called: {interface}, {prop}")
        if interface != 'org.bluez.GattService1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        if prop == 'UUID':
            return self.uuid
        elif prop == 'Primary':
            return self.primary
        else:
            raise dbus.exceptions.DBusException("Invalid property", name='org.freedesktop.DBus.Error.InvalidArgs')

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        print(f"GetAll called: {interface}")
        if interface != 'org.bluez.GattService1':
            raise dbus.exceptions.DBusException("Invalid interface", name='org.freedesktop.DBus.Error.InvalidArgs')

        return {
            'UUID': self.uuid,
            'Primary': self.primary,
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

    @dbus.service.method('org.freedesktop.DBus.ObjectManager', in_signature='', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            service_path = service.path
            response[service_path] = {
                'org.bluez.GattService1': service.GetAll('org.bluez.GattService1')
            }
        print(f"GetManagedObjects response: {response}")
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
