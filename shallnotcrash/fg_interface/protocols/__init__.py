"""
Protocol implementations for FlightGear communication

Currently supported:
- Telnet (default)
"""

from .telnet import TelnetProtocol

__all__ = ['TelnetProtocol']