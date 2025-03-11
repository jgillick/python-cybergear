import traceback
from typing import Literal

EventNames = Literal[
    "state_changed",
    "config_received",
    "param_received",
    "has_fault",
    "fault_cleared",
    "warn",
]


class EventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event: EventNames, listener):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)
        return listener

    def emit(self, event: EventNames, *args, **kwargs):
        if event in self._listeners:
            for listener in self._listeners[event]:
                try:
                    listener(*args, **kwargs)
                except:
                    traceback.print_exc()

    def remove_listener(self, event: EventNames, listener):
        if event in self._listeners:
            self._listeners[event].remove(listener)
            if not self._listeners[event]:
                del self._listeners[event]
