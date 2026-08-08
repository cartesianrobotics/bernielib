"""
First motion test: home the robot, then move each axis to a known coordinate.

Sequence:
    1. ber.home()                 - the top-level homing call (bernielib.py:1472)
    2. X and Y -> 100 mm          - simultaneously, via moveXY()
    3. Z -> 50 mm
    4. A (plunger) -> 10 mm
    5. magnets engaged -> pause -> disengaged, then the rack servo powered off
    6. A -> 0 mm
    7. dumpTip() - the tip ejector, actuated at the current position
    8. A -> 10 mm again

THIS MOVES THE ROBOT. Watch it. Keep a hand near the power switch.

Run with no tip attached - see the clearance note under TARGET_Z below.

Usage:
    python motion_test.py            # home, then run the moves
    python motion_test.py --dry-run  # connect and report position, move nothing

Part of BernieLib.
"""

import argparse
import re
import sys
import time

import bernielib as bl

TARGET_XY = 100.0
# Z counts DOWNWARD from the homed position: moveDownUntilPress() does `z += step`
# to descend (bernielib.py:1716), so Z=0 is the top and larger Z is lower.
# The deck is calibrated at Z 146.7 (waste) to 152.3 (samples), so Z=50 clears
# the highest feature by ~97 mm with a bare nozzle, and still by ~55 mm with a
# tip attached (added_tip_length is 41.6 in robot.json).
# Was 100, which sat lower than intended in practice.
TARGET_Z = 50.0
TARGET_A = 10.0
# Plunger is sent here before the tip is ejected.
TARGET_A_BEFORE_DROP = 0.0
# Hold the magnets against the tubes this long before retracting them. This is
# on top of the 1.5 s rackMoveMagnetsAngle() already waits for the servo to turn.
MAGNET_HOLD_S = 1.0

# How long to allow for one homing / move before giving up.
SETTLE_TIMEOUT = 120.0


def board_state(ber, timeout=3.0):
    """
    Current Smoothie state ('Idle', 'Run', 'Home', 'Alarm', ...).

    Talks to the port directly rather than through writeAndWaitCartesian(),
    because that call waits for 'ok' with a 5 s timeout (bernielib.py:225) and
    homing takes considerably longer than that - it would return None and let
    us race ahead of the machine. '?' is answered immediately even while the
    board is busy, which is what makes this poll work.
    """
    port = ber.cartesian_port
    port.reset_input_buffer()
    port.write(b'?\r')
    message = ''
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port.inWaiting():
            message += port.read(port.inWaiting()).decode('utf-8', errors='replace')
            found = re.search(r'<([A-Za-z]+)\|', message)
            if found:
                return found.group(1)
        time.sleep(0.02)
    return None


def wait_settled(ber, what, timeout=SETTLE_TIMEOUT, needed=3):
    """
    Block until the board reports Idle several polls running.

    'needed' consecutive Idle readings, because a poll issued in the gap between
    sending a command and the planner picking it up can catch a stale Idle.
    """
    start = time.time()
    idle_streak = 0
    time.sleep(0.3)
    while time.time() - start < timeout:
        state = board_state(ber)
        if state == 'Idle':
            idle_streak += 1
            if idle_streak >= needed:
                print("    settled after %.1f s" % (time.time() - start))
                return True
        else:
            if idle_streak:
                idle_streak = 0
            if state == 'Alarm':
                print("    !! board reports ALARM during %s - stopping" % what)
                return False
        time.sleep(0.2)
    print("    !! %s did not settle within %.0f s (last state: %s)" % (what, timeout, state))
    return False


def report_position(ber, label):
    x, y, z, a = ber.getPosition()
    print("    %s X=%.2f Y=%.2f Z=%.2f A=%.2f" % (label, x, y, z, a))
    return x, y, z, a


def check_targets(ber):
    """Refuse to move outside the envelope recorded in robot.json."""
    limits = [
        ('X', TARGET_XY, ber._getSetting('x_max')),
        ('Y', TARGET_XY, ber._getSetting('y_max')),
        ('Z', TARGET_Z, ber._getSetting('z_max')),
        ('A', TARGET_A, ber.getPlungerMaxCoord()),
    ]
    ok = True
    for axis, target, limit in limits:
        verdict = "ok" if 0 <= target <= limit else "OUT OF RANGE"
        if verdict != "ok":
            ok = False
        print("    %s -> %-6.1f (max %-6.1f) %s" % (axis, target, limit, verdict))
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help="Connect and report state, but do not home or move.")
    args = parser.parse_args()

    print("Connecting (bernielib scans the serial ports; this takes a moment)...")
    ber = bl.robot()
    print("  cartesian: %s" % ber.cartesian_port.port)
    print("  loadcell:  %s" % ber.loadcell_port.port)

    try:
        print("\nTarget coordinates vs. the limits in robot.json:")
        if not check_targets(ber):
            print("\nA target is outside the machine envelope. Not moving.")
            return 1

        print("\nBoard state: %s" % board_state(ber))
        report_position(ber, "position now (meaningless until homed):")

        if args.dry_run:
            print("\n--dry-run: stopping here. Nothing moved.")
            return 0

        print("\n[1/8] Homing - ber.home()")
        print("      (homes Z, then X, then Y, then A, then magnets away, servo up)")
        ber.home()
        if not wait_settled(ber, "homing"):
            return 1
        report_position(ber, "homed:")

        print("\n[2/8] X and Y -> %.0f mm (simultaneously)" % TARGET_XY)
        ber.moveXY(x=TARGET_XY, y=TARGET_XY)
        if not wait_settled(ber, "XY move"):
            return 1
        report_position(ber, "after XY:")

        print("\n[3/8] Z -> %.0f mm (downward; ~97 mm above the deck)" % TARGET_Z)
        ber.moveAxis('Z', TARGET_Z)
        if not wait_settled(ber, "Z move"):
            return 1
        report_position(ber, "after Z:")

        print("\n[4/8] A (plunger) -> %.0f mm" % TARGET_A)
        ber.pipetteMove(TARGET_A)
        if not wait_settled(ber, "A move"):
            return 1
        report_position(ber, "after A:")

        # poweroff=False on both moves so the rack servo stays energised across
        # the hold; it is switched off once at the end, via rackPowerOff().
        print("\n[5/8] Magnets: engage -> hold %.0f s -> disengage -> servo off" % MAGNET_HOLD_S)
        print("      engaged angle %s, disengaged angle %s (robot.json)"
              % (ber.getMagnetsNearTubeAngle(), ber.getMagnetsAwayAngle()))
        print("      engaging (lever towards the tubes)...")
        ber.moveMagnetsTowardsTube(poweroff=False)
        time.sleep(MAGNET_HOLD_S)
        print("      disengaging (lever away from the tubes)...")
        ber.moveMagnetsAway(poweroff=False)
        ber.rackPowerOff()
        print("      rack servo powered off.")

        print("\n[6/8] A (plunger) -> %.0f mm, ready to eject" % TARGET_A_BEFORE_DROP)
        ber.pipetteMove(TARGET_A_BEFORE_DROP)
        if not wait_settled(ber, "A move to 0"):
            return 1
        report_position(ber, "before tip drop:")

        print("\n[7/8] Ejecting the tip - ber.dumpTip(), at the current position")
        print("      (drives the plunger to %s to push the ejector, then back)"
              % ber._getDumpTipPlungerMovement())
        ber.dumpTip()
        if not wait_settled(ber, "tip drop"):
            return 1
        report_position(ber, "after tip drop:")

        print("\n[8/8] A (plunger) -> %.0f mm" % TARGET_A)
        ber.pipetteMove(TARGET_A)
        if not wait_settled(ber, "A move back"):
            return 1
        x, y, z, a = report_position(ber, "final:")

        print("\n--- Result ---")
        expected = [('X', x, TARGET_XY), ('Y', y, TARGET_XY),
                    ('Z', z, TARGET_Z), ('A', a, TARGET_A)]
        all_good = True
        for axis, actual, target in expected:
            hit = abs(actual - target) < 0.5
            all_good = all_good and hit
            print("  %s: asked %.1f, reads %.2f  %s" % (axis, target, actual, "ok" if hit else "MISMATCH"))
        print("\nThe robot is left at X=%.1f Y=%.1f Z=%.1f with the plunger at %.1f." % (x, y, z, a))
        print("Re-home before running a protocol." if all_good else "Check the mismatch before going further.")
        return 0 if all_good else 1
    finally:
        ber.close()
        print("Ports closed.")


if __name__ == '__main__':
    sys.exit(main())
