"""
Read-only "are the boards alive?" check for both of Bernie's controllers:
the Smoothieboard (cartesian) and the load cell Arduino.

Sends only query commands - nothing that moves a motor, turns a servo, or
powers anything up. Safe to run with the robot on the bench.
(The one exception is --tare, which is opt-in; see below.)

Usage:
    python hello_robot.py                    # find both boards, query both
    python hello_robot.py --list             # list serial ports and exit
    python hello_robot.py --port COM3        # Smoothieboard is here, skip detection
    python hello_robot.py --loadcell-port COM4
    python hello_robot.py --tare             # also zero the load cells (changes state)

Deliberately depends on pyserial only (no bernielib import), so it still runs
if pandas/scipy or the settings JSONs are broken. The constants below mirror
bernielib.py; keep them in sync.

Part of BernieLib.
"""

import argparse
import re
import sys
import time

import serial

# Mirrors bernielib.py: BAUDRATE, TIMEOUT, and the welcome messages.
BAUDRATE = 115200
TIMEOUT = 5  # seconds
SMOOTHIE_STATUS_REPLY = "Build version: "
LOADCELL_WELCOME = "Bernie's load cells controller"
LOADCELL_WELCOME_ALT1 = "Arnie's mobile gripper tool"

# The two boards are addressed differently, and this script keeps the
# difference so a mismatch shows up here rather than mid-protocol:
#   bernielib._getRobotIdMessage()  identifies boards with eol='\n'
#   bernielib.writeAndWaitCartesian() talks to the Smoothieboard with eol='\r'
#   bernielib.writeLoadCell()       talks to the Arduino with NO terminator.
# The Arduino reads with Serial.readBytes() on a 20 ms timeout
# (firmware_arduino/bernie.ino:28), which is why it needs no line ending.
EOL_DETECT = "\n"
EOL_CARTESIAN = "\r"
EOL_LOADCELL = ""

# Read-only. (command, what it should tell us)
SMOOTHIE_PROBES = [
    ("version", "firmware build version, build date, MCU"),
    ("M115", "firmware name / capabilities"),
    ("?", "status + machine position (this is what getPosition() parses)"),
    ("M114", "current position"),
    ("M119", "endstop states"),
]

# Read-only. 'G?' only prints the stored servo angle, it does not move anything.
# Left out on purpose: 'G0 <angle>' (moves servo), 'P on'/'P off' (servo power),
# 'T' (tares - see --tare).
LOADCELL_PROBES = [
    ("version", "board name"),
    ("G?", "last servo angle the board was told (does not move it)"),
    ("RL", "left load cell reading"),
    ("RR", "right load cell reading"),
]


def list_ports():
    """All serial ports the OS reports. Falls back to brute force on Windows."""
    try:
        from serial.tools import list_ports as _lp
        found = [(p.device, p.description) for p in _lp.comports()]
        if found:
            return found
    except ImportError:
        pass
    # Fallback: same brute-force scan bernielib._mapPorts() does.
    if not sys.platform.startswith('win'):
        return []
    found = []
    for name in ['COM%s' % (i + 1) for i in range(256)]:
        try:
            s = serial.Serial(name)
            s.close()
            found.append((name, '?'))
        except (OSError, serial.SerialException):
            pass
    return found


def write(port, expression, eol):
    """Same shape as bernielib._write()."""
    port.reset_output_buffer()
    port.reset_input_buffer()
    port.write((expression.strip() + eol).encode())


def read_reply(port, overall_timeout=2.0, quiet_time=0.3):
    """
    Read everything the board sends, then stop once it has been quiet for
    quiet_time. Unlike bernielib._readUntilMatch() this waits for no particular
    pattern, so it also captures replies we did not anticipate.
    """
    deadline = time.time() + overall_timeout
    chunks = []
    last_data = time.time()
    while time.time() < deadline:
        waiting = port.in_waiting
        if waiting:
            chunks.append(port.read(waiting).decode('utf-8', errors='replace'))
            last_data = time.time()
            continue
        if chunks and (time.time() - last_data) > quiet_time:
            break
        time.sleep(0.02)
    return ''.join(chunks)


def identify(port_name, attempts=2):
    """Open a port, ask 'version', return (raw_reply, 'cartesian'/'loadcell'/None)."""
    try:
        port = serial.Serial(port_name, BAUDRATE, timeout=TIMEOUT)
    except (OSError, serial.SerialException) as e:
        return ("<could not open: %s>" % e, None)
    try:
        # Opening the port resets the load cell Arduino (DTR); it needs a
        # couple of seconds to boot before it can answer. The Smoothieboard
        # does not reset, so the wait costs us nothing there.
        time.sleep(2)
        reply = ''
        for _ in range(attempts):
            write(port, 'version', EOL_DETECT)
            reply = read_reply(port)
            if reply.strip():
                break
    finally:
        port.close()

    board = None
    if SMOOTHIE_STATUS_REPLY in reply:
        board = 'cartesian'
    elif LOADCELL_WELCOME in reply or LOADCELL_WELCOME_ALT1 in reply:
        board = 'loadcell'
    return (reply, board)


def check_position_parsing(status_reply):
    """
    Run bernielib.getPosition()'s parsing over the '?' reply, so we learn now
    whether that function will work with this firmware.
    """
    try:
        msg = re.split(pattern=r'\|', string=status_reply)[1]
        msg = re.split(pattern=r':', string=msg)[-1]
        coords = [float(v) for v in re.split(pattern=',', string=msg)[:4]]
        return "X=%s Y=%s Z=%s A=%s" % tuple(coords)
    except (IndexError, ValueError) as e:
        return "PARSE FAILED (%s: %s)" % (type(e).__name__, e)


def check_load_parsing(reply):
    """
    bernielib.readRightLoad() does float(reply.strip()) and blows up with
    ValueError on anything else. Check that here instead.
    """
    try:
        return "%s" % float(reply.strip())
    except (ValueError, AttributeError) as e:
        return "PARSE FAILED (%s: %s)" % (type(e).__name__, e)


def show(text):
    """Print a board reply with the control characters made visible."""
    if not text:
        return "    <nothing - no reply>"
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return '\n'.join("    | " + ln for ln in lines if ln.strip())


def run_probes(port_name, probes, eol, label):
    """Send each read-only command, print what came back, return {cmd: reply}."""
    print("\n--- %s on %s (read-only commands) ---" % (label, port_name))
    try:
        port = serial.Serial(port_name, BAUDRATE, timeout=TIMEOUT)
    except (OSError, serial.SerialException) as e:
        print("Could not open %s: %s" % (port_name, e))
        return None

    replies = {}
    try:
        time.sleep(2)  # let the Arduino finish rebooting after the port opened
        port.reset_input_buffer()
        for cmd, meaning in probes:
            print("\n>>> %s   (%s)" % (cmd, meaning))
            write(port, cmd, eol)
            replies[cmd] = read_reply(port)
            print(show(replies[cmd]))
    finally:
        port.close()
    return replies


def read_load_repeatedly(port_name, times=3, delay=0.5):
    """
    Read both load cells a few times. A live HX711 wanders by a count or two;
    an identical value every time (or no value) means the sensor is not talking.
    """
    print("\n--- Load cells, %d readings each ---" % times)
    try:
        port = serial.Serial(port_name, BAUDRATE, timeout=TIMEOUT)
    except (OSError, serial.SerialException) as e:
        print("Could not open %s: %s" % (port_name, e))
        return
    try:
        time.sleep(2)
        port.reset_input_buffer()
        for cmd, side in (('RL', 'left'), ('RR', 'right')):
            values = []
            for _ in range(times):
                write(port, cmd, EOL_LOADCELL)
                values.append(check_load_parsing(read_reply(port)))
                time.sleep(delay)
            print("  %-5s (%s): %s" % (cmd, side, ", ".join(values)))
    finally:
        port.close()


def tare(port_name):
    """The one state-changing command in this script: zero both load cells."""
    print("\n--- Taring both load cells ('T') ---")
    try:
        port = serial.Serial(port_name, BAUDRATE, timeout=TIMEOUT)
    except (OSError, serial.SerialException) as e:
        print("Could not open %s: %s" % (port_name, e))
        return
    try:
        time.sleep(2)
        port.reset_input_buffer()
        write(port, 'T', EOL_LOADCELL)
        print(show(read_reply(port)))
    finally:
        port.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help="Smoothieboard port, e.g. COM3. Default: auto-detect.")
    parser.add_argument('--loadcell-port', help="Load cell Arduino port. Default: auto-detect.")
    parser.add_argument('--list', action='store_true', help="List serial ports and exit.")
    parser.add_argument('--tare', action='store_true',
                        help="Also tare the load cells. This CHANGES state; everything else is read-only.")
    args = parser.parse_args()

    ports = list_ports()
    print("Serial ports found: %s" % (", ".join(n for n, _ in ports) or "(none)"))
    for name, desc in ports:
        print("    %-8s %s" % (name, desc))
    if args.list:
        return 0
    if not ports and not (args.port or args.loadcell_port):
        print("\nNo serial ports. Is the robot plugged in and powered?")
        return 1

    smoothie_port = args.port
    loadcell_port = args.loadcell_port
    if smoothie_port is None or loadcell_port is None:
        print("\n--- Asking every port to identify itself ---")
        for name, _ in ports:
            if name in (smoothie_port, loadcell_port):
                continue
            reply, board = identify(name)
            print("\n%s says:" % name)
            print(show(reply))
            if board == 'cartesian':
                print("  -> Smoothieboard (cartesian).")
                smoothie_port = smoothie_port or name
            elif board == 'loadcell':
                print("  -> load cell Arduino.")
                loadcell_port = loadcell_port or name
            else:
                print("  -> unrecognized; not one of Bernie's boards.")

    status_reply = ''
    if smoothie_port:
        replies = run_probes(smoothie_port, SMOOTHIE_PROBES, EOL_CARTESIAN, "Smoothieboard")
        status_reply = (replies or {}).get('?', '')

    if loadcell_port:
        run_probes(loadcell_port, LOADCELL_PROBES, EOL_LOADCELL, "Load cell Arduino")
        read_load_repeatedly(loadcell_port)
        if args.tare:
            tare(loadcell_port)

    print("\n--- Summary ---")
    print("Smoothieboard:     %s" % (smoothie_port or "NOT FOUND"))
    print("Load cell Arduino: %s" % (loadcell_port or "NOT FOUND"))
    if smoothie_port:
        print("getPosition() parsing of '?': %s" %
              (check_position_parsing(status_reply) if status_reply else "no '?' reply to parse."))
    if args.tare:
        print("Load cells were tared.")
    print("Nothing was moved.")
    return 0 if (smoothie_port and loadcell_port) else 1


if __name__ == '__main__':
    sys.exit(main())
