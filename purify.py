# Final script that performs magnetic beads purification on one side

import sys
import os
import csv
import time
from datetime import datetime

# loacl libraries
import bernielib as bl

# TODO: A There is some problem when robot does not hit the tip. It does not perform search around.
# TODO: AAA Robot touches waste side, then moves again to the sample. Make that stop.

# Functions for sanity checks
# ============================================================================================

def isArgumentPassed():
    """
    Checks whether an argument was passed to the function
    """
    n = len(sys.argv)  # Number of arguments
    if n > 1:
        return True
    else:
        return False

def isSampleSheetExist(samplesheet_path):
    """
    Checkis whether the provided samplesheet exists.
    """
    return os.path.exists(samplesheet_path)

def printHowToUse():
    print("This is the script for purifying DNA mixture by removing any DNA molecules")
    print("shorter then a certain size.")
    print("")
    print("Usage:")
    print("python purify_one_cutoff.py samplesheet.csv")
    print("Here, samplesheet.csv is the file with the purification settings.")
    print("Please see the instructions on how to modify your samplesheet.csv")
    # TODO: Insert link with the instructions on how to use samplesheet.csv
    print("TODO: Here, place the link with the instructions")

def areTwoPortsAvailable():
    port_list = bl.listSerialPorts()
    if len(port_list) >= 2:
        return True
    else:
        print ("CRITICAL ERROR: can not locate Bernie robot ports.")
        print ("Bernie robot appears as two COM ports when connected.")
        print("For example, COM3 and COM4.")
        print("However, there were only "+str(len(port_list))+" ports found.")
        print(port_list)
        print("")
        print("Make sure there is no other program keeping those ports open,")
        print("such as a Jupyter notebook instance, or an Arduino IDE port scanner.")
        print("Close any program that may be using those ports, then try again.")
        print("")
        print("Try unplugging and turning off the robot (both power and USB), ")
        print("then turn it back on and plug in USB, then run the script again.")
        print("If this does not help, make sure the USB cable is not damaged.")
        print("If this is the first time you are trying to run this script, ")
        print("make sure the Arduino drivers are installed.")
        print("If nothing helps, please refer to the troubleshooting manual")
        # TODO: insert link for the troubleshooting instructions for when USB ports are not recognized.
        return False

# Functions for loading and handling the purification settings
# ===========================================================================================

def loadSettings(filepath):
    try:
        with open(filepath, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            content = list(csv_reader)
        return content
    except:
        print("Can't import the samplesheet file. Please check the file format, it must be .csv")
        sys.exit("Script terminated")
        
def getRowWithParameter(content, desired_parameter):
    for row in content:
        current_parameter = row['Parameters']
        if current_parameter == desired_parameter:
            return row

def positionsToPurify(content):
    positions_list = []
    row = getRowWithParameter(content, 'Initial sample volume')
    for position in range(12):
        if float(row[str(position)]) > 0:
            positions_list.append(position)
    return positions_list

def positionsToPurify2ndStage(content):
    sample_positions_list = positionsToPurify(content)
    pos_2nd_stage_list = []
    for position in sample_positions_list:
        pos_2nd_stage = position + 6
        pos_2nd_stage_list.append(pos_2nd_stage)
    return pos_2nd_stage_list

def returnSampleParameter(settings, param, position):
    try:
        row = getRowWithParameter(settings, param)
    except:
        print("A critical parameter "+param+" is not in the sample sheet.")
        print("Please check your sample sheet for correctness, and then try again.")
        sys.exit("Script terminated.")
    try:
        value = row[str(position)]
    except:
        print("A position number "+str(position)+" in the parameter "+param+" is not in the sample sheet.")
        print("Please check your sample sheet for correctness, and then try again.")
        sys.exit("Script terminated.")
    try:
        value = float(value)
    except:
        pass
    return value    

def returnProtocolParameter(settings, param):
    return returnSampleParameter(settings, param, '0')


# Protocol-wide settings
# ===========================================================================================

def returnTipRackType(settings):
    """
    Returns the tip rack type. Used to properly initialize the robot.
    """
    return returnProtocolParameter(settings, 'Tip Rack Type')
    
def returnLoadCellPort(settings):
    """
    Returns the port name for the load cell controller (Arduino metro mini)
    """
    value = returnProtocolParameter(settings, 'Load cells controller port')
    if value == 'auto':
        return None
    else:
        return value

def returnCartesianPort(settings):
    """
    Returns the port name for the cartesian controller (smoothieboard)
    """
    value = returnProtocolParameter(settings, 'Cartesian controller port')
    if value == 'auto':
        return None
    else:
        return value

def decideCutoffNumber(settings):
    return returnProtocolParameter(settings, 'Number of cutoffs')


def returnPipettingDelay(settings):
    return returnProtocolParameter(settings, 'Delay after pipetting')

def returnMaxPipetteSpeed(settings):
    return returnProtocolParameter(settings, 'Maximum pipetting speed')
    
def returnBeadsPipettingSpeed(settings):
    return returnProtocolParameter(settings, 'Beads pipetting speed')
    
def returnEthanolPipettingSpeed(settings):
    return returnProtocolParameter(settings, 'Ethanol pipetting speed')
    
def returnEluentPipettingSpeed(settings):
    return returnProtocolParameter(settings, 'Eluent pipetting speed')


# Functions samples and tubes initialization
# ===========================================================================================

def initSamples(robot, settings):
    initial_vol_list = []
    # Getting list of positions at which samples are placed
    samples_positions_list = positionsToPurify(settings)
    # Obtaining initial sample volume from settings
    for position in samples_positions_list:
        volume = returnSampleParameter(settings, 'Initial sample volume', position)
        initial_vol_list.append(volume)
    # Initializing sample instances
    samples_list = bl.createSamplesToPurifyList(robot, initial_vol_list)
    return samples_list

def initIntermediate(robot, settings):
    samples_positions_list = positionsToPurify(settings)
    number_of_samples = len(samples_positions_list)
    
    # Initializing sample instances
    intermediate_list = bl.createSamplesToPurifyList(robot, number_of_tubes=number_of_samples, 
                                                     start_from_position=6)
    return intermediate_list                                                 
    

def initResultTubes(robot, settings):
    # Getting list of positions at which samples are placed
    samples_positions_list = positionsToPurify(settings)
    N_samples = len(samples_positions_list) # Number of samples
    # Initializing results tube instances
    result_list = bl.createPurifiedSamplesList(robot, N_samples)
    return result_list

def initReagents(robot, settings):
    """
    Return 4 instances of the reagent tubes: 
    for beads, waste, eluent, ethanol 80%; in this particular order.
    The parameters for the tubes (such as volume and location) are also defined according to the sample sheet.
    """
    
    # Beads tube settings
    beads_tube_type = returnProtocolParameter(settings, 'Beads tube type')
    beads_rack_name = returnProtocolParameter(settings, 'Beads tube rack')
    if beads_rack_name == 'samples':
        beads_rack = robot.samples_rack
    elif beads_rack_name == 'reagents':
        beads_rack = robot.reagents_rack
    else:
        print ("wrong Beads tube rack specified in the samplesheet file")
        return
    beads_col = int(returnProtocolParameter(settings, 'Beads tube column'))
    beads_row = int(returnProtocolParameter(settings, 'Beads tube well'))
    V_avail_beads = returnProtocolParameter(settings, 'Beads initial volume')
    
    # Initializing beads tube
    beads_tube = bl.createSample(beads_tube_type, 'beads', beads_rack, beads_col, beads_row, V_avail_beads)

    
    # -------------------
    # Waste tube settings
    waste_tube_type = returnProtocolParameter(settings, 'Waste tube type')
    waste_rack_name = returnProtocolParameter(settings, 'Waste tube rack')
    if waste_rack_name == 'reagents':
        waste_rack = robot.reagents_rack
    else:
        print ("wrong Waste tube rack specified in the samplesheet file")
        return
    waste_col = 0
    waste_row = int(returnProtocolParameter(settings, 'Waste tube position'))
    V_waste = returnProtocolParameter(settings, 'Waste volume')
    
    # Initializing waste tube
    waste_tube = bl.createSample(waste_tube_type, 'liquid_waste', waste_rack, waste_col, waste_row, V_waste)

    
    # -------------------
    # Eluent tube settings
    eluent_tube_type = returnProtocolParameter(settings, 'Eluent tube type')
    eluent_rack_name = returnProtocolParameter(settings, 'Eluent tube rack')
    if eluent_rack_name == 'reagents':
        eluent_rack = robot.reagents_rack
    else:
        print ("wrong Eluent tube rack specified in the samplesheet file")
        return
    eluent_col = 0
    eluent_row = int(returnProtocolParameter(settings, 'Eluent tube position'))
    V_avail_eluent = returnProtocolParameter(settings, 'Eluent volume')
    
    # Initializing eluent tube
    eluent_tube = bl.createSample(eluent_tube_type, 'eluent', eluent_rack, eluent_col, eluent_row, V_avail_eluent)

    
    # -------------------
    # Ethanol tube settings
    ethanol_tube_type = returnProtocolParameter(settings, 'Ethanol tube type')
    ethanol_rack_name = returnProtocolParameter(settings, 'Ethanol tube rack')
    if ethanol_rack_name == 'reagents':
        ethanol_rack = robot.reagents_rack
    else:
        print ("wrong Ethanol tube rack specified in the samplesheet file")
        return
    ethanol_col = 0
    ethanol_row = int(returnProtocolParameter(settings, 'Ethanol tube position'))
    V_avail_ethanol = returnProtocolParameter(settings, 'Ethanol volume')    
    
    ethanol80_tube = bl.createSample(ethanol_tube_type, 'EtOH80pct', ethanol_rack, ethanol_col, ethanol_row, V_avail_ethanol)
    
    return beads_tube, waste_tube, eluent_tube, ethanol80_tube




# Beads volume calculations
# ===========================================================================================

def getBeadsVolume(robot, settings, position,
                   beads_vol_param_name='Beads volume',
                   beads_frac_param_name='Fraction',
                   dna_size_cutoff_param_name='DNA size cutoff',
                   initial_sample_vol_param_name='Initial sample volume',
                   ):
    # Importing all possible parameters
    beads_volume = returnSampleParameter(settings, beads_vol_param_name, position)
    beads_volume_fraction = returnSampleParameter(settings, beads_frac_param_name, position)
    dna_size_cutoff = returnSampleParameter(settings, dna_size_cutoff_param_name, position)
    init_sample_vol = returnSampleParameter(settings, initial_sample_vol_param_name, position)
    
    # Deciding which one to use
    if beads_volume > 0:
        use_beads_volume = beads_volume
    elif beads_volume <= 0 and beads_volume_fraction > 0:
        # If the beads volumes are not explicitly provided, use the volume multiplier (fraction)
        use_beads_volume = init_sample_vol * beads_volume_fraction
    elif beads_volume <= 0 and beads_volume_fraction <= 0 and dna_size_cutoff > 0:
        # Approximation using the beads manufacturer data
        # Using if neither beads volume, nor beads volume multiplier are explicitly provided.
        # Getting polynome coefficients
        a, b, c = robot.getBeadsVolumeCoef()
        # Calculating volume multiplier (fraction)
        multiplier = a + b / dna_size_cutoff + c / dna_size_cutoff ** 2
        use_beads_volume = init_sample_vol * multiplier
    else:
        print("No beads volume provided")
        use_beads_volume = 0
    return use_beads_volume    

def getBeadsVolumesForAllSamples(robot, settings, positions_list):
    beads_vol_list = []
    for position in positions_list:
        v = getBeadsVolume(robot, settings, position)
        beads_vol_list.append(v)
        print("Sample at position "+str(position)+" will receive "+str(v)+" uL of magnetic beads.")
    return beads_vol_list


def getBeadsVolume1stStage(robot, settings, position):
    # Will return the volume of beads to perform an upper DNA cutoff, or the first stage of the
    # purification
    return getBeadsVolume(robot, settings, position,
                          beads_vol_param_name='Beads volume upper cutoff',
                          beads_frac_param_name='Fraction upper cutoff',
                          dna_size_cutoff_param_name='DNA size upper cutoff',
                          )


def getBeadsVolume1stStageAllSamples(robot, settings, positions_list):
    v_list = []
    for position in positions_list:
        v = getBeadsVolume1stStage(robot, settings, position)
        v_list.append(v)
        print("Sample at position "+str(position)+" will receive "+str(v)+" uL of magnetic beads at first stage.")
    return v_list

def getBeadsVolume2ndStage(robot, settings, position):
    """
    Will return the volume of the beads to perform smaller DNA cutoff, or the second stage of the
    purification.
    """
    beads_volume_2nd_stage = returnSampleParameter(settings, 'Beads volume', position)
    beads_vol_frac_2nd_stage = returnSampleParameter(settings, 'Fraction', position)
    dna_size_cutoff_2nd_stage = returnSampleParameter(settings, 'DNA size cutoff', position)
    
    v1 = getBeadsVolume1stStage(robot, settings, position)
    init_sample_vol = returnSampleParameter(settings, 'Initial sample volume', position)
    beads_vol_frac_1st_stage = v1 / (init_sample_vol*1.0)
    
    # Deciding the parameter to use for the 2nd stage
    if beads_volume_2nd_stage > 0:
        v2 = beads_volume_2nd_stage
    elif beads_volume_2nd_stage <= 0 and beads_vol_frac_2nd_stage > 0:
        real_fraction = beads_vol_frac_2nd_stage - beads_vol_frac_1st_stage
        v2 = real_fraction * init_sample_vol
    elif beads_volume_2nd_stage <= 0 and beads_vol_frac_2nd_stage <= 0 and dna_size_cutoff_2nd_stage > 0:
        # Approximation using the beads manufacturer data
        # Using if neither beads volume, nor beads volume multiplier are explicitly provided.
        # Getting polynome coefficients
        a, b, c = robot.getBeadsVolumeCoef()
        # Calculating volume multiplier (fraction)
        beads_vol_frac_2nd_stage = a + b / dna_size_cutoff_2nd_stage + c / dna_size_cutoff_2nd_stage ** 2
        real_fraction = beads_vol_frac_2nd_stage - beads_vol_frac_1st_stage
        v2 = real_fraction * init_sample_vol
    else:
        print("No beads volume for the second cutoff provided")
        v2 = 0
    return v2

def getBeadsVolume2ndStageAllSamples(robot, settings, positions_list):
    v_list = []
    for position in positions_list:
        v = getBeadsVolume2ndStage(robot, settings, position)
        v_list.append(v)
        print("Sample at position "+str(position)+" will receive "+str(v)+" uL of magnetic beads at the second stage.")
    return v_list


# Ethanol wash volumes
# ===========================================================================================

def getWashVolume(settings, stage):
    vol_list = []
    samples_positions_list = positionsToPurify(settings)
    if stage == 1:
        parameter_name = 'First stage ethanol wash volume'
    elif stage == 2:
        parameter_name = 'Second stage ethanol wash volume'
    else:
        parameter_name = 'First stage ethanol wash volume'
    for position in samples_positions_list:
        volume = returnSampleParameter(settings, parameter_name, position)
        vol_list.append(volume)
    return vol_list


# Eluent volumes
# ===========================================================================================

def getEluentVolume(settings):
    samples_positions_list = positionsToPurify(settings)
    vol_list = []
    for position in samples_positions_list:
        volume = returnSampleParameter(settings, 'Elution volume', position)
        vol_list.append(volume)
    return vol_list



# Time recording
# ===========================================================================================

def waitAfterTimestamp(timestamp, delay):
    new_ts = time.time()
    while (new_ts - timestamp) < delay:
        time.sleep(1)
        new_ts = time.time()



# ===========================================================================================
# ===========================================================================================

# Here are actual protocol functions

# ===========================================================================================
# ===========================================================================================



def waitAndMixByScript(robot, sample, timestamp, delay, mix_script, tip_col, tip_row):
    new_ts = time.time()
    robot.pickUpNextTip()
    robot.move(z=50)
    while (new_ts - timestamp) < delay:
        robot.mixByScript(sample, mix_script)
        robot.move(z=50)
        new_ts = time.time()
    robot.dumpTipToPosition(tip_col, tip_row)

# TODO: This function can be used at different stages of the protocol, 
# however, it always loads Times to mix while absorbing.
# Make it load proper parameter.
def mixManySamples(robot, samples_list, timestamp, settings):
    """
    Will perform an extra mixes for all the samples provided in samples_list.
    """
    # Retrieving parameters for the mixing process
    delay = returnProtocolParameter(settings, 'DNA absorption time') * 60.0
    mix_cycle_number = int(returnProtocolParameter(settings, 'Times to mix while absorbing'))
    first_sample = samples_list[0]
    mix_script = first_sample.stype.getMixScript()
    delay_between_mixes = delay / (mix_cycle_number + 1)
    # Waiting before the first mix.
    # Needed for the case when the mix cycle number = 0. In this case, 
    # no mixing will happen, just waiting.
    new_ts = time.time()
    time_spent_pipetting = new_ts - timestamp
    wait_time_until_next_mix = delay_between_mixes - time_spent_pipetting
    if wait_time_until_next_mix >= 0:
        time.sleep(wait_time_until_next_mix)    
    for cycle in range(int(mix_cycle_number)):
        for sample in samples_list:
            robot.pickUpNextTip()
            robot.move(z=50)    
            robot.mixByScript(sample, mix_script)
            robot.move(z=50)
            robot.dumpTipToWaste()
            
        timestamp = new_ts
        new_ts = time.time()
        time_spent_pipetting = new_ts - timestamp
        wait_time_until_next_mix = delay_between_mixes - time_spent_pipetting
        if wait_time_until_next_mix >= 0:
            time.sleep(wait_time_until_next_mix)
    

def addBeadsToAll(robot, samples_list, v_beads_list, beads, used_tip_fate='waste', z_safe=50):
    
    robot.moveMagnetsAway(poweroff=True)    # Magnets away from the tubes
    robot.pickUpNextTip()                   # Picking up next tip
    robot.move(z=z_safe)                    # Moving up not to hit anything
    robot.mixByScript(beads)                # Mixing beads (mix script from beads properties)
    robot.move(z=z_safe)                    # Moving up not to hit anything
    
    # Transferring beads suspension from beads tubes to the sample tubes.
    # Using the same tip. Not touching sample tubes.
    for sample, v_beads in zip(samples_list, v_beads_list):
        robot.transferLiquid(beads, sample, v_beads, touch_wall=False)
    
    # Mixing beads suspension with the sample
    counter = 0
    for sample, v_beads in zip(samples_list, v_beads_list):
        # First sample can use the same tip as was used to add beads.
        # For all other samples, getting a new tip. 
        if counter != 0:
            robot.move(z=z_safe)
            robot.pickUpNextTip()
        
        # Pipette is with the tip now.
        robot.move(z=z_safe)                # Moving up not to hit anything
        
        robot.mixByScript(sample)           # Perform mixing
        
        # Starting timer after mixing beads in the first tube.
        # The timer will be used to measure incubation time.
        if counter == 0:
            timestamp = time.time()
        counter += 1
        
        robot.move(z=z_safe)                # After mixing, moving up
        # What to do with the tip? Where to drop?
        if used_tip_fate == 'waste':
            robot.dumpTipToWaste()          # To the waste
        elif used_tip_fate == 'back':
            robot.returnTipBack()           # Back to the rack, so it can be reused later
        else:
            print("Wrong tip fate provided. Dumping the tip to waste.")
            robot.dumpTipToWaste()
    
    return timestamp


def transferSampleToSecondStage(robot, sample, intermediate, z_safe=50, delay=0.5):
    robot.move(z=z_safe)        # Move to the safe heigth
    robot.pickUpNextTip()       # Picking up a tip
    robot.move(z=z_safe)        # Move to the safe heigth
    v = sample.getVolume()      # Volume in the first stage cutoff tube
    # Performing an actual liquid transfer:
    robot.transferLiquid(source=sample, 
                         destination=intermediate, 
                         volume=v, 
                         dry_tube=True,
                         safe_z=z_safe, 
                         delay=delay, 
                         source_tube_radius=2.0) #TODO: Add this to the sample type settings.
    robot.move(z=z_safe)        # Moving up so the tip does not hit anything
    robot.dumpTipToWaste()      # Discarding the tip
    robot.move(z=z_safe)        # Moving up so the tip does not hit anything    


def transferAllSamplesToSecondStage(robot, samples_list, intermediate_list, z_safe=50, delay=0.5):
    for sample, intermediate in zip(samples_list, intermediate_list):
        transferSampleToSecondStage(robot, sample, intermediate, z_safe=z_safe, delay=delay)
        
    

def removeSupernatant(robot, sample, waste, z_safe=50, delay=0.5, fast=False):
    
    robot.move(z=z_safe)        # Move to the safe heigth
    robot.pickUpNextTip()       # Picking up a tip
    robot.move(z=z_safe)        # Move to the safe heigth
    # Uptaking liquid
    v = sample.getVolume() # Volume in the tube with the mix of the eluted DNA and beads
    # Performing an actual liquid transfer:
    robot.transferLiquid(source=sample, 
                         destination=waste, 
                         volume=v, 
                         dry_tube=True,
                         safe_z=z_safe, 
                         delay=delay, 
                         touch_wall=False, # Robot should not touch the wall of the waste, and then going back to the samples.
                         source_tube_radius=2.0) #TODO: Add this to the sample type settings.
    robot.move(z=z_safe)        # Moving up so the tip does not hit anything
    robot.dumpTipToWaste()      # Discarding the tip
    robot.move(z=z_safe)        # Moving up so the tip does not hit anything

def removeSupernatantAllSamples(robot, samples_list, waste, delay=0.5, fast=False):
    counter = 0
    for sample in samples_list:
        removeSupernatant(robot, sample, waste, delay=delay, fast=fast)
        if counter == 0:
            sample_dried_timestamp = time.time()
        counter += 1
    return sample_dried_timestamp

def add80PctEthanol(robot, samples_list, ethanol, volume_list, z_safe=50):
    robot.pickUpNextTip()
    robot.move(z=z_safe)
    
    counter = 0
    for sample, volume in zip(samples_list, volume_list):
        robot.transferLiquid(ethanol, sample, volume, touch_wall=False)
        if counter == 0:
            ethanol_added_time = time.time()
        counter += 1
    
    robot.move(z=z_safe)
    robot.dumpTipToWaste()
    
    return ethanol_added_time

def elutionMix(robot, sample, volume, delay=0.5):
    z0 = robot._getTubeZBottom(sample)
    z_top = sample.getSampleTopAbsZ(added_length=robot._calcExtraLength())
    robot.movePipetteToVolume(0)
    robot.movePipetteToVolume(volume+5)
    robot.movePipetteToVolume(volume)
    robot.move(z=z0-0.5)
    robot.movePipetteToVolume(0)
    time.sleep(delay)
    # Washing steps, moving along the wall
    # 1
    z_curr = z_top + 24
    #z_curr = sample.calcAbsLiquidLevelFromVol(500, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    robot.moveAxisDelta('X', 3.0)
    robot.movePipetteToVolume(volume/4.0)
    time.sleep(delay/4.0)
    # 2
    z_curr = z_top + 28
    #z_curr = sample.calcAbsLiquidLevelFromVol(300, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    #robot.moveAxisDelta('X', -0.629)
    robot.movePipetteToVolume(2 * (volume/4.0))
    time.sleep(delay/4.0)
    # 3
    z_curr = z_top + 32
    #z_curr = sample.calcAbsLiquidLevelFromVol(150, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    robot.moveAxisDelta('X', -0.629)
    robot.movePipetteToVolume(3 * (volume/4.0))
    time.sleep(delay/4.0)
    # 4
    z_curr = z_top + 36
    #z_curr = sample.calcAbsLiquidLevelFromVol(150, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    robot.moveAxisDelta('X', -0.629)
    robot.movePipetteToVolume(volume)
    time.sleep(delay/4.0)
    
    x, y = sample.getCenterXY()
    robot.move(x=x, y=y)
    z_curr = sample.calcAbsLiquidLevelFromVol(volume+100, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    
    robot.movePipetteToVolume(volume+50)
    time.sleep(delay)
    robot.movePipetteToVolume(0)

def elutionMixLrgVol(robot, sample, volume, delay=0.5):
    z0 = robot._getTubeZBottom(sample)
    z_top = sample.getSampleTopAbsZ(added_length=robot._calcExtraLength())
    
    # Uptaking
    robot.movePipetteToVolume(0)
    robot.movePipetteToVolume(volume+5)
    robot.movePipetteToVolume(volume)
    robot.move(z=z0-0.8)
    robot.movePipetteToVolume(0)
    time.sleep(delay)
    
    # Ejecting liquid
    z_curr = sample.calcAbsLiquidLevelFromVol(1000, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    robot.moveAxisDelta('X', 3.4)
    robot.movePipetteToVolume(volume+50)
    z_curr = sample.calcAbsLiquidLevelFromVol(500, added_length=robot._calcExtraLength())
    robot.move(z=z_curr)
    
    # To back position
    x, y = sample.getCenterXY()
    robot.move(x=x, y=y)
    
    robot.movePipetteToVolume(0)

#TODO: make safe_z a general property of the robot
def elute(robot, sample, eluent, volume, settings, mix_delay=0.5, mix_times=None, safe_z=50):
    
    # Loading parameters
    if mix_times is None:
        mix_times = int(returnProtocolParameter(settings, 'Elution times to mix'))
    
    robot.moveMagnetsAway(poweroff=True)
    robot.pickUpNextTip()
    robot.move(z=safe_z)
    robot.transferLiquid(eluent, sample, volume)
    for i in range(mix_times):
        elutionMixLrgVol(robot, sample, volume)
        elutionMixLrgVol(robot, sample, volume)
        elutionMix(robot, sample, volume)
    elution_start_time = time.time()
    elutionMix(robot, sample, volume)
    elutionMix(robot, sample, volume)
    
    robot.move(z=safe_z)
    #robot.returnTipBack()
    robot.dumpTipToWaste()
    sample.setVolume(volume)
    return elution_start_time

def eluteAllSamples(robot, samples_list, eluent, V_eluent_list, settings, mix_delay=0.5, safe_z=50):
    counter = 0
    for sample, V_eluent in zip(samples_list, V_eluent_list):
        ts = elute(robot, sample, eluent, V_eluent, settings, mix_delay=mix_delay, safe_z=safe_z)
        print ()
        if counter == 0:
            elution_start_timestamp = ts
        counter += 1
    return elution_start_timestamp

def separateEluate(robot, eluate_tube, result_tube, pipette_delay=0.5, source_tube_radius=2, safe_z=50):
    robot.move(z=safe_z)        # Moving up so the tip does not hit anything
    robot.pickUpNextTip()       # Getting a new tip
    robot.move(z=safe_z)        # Moving up so the tip does not hit anything
    # Uptaking liquid
    v = eluate_tube.getVolume()      # Volume in the tube with the mix of the eluted DNA and beads
    # Performing an actual liquid transfer:
    robot.transferLiquid(source=eluate_tube, 
                         destination=result_tube, 
                         volume=v, 
                         dry_tube=True,
                         safe_z=safe_z, 
                         delay=pipette_delay, 
                         source_tube_radius=source_tube_radius)
    robot.move(z=safe_z)        # Moving up so the tip does not hit anything
    robot.dumpTipToWaste()      # Discarding the tip
    robot.move(z=safe_z)        # Moving up so the tip does not hit anything

def separateEluateAllTubes(robot, eluate_list, results_list):
    for sample, result in zip(eluate_list, results_list):
        separateEluate(robot, sample, result)


def purify_one_cutoff(robot, settings):
    """
    Functions for 1-cutoff purification, that removes lower length DNA.
    Call this function to perform an entire purification
    """
    # Loading settings
    samples_list = initSamples(robot, settings)
    result_list = initResultTubes(robot, settings)
    beads, waste, water, EtOH80pct = initReagents(robot, settings)
    positions_list = positionsToPurify(settings)
    v_beads_list = getBeadsVolumesForAllSamples(robot, settings, positions_list)
    v_ethanol_1st_stage_list = getWashVolume(settings, 1)
    v_ethanol_2nd_stage_list = getWashVolume(settings, 2)
    v_eluent_list = getEluentVolume(settings)
    
    max_pipette_speed = returnMaxPipetteSpeed(settings)
    beads_pipetting_speed = returnBeadsPipettingSpeed(settings)
    ethanol_pipetting_speed = returnEthanolPipettingSpeed(settings)
    eluent_pipetting_speed = returnEluentPipettingSpeed(settings)
    
    T_pull = returnProtocolParameter(settings, 'Beads pulling time after absorption') * 60.0
    T_wash_1 = returnProtocolParameter(settings, 'First stage ethanol wash time') * 60.0
    T_wash_2 = returnProtocolParameter(settings, 'Second stage ethanol wash time') * 60.0
    T_dry = returnProtocolParameter(settings, 'Time to dry after ethanol wash') * 60.0
    T_elute = returnProtocolParameter(settings, 'Elution time') * 60.0
    
    print("This is the one-stage magnetic beads purification.")
    print("It will remove any DNA and other molecules of low molecular weight.")
    print("I will purify "+str(len(samples_list))+" samples")
    print("I will use the following magnetic beads volumes to purify: ")
    print(str(v_beads_list))
    print("I will elute the resulting DNA with eluent of the following volumes: ")
    print(str(v_eluent_list))
    print("")
    print("Purification started ", datetime.now().strftime("%H:%M:%S"))
    print("")
    
    # Starting the physical protocol
    print("Adding magnetic beads. Started ", datetime.now().strftime("%H:%M:%S"))
    
    # Setting the pipette speed for pipetting more viscous beads.
    robot.setSpeedPipette(beads_pipetting_speed) 
    timestamp_beads_added = addBeadsToAll(robot, samples_list, v_beads_list, beads)
    robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed
    print("Beads added ", datetime.now().strftime("%H:%M:%S"))
    print("Now waiting for DNA absorption.")
    
    # Extra mixing samples with magnetic beads during the protocol.
    mixManySamples(robot, samples_list, timestamp_beads_added, settings)
    
    # Pulling beads to the side
    print("DNA absorption finished ", datetime.now().strftime("%H:%M:%S"))
    print("Now pulling the beads towards the tube side")
    print("Pulling time is "+str(T_pull/60)+" minutes")
    print("Started ", datetime.now().strftime("%H:%M:%S"))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    
    # Removing supernatant (the desired DNA of larger molecular weight is on the beads)
    print("Beads are now on the side of the tube.")
    print("Removing supernatant. Started ", datetime.now().strftime("%H:%M:%S"))
    # Setting the pipette speed for the viscous beads supernatant
    robot.setSpeedPipette(beads_pipetting_speed)
    ts = removeSupernatantAllSamples(robot, samples_list, waste, fast=True)
    robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed
    print("Supernatant removed from all tubes at ", datetime.now().strftime("%H:%M:%S"))
    
    # 1st stage ethanol wash
    print("Now starting ethanol washes.")
    print("Adding 80% ethanol. Started ", datetime.now().strftime("%H:%M:%S"))
    # Setting the pipette speed for the less viscous ethanol solution
    robot.setSpeedPipette(ethanol_pipetting_speed)
    timestamp_ethanol_added = add80PctEthanol(robot, samples_list, EtOH80pct, v_ethanol_1st_stage_list)
    print("Wash 1: ethanol added ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_1)
    print("Wash 1: ethanol incubation finished ", datetime.now().strftime("%H:%M:%S"))
    ts = removeSupernatantAllSamples(robot, samples_list, waste, fast=True)
    print("Wash 1: ethanol removed ", datetime.now().strftime("%H:%M:%S"))
    
    # 2nd stage ethanol wash
    timestamp_ethanol_added = add80PctEthanol(robot, samples_list, EtOH80pct, v_ethanol_2nd_stage_list)
    print("Wash 2: ethanol added ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_2)
    print("Wash 2: ethanol incubation finished ", datetime.now().strftime("%H:%M:%S"))
    timestamp_ethanol_removed = removeSupernatantAllSamples(robot, samples_list, waste)
    print("Wash 2: ethanol removed ", datetime.now().strftime("%H:%M:%S"))
    robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed
    
    # Drying ethanol
    print("Now drying the tubes from the remaining ethanol.")
    print("Time to dry: ", str(T_dry))
    print("Drying started: ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_removed, T_dry)
    print("Ethanol drying finished ", datetime.now().strftime("%H:%M:%S"))
    
    # Elution
    # Adding eluent
    print("Starting elution. Started ", datetime.now().strftime("%H:%M:%S"))
    # Setting the pipette speed for the eluent solution (usually water)
    robot.setSpeedPipette(eluent_pipetting_speed)
    elution_start_timestamp = eluteAllSamples(robot, samples_list, water, v_eluent_list, settings)
    print("Eluent added ", datetime.now().strftime("%H:%M:%S"))
    print("Now mixing the samples. Started at ", datetime.now().strftime("%H:%M:%S"))
    mixManySamples(robot, samples_list, elution_start_timestamp, settings)
    print("Elution incubation finished ", datetime.now().strftime("%H:%M:%S"))
    
    # Pulling beads to the side
    print("Now pulling the beads towards the tube side")
    print("Pulling time is "+str(T_pull/60)+" minutes")
    print("Started ", datetime.now().strftime("%H:%M:%S"))
    robot.moveMagnetsTowardsTube()
    time.sleep(T_pull)
    print("Beads pulled to the side ", datetime.now().strftime("%H:%M:%S"))
    
    # Moving eluate to the results tubes
    print("Now moving the eluate to the results tubes. Started ", datetime.now().strftime("%H:%M:%S"))
    separateEluateAllTubes(robot, samples_list, result_list)
    print("Eluate transferred to the new tube ", datetime.now().strftime("%H:%M:%S"))
    print("Purification finished ", datetime.now().strftime("%H:%M:%S"))
    robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed
    

def purifyTwoCutoffs(robot, settings):
    """
    Performs two-cutoffs purification; removing shorter and longer DNA.
    Call this function to perform entire purification
    """
    # Loading settings
    samples_list = initSamples(robot, settings)
    intermediate_list = initIntermediate(robot, settings) # Tubes at which the 2nd stage is performed.
    result_list = initResultTubes(robot, settings)
    beads, waste, water, EtOH80pct = initReagents(robot, settings)
    positions_1st_stage_list = positionsToPurify(settings)
    positions_2nd_stage_list = positionsToPurify2ndStage(settings)
    # Both should have positions_1st_stage_list
    v_beads_1st_stage_list = getBeadsVolume1stStageAllSamples(robot, settings, positions_1st_stage_list)
    v_beads_2nd_stage_list = getBeadsVolume2ndStageAllSamples(robot, settings, positions_1st_stage_list)
    
    v_ethanol_1st_stage_list = getWashVolume(settings, 1)
    v_ethanol_2nd_stage_list = getWashVolume(settings, 2)
    v_eluent_list = getEluentVolume(settings)

    T_pull = returnProtocolParameter(settings, 'Beads pulling time after absorption') * 60.0
    T_wash_1 = returnProtocolParameter(settings, 'First stage ethanol wash time') * 60.0
    T_wash_2 = returnProtocolParameter(settings, 'Second stage ethanol wash time') * 60.0
    T_dry = returnProtocolParameter(settings, 'Time to dry after ethanol wash') * 60.0
    T_elute = returnProtocolParameter(settings, 'Elution time') * 60.0

    print("This is the two-stages magnetic beads purification.")
    print("It will remove any DNA and other molecules of too low and too high molecular weight.")
    print("I will purify "+str(len(samples_list))+" samples")
    print("I will use the following magnetic beads volumes for short DNA cutoff: ")
    print(str(v_beads_1st_stage_list))
    print("I will use the following magnetic beads volumes for long DNA cutoff: ")
    print(str(v_beads_2nd_stage_list))
    print("I will elute the resulting DNA with eluent of the following volumes: ")
    print(str(v_eluent_list))
    print("")
    print("Purification started ", datetime.now().strftime("%H:%M:%S"))
    print("")    
    
    # Starting the physical protocol
    
    # First cutoff.
    # --------------------------
    print("Adding magnetic beads. Started ", datetime.now().strftime("%H:%M:%S"))
    timestamp_beads_added = addBeadsToAll(robot, samples_list, v_beads_1st_stage_list, beads)
    print("Beads added ", datetime.now().strftime("%H:%M:%S"))
    print("Now waiting for DNA absorption.")    
    
    # Extra mixing samples with magnetic beads during the protocol.
    mixManySamples(robot, samples_list, timestamp_beads_added, settings)
    
    # Pulling beads to the side
    print("DNA absorption finished ", datetime.now().strftime("%H:%M:%S"))
    print("Now pulling the beads towards the tube side")
    print("Pulling time is "+str(T_pull/60)+" minutes")
    print("Started ", datetime.now().strftime("%H:%M:%S"))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    
    # Transferring to the intermediary tubes
    transferAllSamplesToSecondStage(robot, samples_list, intermediate_list)
    
    # After tubes are transferred, moving magnets away.
    robot.moveMagnetsAway(poweroff=True)
    
    # Second cutoff
    # -------------
    print("Adding magnetic beads. Started ", datetime.now().strftime("%H:%M:%S"))
    timestamp_beads_added = addBeadsToAll(robot, intermediate_list, v_beads_2nd_stage_list, beads)
    print("Beads added ", datetime.now().strftime("%H:%M:%S"))
    print("Now waiting for DNA absorption.")
    
    # Extra mixing samples with magnetic beads during the protocol.
    mixManySamples(robot, intermediate_list, timestamp_beads_added, settings)
    
    # Pulling beads to the side
    print("DNA absorption finished ", datetime.now().strftime("%H:%M:%S"))
    print("Now pulling the beads towards the tube side")
    print("Pulling time is "+str(T_pull/60)+" minutes")
    print("Started ", datetime.now().strftime("%H:%M:%S"))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    
    # Removing supernatant (the desired DNA of larger molecular weight is on the beads)
    print("Beads are now on the side of the tube.")
    print("Removing supernatant. Started ", datetime.now().strftime("%H:%M:%S"))
    ts = removeSupernatantAllSamples(robot, intermediate_list, waste, fast=True)
    print("Supernatant removed from all tubes at ", datetime.now().strftime("%H:%M:%S"))
    
    # 1st stage ethanol wash
    print("Now starting ethanol washes.")
    print("Adding 80% ethanol. Started ", datetime.now().strftime("%H:%M:%S"))
    timestamp_ethanol_added = add80PctEthanol(robot, intermediate_list, EtOH80pct, v_ethanol_1st_stage_list)
    print("Wash 1: ethanol added ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_1)
    print("Wash 1: ethanol incubation finished ", datetime.now().strftime("%H:%M:%S"))
    ts = removeSupernatantAllSamples(robot, intermediate_list, waste, fast=True)
    print("Wash 1: ethanol removed ", datetime.now().strftime("%H:%M:%S"))
    
    # 2nd stage ethanol wash
    timestamp_ethanol_added = add80PctEthanol(robot, intermediate_list, EtOH80pct, v_ethanol_2nd_stage_list)
    print("Wash 2: ethanol added ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_2)
    print("Wash 2: ethanol incubation finished ", datetime.now().strftime("%H:%M:%S"))
    timestamp_ethanol_removed = removeSupernatantAllSamples(robot, intermediate_list, waste)
    print("Wash 2: ethanol removed ", datetime.now().strftime("%H:%M:%S"))
    
    # Drying ethanol
    print("Now drying the tubes from the remaining ethanol.")
    print("Time to dry: ", str(T_dry))
    print("Drying started: ", datetime.now().strftime("%H:%M:%S"))
    waitAfterTimestamp(timestamp_ethanol_removed, T_dry)
    print("Ethanol drying finished ", datetime.now().strftime("%H:%M:%S"))
    
    # Elution
    # Adding eluent
    print("Starting elution. Started ", datetime.now().strftime("%H:%M:%S"))
    elution_start_timestamp = eluteAllSamples(robot, intermediate_list, water, v_eluent_list, settings)
    print("Eluent added ", datetime.now().strftime("%H:%M:%S"))
    print("Now mixing the samples. Started at ", datetime.now().strftime("%H:%M:%S"))
    mixManySamples(robot, intermediate_list, elution_start_timestamp, settings)
    print("Elution incubation finished ", datetime.now().strftime("%H:%M:%S"))
    
    # Pulling beads to the side
    print("Now pulling the beads towards the tube side")
    print("Pulling time is "+str(T_pull/60)+" minutes")
    print("Started ", datetime.now().strftime("%H:%M:%S"))
    robot.moveMagnetsTowardsTube()
    time.sleep(T_pull)
    print("Beads pulled to the side ", datetime.now().strftime("%H:%M:%S"))
    
    # Moving eluate to the results tubes
    print("Now moving the eluate to the results tubes. Started ", datetime.now().strftime("%H:%M:%S"))
    separateEluateAllTubes(robot, intermediate_list, result_list)
    print("Eluate transferred to the new tube ", datetime.now().strftime("%H:%M:%S"))
    print("Purification finished ", datetime.now().strftime("%H:%M:%S"))
    
    
    
    

# Main body
# ===========================================================================================

if __name__ == '__main__':
    print(" ")
    print("=================================================================================")
    print("This is the script for purifying DNA mixture by removing any DNA molecules")
    print("shorter then a certain size.")
    print(" ")
    print("I will start from running a few sanity checks")

    # Making sure the argument provided
    if isArgumentPassed():
        settings_file_path = sys.argv[1]   # Getting the settings
        print("Found an argument: "+settings_file_path+", OK")
    else:
        printHowToUse()
        sys.exit("Script terminated") 

    # Checking whether the samplesheet file exists
    if isSampleSheetExist(settings_file_path):
        print("This file exists, OK")
        # Loading data settings
        settings = loadSettings(settings_file_path)
    else:
        print("Can't locate a samplesheet.")
        print("You provided the following path to the samplesheet: ")
        print(settings_file_path)
        print("However, there was no file like that found.")
        print(" ")
        printHowToUse()
        sys.exit("Script terminated") 
    
    # Checking whether there are at least two COM ports found.
    # Bernie Robot will be recognized as two COM ports.
    # If less are found, that means robot is either not connected, or 
    # there is some hardware failure.
    if areTwoPortsAvailable():
        print("Found COM ports, will try to identify them, OK")
    else:
        sys.exit("Script terminated") 
        
    # Initializing  the robot and homing it.
    # TODO: load port names from the settings file
    
    # How many stages (cutoffs) to perform:
    stages = decideCutoffNumber(settings)
    
    # Tip rack type:
    tip_rack_type = returnTipRackType(settings)
    
    # Ports
    load_cell_port = returnLoadCellPort(settings)
    cartesian_port = returnCartesianPort(settings)
    
    # Initializing the robot
    ber = bl.robot(cartesian_port_name=cartesian_port, loadcell_port_name=load_cell_port, tips_type=tip_rack_type)
    ber.home()
    
    if stages == 1:
        purify_one_cutoff(ber, settings)
    elif stages == 2:
        purifyTwoCutoffs(ber, settings)
    else:
        print("Can't find the number of cutoffs.")
        print("Specify 'Number of cutoffs' parameter in the sample sheet file.")
        print("Set '1' if you want only to remove short DNA, set '2' if you want to remove both too short and too long DNA.")

    ber.powerStepperOff('A') # to prevent unnecessary heating. Must be off already, but just in case.
    ber.powerStepperOff()    # Powering off all steppers
    
    ber.close()
    
    