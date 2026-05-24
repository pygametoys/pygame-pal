from __future__ import annotations

import threading

from mido import ports
from supriya_midi import MidiOut, get_api_name, get_compiled_api, get_compiled_api_by_name


def _get_default_api():
    compiled = get_compiled_api()
    if not compiled:
        return None
    return compiled[0]


def _resolve_api(name: str | None):
    if name is None:
        return _get_default_api()
    return get_compiled_api_by_name(name.lower())


def _create_midi_out(api: str | None) -> MidiOut:
    if api is None:
        return MidiOut()
    return MidiOut(api=api)


def get_devices(api: str | None = None, **kwargs):
    midi_out = _create_midi_out(_resolve_api(api))
    output_names = midi_out.get_ports()
    midi_out.delete()
    return [
        {
            "name": name,
            "is_input": False,
            "is_output": True,
        }
        for name in output_names
    ]


class PortCommon:
    def _close(self):
        self._rt.close_port()
        self._rt.delete()


class Input(ports.BaseInput):
    def _open(self, **kwargs):
        raise OSError("supriya backend does not implement MIDI input")


class Output(PortCommon, ports.BaseOutput):
    _locking = False

    def _open(
        self,
        client_name=None,
        virtual: bool = False,
        api: str | None = None,
        callback=None,
        **kwargs,
    ):
        self.closed = True
        self._send_lock = threading.RLock()
        resolved_api = _resolve_api(api)
        self._rt = _create_midi_out(resolved_api)
        self.api = get_api_name(resolved_api).upper() if resolved_api is not None else "UNSPECIFIED"
        self._device_type = f"Supriya/{self.api}"

        if client_name is not None:
            virtual = True
            self._rt.set_client_name(client_name)

        if virtual:
            if self.name is None:
                raise OSError("virtual port must have a name")
            self._rt.open_virtual_port(self.name)
            return

        port_names = self._rt.get_ports()
        if not port_names:
            raise OSError("no ports available")

        if self.name is None:
            self.name = port_names[0]
            port_id = 0
        elif self.name in port_names:
            port_id = port_names.index(self.name)
        else:
            raise OSError(f"unknown port {self.name!r}")

        self._rt.open_port(port_id)

    def send(self, msg):
        with self._send_lock:
            self._rt.send_message(msg.bytes())

    send.__doc__ = ports.BaseOutput.send.__doc__
