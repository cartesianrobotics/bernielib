import bernielib as bl
import os
import threading
import sys

from PIL import Image

if __name__ == '__main__':
    print("This is the script for calibrating Bernie's working area.")
    print("Please make sure to remove any tubes from Bernie.")
    input("Press Enter when done...")
    print("Now make sure the waste bin is placed into the working area.")
    input("Press Enter when done...")
    print("Place tip rack in 'old' format into the working area.")
    print("Make sure the lid is off. Tips may or may not be present.")
    input("Press Enter when done...")
    
    
    print("Please check again: No tubes in the working area; old-style tip rack and waste bin are present.")
    print("The picture should open now; this is how the working area should look like.")
    img = Image.open('bernie_workarea_ready_for_calibration.png')
    img__ready_to_calibrate__thread = threading.Thread(target=img.show, args=(), daemon=True)
    img__ready_to_calibrate__thread.start()
    input("Press Enter when done. The robot will start calibrating...")
    
    print("Starting to calibrate now.")
    print("Homing the robot. Please wait...")
    ber = bl.robot()
    ber.home()
    print("The pipette should now be in the top right corner. The working area should be on the back. ")
    homing_success = input("Press y and enter if this happened: ")
    if homing_success != 'y':
        sys.exit("Homing failed according to the user. Start troubleshooting.")
    
    print("Now calibrating the samples rack. Please wait...")
    ber.calibrateRack(rack='samples')
    print("Sample rack calibration finished.")
    print("Now calibrating the reagents rack. Please wait...")
    ber.calibrateRack(rack='reagents')
    print("Reagents rack calibration finished.")
    print("Now calibrating the waste bin. Please wait...")
    ber.calibrateRack(rack='waste')
    print("Waste bin calibration finished.")
    print("Now calibrating the 'old'-style tips rack. Please wait...")
    ber.calibrateRack(rack='tips')
    print("Old-style tips rack calibration finished.")
    
    mt_rack = input("If you like to calibrate a Mettler Toledo tips rack, please press y: ")
    if mt_rack == 'y':
        ber.move(z=5)
        ber.move(y=250)
        input("Remove the tips rack from the working area. Press Enter when done...")
        input("Remove the cover from Mettler Toledo tip rack completely. Press Enter when done...")
        input("Place the Mettler Toledo rack into the adapter. Press Enter when done...")
        print("Place the adapter with the rack into the working area.")
        print("Hinges from the cover must face to your left.")
        input("Press Enter when done... Robot will start moving.")
        print("Now calibrating the Mettler Toledo tips rack. Please wait...")
        ber.close()
        del ber
        ber = bl.robot(tips_type='new')
        ber.home()
        ber.calibrateRack(rack='tips')
        print("Mettler Toledo tips rack calibration finished.")
        
    print("Finalizing. Please wait...")
    ber.home()
    
    ber.powerStepperOff('A') # to prevent unnecessary heating. Must be off already, but just in case.
    ber.powerStepperOff()    # Powering off all steppers
    
    ber.close()
    del ber
    
    print("Calibration complete. The robot is ready to use now.")
        
    