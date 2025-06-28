"""
fg_interface - FlightGear communication interface for ShallNotCrash

Exposes the main FGConnection class and common exceptions.
"""

from .core import FGConnection
from .exceptions import FGCommError, ConnectionTimeout, ProtocolError

__all__ = ['FGConnection', 'FGCommError', 'ConnectionTimeout', 'ProtocolError']