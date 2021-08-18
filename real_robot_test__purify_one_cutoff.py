# This will do a high-level test of the purify_one_cutoff.py script
import sys
import time

import purify_one_cutoff as ponec

def test__Homing():
    ber = ponec.bl.robot()
    ber.home()
    ber.close()
    print("Robot should have moved to the home.")
    val = input("Did it happened? Enter y if yes, anything else if no: ")
    if val == 'y':
        print("Homing success.")
    else:
        print("Homing failed.")
        sys.exit("Test failed. Terminating.")


def test__mixManySamples():
    print("Testing mixManySamples function.")
    # Preparing for the test
    settings = ponec.loadSettings('samplesheet.csv')
    ber = ponec.bl.robot()
    samples_list = ponec.initSamples(ber, settings)
    for sample in samples_list:   # For the test, sample starts with zero volume
        sample.setVolume(0)
    beads, waste, water, EtOH80pct = ponec.initReagents(ber, settings)
    # Adding the liquid
    ber.pickUpNextTip()
    ber.move(z=50)
    for sample in samples_list:
        ber.transferLiquid(water, sample, 100)
    ber.move(z=50)
    ber.dumpTipToWaste()
    ber.move(z=50)
    
    timestamp = time.time()
    
    # Performing an actual test
    ponec.mixManySamples(ber, samples_list, timestamp, settings)
    
    # Cleaning update
    ber.pickUpNextTip()
    ber.move(z=50)
    for sample in samples_list:
        ber.transferLiquid(sample, waste, 100, dry_tube=True)
    ber.move(z=50)
    ber.dumpTipToWaste()
    ber.move(z=50)
    ber.close()
    
    print("Test finished.")
    print("Robot should have attempted to wait for some time, mix samples, then wait again.")
    val = input("Did it happened? Enter y if yes, anything else if no: ")
    if val == 'y':
        print("mixManySamples success.")
    else:
        print("mixManySamples failed.")
        sys.exit("Test failed. Terminating.")
    

if __name__ == '__main__':
    #test__Homing()
    test__mixManySamples()