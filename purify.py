# Final script that performs magnetic beads purification on one side

import sys
import os
import csv
import time
import logging
from datetime import datetime

# loacl libraries
import bernielib as bl

# TODO: A There is some problem when robot does not hit the tip. It does not perform search around.
# TODO: AAA Robot touches waste side, then moves again to the sample. Make that stop.

# Functions for sanity checks
# ============================================================================================

# Setting up logging to file
logging.basicConfig(
                    filename=(str(time.time())+'purify.log'), 
                    level=logging.DEBUG,
                    format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
                    )

# Handler which writes INFO messages to the console
console = logging.StreamHandler()
# Setting output to INFO level
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)



class settings():
    def __init__(self, filepath):
        if self.sampleSheetExist(filepath):
            self.loadSettings(filepath)
            self.loadIndividualSettings()
    
    def loadSettings(self, filepath):
        logging.debug("Opening settings file %s" % (filepath, ))
        try:
            with open(filepath, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                self.settings = list(csv_reader) # Loads settings as a python csv object
            logging.debug("Settings file successfully opened.")
            return self.settings
        except:
            logging.error("Failed to import the samplesheet file with the experiment settings.")
            sys.exit("Script terminated")

    def sampleSheetExist(self, filepath):
        if os.path.exists(filepath):
            logging.debug("Settings file in the path %s exists." % filepath)
            return True
        else:
            logging.error("Samplesheet not found in the path %s, or can't open that file." % settings_file_path)
            printHowToUse()
            sys.exit("Script terminated") 

    def getRowWithParameter(self, desired_parameter):
        for row in self.settings:
            current_parameter = row['Parameters']
            if current_parameter == desired_parameter:
                return row
    
    def positionsToPurify(self):
        positions_list = []
        # Using "initial sample volume" parameter to identify whether to 
        # purify this sample.
        row = self.getRowWithParameter('Initial sample volume')
        for position in range(12):
            # For the samples to purify, the "initial sample volume" parameter will be positive
            if float(row[str(position)]) > 0:
                positions_list.append(position)
        return positions_list
    
    def positionsToPurify2ndStage(self):
        sample_positions_list = self.positionsToPurify()
        # First tube for the second stage purification is at position '6'.
        pos_2nd_stage_list = [x+6 for x in sample_positions_list]
        return pos_2nd_stage_list
    
    def returnSampleParameter(self, param, position):
        try:
            row = self.getRowWithParameter(param)
        except:
            logging.error("A critical parameter %s is not in the samplesheet file." % (param, ))
            logging.error("Please edit your samplesheet and try again.")
            sys.exit("Script terminated.")
        try:
            value = row[str(position)]
        except:
            logging.error("A position number %s in the parameter %s is not in the sample sheet." % (position, param, ))
            logging.error("Please correct your samplesheet and try again.")
            sys.exit("Script terminated.")
        try:
            value = float(value)
        except:
            pass
        return value    

    def _returnSampleParameterList(self, param):
        return [self.returnSampleParameter(param, x) for x in self.positionsToPurify()]

    def returnProtocolParameter(self, param):
        return self.returnSampleParameter(param, '0')

    def loadIndividualSettings(self):
        """
        To be called at initialization. Will load all the individual settings.
        """
        self.tip_rack_type = self.returnProtocolParameter('Tip Rack Type')
        self.load_cell_port = self.returnPort(kind='Load cells controller port')
        self.cartesian_port = self.returnPort(kind='Cartesian controller port')
        self.cutoffs = self.returnProtocolParameter('Number of cutoffs')
        self.pipetting_delay = self.returnProtocolParameter('Delay after pipetting')
        self.default_pipette_speed = self.returnProtocolParameter('Maximum pipetting speed')
        self.beads_pipetting_speed = self.returnProtocolParameter('Beads pipetting speed')
        self.ethanol_pipetting_speed = self.returnProtocolParameter('Ethanol pipetting speed')
        self.eluent_pipetting_speed = self.returnProtocolParameter('Eluent pipetting speed')
        self.initial_sample_vol_list = self._returnSampleParameterList('Initial sample volume')
        self.number_of_samples = len(self.initial_sample_vol_list)
        self.positions_to_purify_list = self.positionsToPurify()
        self.positions_2nd_stage_tubes = self.positionsToPurify2ndStage()
        
        self.beads_tube_type = self.returnProtocolParameter('Beads tube type')
        self.waste_tube_type = self.returnProtocolParameter('Waste tube type')
        self.eluent_tube_type = self.returnProtocolParameter('Eluent tube type')
        self.ethanol_tube_type = self.returnProtocolParameter('Ethanol tube type')
        
        self.beads_rack_name = self._getRackName('Beads')
        self.waste_rack_name = self._getRackName('Waste')
        self.eluent_rack_name = self._getRackName('Eluent')
        self.ethanol_rack_name = self._getRackName('Ethanol')
        
        self.beads_column_in_rack, self.beads_row_in_rack = self._getTubePositionInRack('Beads')
        self.waste_column_in_rack, self.waste_row_in_rack = self._getTubePositionInRack('Waste')
        self.eluent_column_in_rack, self.eluent_row_in_rack = self._getTubePositionInRack('Eluent')
        self.ethanol_column_in_rack, self.ethanol_row_in_rack = self._getTubePositionInRack('Ethanol')
        
        self.V_beads = self.returnProtocolParameter('Beads initial volume')
        self.V_waste = self.returnProtocolParameter('Waste initial volume')
        self.V_eluent = self.returnProtocolParameter('Eluent initial volume')
        self.V_ethanol = self.returnProtocolParameter('Ethanol initial volume')
        
        self.beads_vol_1st_stage_list = self._getBeadsVolForAllSamples(stage=1)
        # Will get some meaningful data only if cutoffs setting is 2.
        self.beads_vol_2nd_stage_list = self._getBeadsVolForAllSamples(stage=self.cutoffs)
        
        self.wash_1_vol_list = self._returnSampleParameterList('First stage ethanol wash volume')
        self.wash_2_vol_list = self._returnSampleParameterList('Second stage ethanol wash volume')
        self.eluent_vol_list = self._returnSampleParameterList('Elution volume')
        
        
    def returnPort(self, kind):
        try:
            value = self.returnProtocolParameter(kind)
        except:
            logging.error("returnPort: Setting file has no port with such name: %s" % kind)
            value = 'auto'
    
        if value == 'auto':
            return None
        else:
            return value
        
    def _getRackName(self, reagent):
        rack_name = self.returnProtocolParameter(reagent+' tube rack')
        if rack_name == 'samples' or rack_name == 'reagents':
            return rack_name
        else:
            logging.error("_getRackType: settings file has a wrong rack name specified.")
            logging.error("For the reagent '%s', the correct rack name may be 'samples' or 'reagents'" % reagent)
            logging.error("but the name %s was provided." % rack_name)
            return 

    def _getTubePositionInRack(self, reagent):
        col = int(self.returnProtocolParameter(reagent+' tube column'))
        row = int(self.returnProtocolParameter(reagent+' tube well'))
        return col, row



    def _getBeadsSetting(self, position, stage, setting_prefix):
        if stage == 1 and self.cutoffs == 2:
            param_name = setting_prefix + ' upper cutoff'
        else:
            if setting_prefix == 'DNA size':
                param_name = 'DNA size cutoff'
            else:
                param_name = setting_prefix
        v = self.returnSampleParameter(param_name, position)
        return v
    
    def _getBeadsVolDirectly(self, position, stage):
        return self._getBeadsSetting(position, stage, 'Beads volume')
    
    def _calcBeadsVolFromFrac(self, position, fraction):
        initial_sample_volume = self.initial_sample_vol_list[position]
        v = initial_sample_volume * fraction
        return v
    
    def _getBeadsVolUsingFraction(self, position, stage):
        beads_volume_fraction = self._getBeadsSetting(position, stage, 'Fraction')
        if stage == 2:
            # Second stage of the cutoff is calculated differently then the first stage.
            # One need to correct for the PEG solution that is already present in the tube
            # from the first stage.
            beads_vol_frac_1st_stage = self._getBeadsSetting(position, stage=1, setting_prefix='Fraction')
            beads_volume_fraction = beads_volume_fraction - beads_vol_frac_1st_stage
        beads_volume = self._calcBeadsVolFromFrac(position, beads_volume_fraction)
        return beads_volume

    def _calcBeadVolFractionFromDNACutoff(self, dna_size_cutoff):
        # Getting polynome coefficients
        a, b, c = bl.getBeadsVolumeCoef()
        # Calculating volume multiplier (fraction)
        frac = a + b / dna_size_cutoff + c / dna_size_cutoff ** 2
        return frac
    
    def _getBeadsVolUsingDNACutoff(self, position, stage):
        dna_size_cutoff = self._getBeadsSetting(position, stage, 'DNA size')
        beads_volume_fraction = self._calcBeadVolFractionFromDNACutoff(dna_size_cutoff)
        if stage == 2:
            # Second stage of the cutoff is calculated differently then the first stage.
            # One need to correct for the PEG solution that is already present in the tube
            # from the first stage.
            dna_size_cutoff_1st_stage = self._getBeadsSetting(position, stage=1, setting_prefix='DNA size')
            beads_vol_frac_1st_stage = self._calcBeadVolFractionFromDNACutoff(dna_size_cutoff_1st_stage)
            beads_volume_fraction = beads_volume_fraction - beads_vol_frac_1st_stage
        beads_volume = self._calcBeadsVolFromFrac(position, beads_volume_fraction)
        return beads_volume

    def _beadsVolNotValid(self, v):
        if v is None:
            return True
        else:
            if v <= 0:
                return True
            else:
                return False
    
    def _getBeadsVolume(self, position, stage):
        """
        Will get beads volume for the first stage of the purification
        """
        beads_volume = self._getBeadsVolDirectly(position, stage)
        if self._beadsVolNotValid(beads_volume):
            # If the beads volumes are not explicitly provided, use the volume multiplier (fraction)
            beads_volume = self._getBeadsVolUsingFraction(position, stage)
            if self._beadsVolNotValid(beads_volume):
                # Approximation using the beads manufacturer data
                # Using if neither beads volume, nor beads volume multiplier are explicitly provided.
                beads_volume = self._getBeadsVolUsingDNACutoff(position, stage)
                if self._beadsVolNotValid(beads_volume):
                    logging.warning("_getBeadsVolume: No beads volume provided in the samplesheet for the sample number %s" % position)
                    beads_volume = 0
        logging.debug("Sample at position %s will receive %s uL of magnetic beads." % (position, beads_volume, ))
        return beads_volume
    
    
    def _getBeadsVolForAllSamples(self, stage):
        return [self._getBeadsVolume(x, stage) for x in self.positionsToPurify()]
        









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
    logging.debug("printHowToUse function invoked.")
    logging.debug("TODO: place URL to the instructions.")
    logging.info("This is the script for purifying DNA mixture by removing any DNA molecules shorter then a certain size./n")
    logging.info("Usage:")
    logging.info("python purify_one_cutoff.py samplesheet.csv")
    logging.info("Here, samplesheet.csv is the file with the purification settings.")
    logging.info("Please see the instructions on how to modify your samplesheet.csv")
    logging.info("")


# Functions for loading and handling the purification settings
# ===========================================================================================

def loadSettings(filepath):
    logging.debug("Opening settings file %s" % (filepath, ))
    try:
        with open(filepath, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            content = list(csv_reader)
        logging.debug("Settings file successfully opened.")
        return content
    except:
        logging.error("Failed to import the samplesheet file with the experiment settings.")
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
        logging.error("A critical parameter %s is not in the samplesheet file." % (param, ))
        logging.error("Please edit your samplesheet and try again.")
        sys.exit("Script terminated.")
    try:
        value = row[str(position)]
    except:
        logging.error("A position number %s in the parameter %s is not in the sample sheet." % (position, param, ))
        logging.error("Please correct your samplesheet and try again.")
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
        logging.error("initReagents: Wrong Beads tube rack specified in the samplesheet file.")
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
        logging.error("initReagents: Wrong waste tube rack specified in the samplesheet file.")
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
        logging.error("initReagents: Wrong Eluent tube rack specified in the samplesheet file.")
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
        logging.error("initReagents: Wrong Ethanol tube rack specified in the samplesheet file.")
        return
    ethanol_col = 0
    ethanol_row = int(returnProtocolParameter(settings, 'Ethanol tube position'))
    V_avail_ethanol = returnProtocolParameter(settings, 'Ethanol volume')    
    
    ethanol80_tube = bl.createSample(ethanol_tube_type, 'EtOH80pct', ethanol_rack, ethanol_col, ethanol_row, V_avail_ethanol)
    
    return beads_tube, waste_tube, eluent_tube, ethanol80_tube




# Beads volume calculations
# ===========================================================================================

def getBeadsVolume(settings, position,
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
        a, b, c = bl.getBeadsVolumeCoef()
        # Calculating volume multiplier (fraction)
        multiplier = a + b / dna_size_cutoff + c / dna_size_cutoff ** 2
        use_beads_volume = init_sample_vol * multiplier
    else:
        logging.warning("getBeadsVolume: No beads volume provided in the samplesheet.")
        logging.warning("Sample position %s" % (position, ))
        use_beads_volume = 0
    return use_beads_volume    

def getBeadsVolumesForAllSamples(settings, positions_list):
    beads_vol_list = []
    for position in positions_list:
        v = getBeadsVolume(settings, position)
        beads_vol_list.append(v)
        logging.debug("Sample at position %s will receive %s uL of magnetic beads." % (position, v, ))
    return beads_vol_list


def getBeadsVolume1stStage(settings, position):
    # Will return the volume of beads to perform an upper DNA cutoff, or the first stage of the
    # purification
    return getBeadsVolume(settings, position,
                          beads_vol_param_name='Beads volume upper cutoff',
                          beads_frac_param_name='Fraction upper cutoff',
                          dna_size_cutoff_param_name='DNA size upper cutoff',
                          )


def getBeadsVolume1stStageAllSamples(settings, positions_list):
    v_list = []
    for position in positions_list:
        v = getBeadsVolume1stStage(settings, position)
        v_list.append(v)
        logging.debug("Sample at position %s will receive %s uL of magnetic beads." % (position, v, ))
    return v_list

def getBeadsVolume2ndStage(settings, position):
    """
    Will return the volume of the beads to perform smaller DNA cutoff, or the second stage of the
    purification.
    """
    beads_volume_2nd_stage = returnSampleParameter(settings, 'Beads volume', position)
    beads_vol_frac_2nd_stage = returnSampleParameter(settings, 'Fraction', position)
    dna_size_cutoff_2nd_stage = returnSampleParameter(settings, 'DNA size cutoff', position)
    
    v1 = getBeadsVolume1stStage(settings, position)
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
        a, b, c = bl.getBeadsVolumeCoef()
        # Calculating volume multiplier (fraction)
        beads_vol_frac_2nd_stage = a + b / dna_size_cutoff_2nd_stage + c / dna_size_cutoff_2nd_stage ** 2
        real_fraction = beads_vol_frac_2nd_stage - beads_vol_frac_1st_stage
        v2 = real_fraction * init_sample_vol
    else:
        logging.warning("getBeadsVolume2ndStage: No beads volume for the 2nd cutoff provided in the samplesheet.")
        logging.warning("Sample position %s" % (position, ))
        v2 = 0
    return v2

def getBeadsVolume2ndStageAllSamples(settings, positions_list):
    v_list = []
    for position in positions_list:
        v = getBeadsVolume2ndStage(settings, position)
        v_list.append(v)
        logging.debug("Sample at position %s will receive %s uL of magnetic beads during the second stage of the purification." % (position, v, ))
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
    

def addBeadsToAll(robot, samples_list, 
                  v_beads_list, beads, pipetting_speed, used_tip_fate='waste', z_safe=50, delay=1):
    
    default_pipette_speed = robot.getSpeedPipette() # Getting robot default pipetting speed
    
    robot.setSpeedPipette(pipetting_speed) 
    
    robot.moveMagnetsAway(poweroff=True)    # Magnets away from the tubes
    robot.pickUpNextTip()                   # Picking up next tip
    robot.move(z=z_safe)                    # Moving up not to hit anything
    robot.mixByScript(beads)                # Mixing beads (mix script from beads properties)
    robot.move(z=z_safe)                    # Moving up not to hit anything
    
    # Transferring beads suspension from beads tubes to the sample tubes.
    # Using the same tip. Not touching sample tubes.
    for sample, v_beads in zip(samples_list, v_beads_list):
        robot.transferLiquid(beads, sample, v_beads, touch_wall=False, delay=delay)
    
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
            logging.warning("Wrong tip fate provided. Dumping the tip to waste.")
            robot.dumpTipToWaste()
    
    robot.setSpeedPipette(default_pipette_speed) # Resetting the max pipette speed
    
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

def removeSupernatantAllSamples(robot, samples_list, waste, pipette_speed, delay=0.5, fast=False):
    logging.info("Discarding the supernatant to the waste.")
    
    default_pipette_speed = robot.getSpeedPipette() # Getting robot default pipetting speed
    
    # Setting pipette speed for the supernatant pipetting
    robot.setSpeedPipette(pipette_speed)
    
    counter = 0
    for sample in samples_list:
        removeSupernatant(robot, sample, waste, delay=delay, fast=fast)
        if counter == 0:
            sample_dried_timestamp = time.time()
        counter += 1
    robot.setSpeedPipette(default_pipette_speed) # Resetting speed to the default
    logging.info("Supernatant removal complete.")
    return sample_dried_timestamp

def add80PctEthanol(robot, samples_list, ethanol, volume_list, z_safe=50, delay=1.0):
    robot.pickUpNextTip()
    robot.move(z=z_safe)
    
    counter = 0
    for sample, volume in zip(samples_list, volume_list):
        robot.transferLiquid(ethanol, sample, volume, touch_wall=False, delay=delay)
        if counter == 0:
            ethanol_added_time = time.time()
        counter += 1
    
    robot.move(z=z_safe)
    robot.dumpTipToWaste()
    
    return ethanol_added_time


def ethanolWash(robot, settings, samples_list, EtOH80pct, waste):
    
    # Loading ethanol volumes for the both stages.
    v_ethanol_1st_stage_list = getWashVolume(settings, 1)
    v_ethanol_2nd_stage_list = getWashVolume(settings, 2)
    
    # Loading times for how long to wait for ethanol incubation.
    T_wash_1 = returnProtocolParameter(settings, 'First stage ethanol wash time') * 60.0
    T_wash_2 = returnProtocolParameter(settings, 'Second stage ethanol wash time') * 60.0
    T_dry = returnProtocolParameter(settings, 'Time to dry after ethanol wash') * 60.0
    
    # Delay at the end of the pipetting
    pipetting_delay = returnPipettingDelay(settings)
    
    # Loading settings for the speed of plunger movement for ethanol pipetting.
    ethanol_pipetting_speed = returnEthanolPipettingSpeed(settings)
    max_pipette_speed = returnMaxPipetteSpeed(settings)
    
    # 1st stage ethanol wash
    logging.info("Now performing two ethanol washes.")
    logging.info("Wash-1: Now adding 80% ethanol to all the samples...")
    # Setting the pipette speed for the less viscous ethanol solution
    #robot.setSpeedPipette(ethanol_pipetting_speed)
    timestamp_ethanol_added = add80PctEthanol(robot, samples_list, EtOH80pct, 
                                              v_ethanol_1st_stage_list, delay=pipetting_delay)
    logging.info("Wash-1: 80% ethanol added to all tubes.")
    logging.info("Wash-1: Now incubating the samples for %s seconds..." % (T_wash_1, ))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_1)
    logging.info("Wash-1: Ethanol incubation finished.")
    logging.info("Wash-1: Now removing ethanol from the sample tubes...")
    ts = removeSupernatantAllSamples(robot, samples_list, waste, ethanol_pipetting_speed, 
                                     fast=True, delay=pipetting_delay)
    logging.info("Wash-1: Ethanol removed from all the samples.")
    
    # 2nd stage ethanol wash
    logging.info("Now proceeding to the second ethanol wash.")
    logging.info("Wash-2: Now adding 80% ethanol to all the samples...")
    timestamp_ethanol_added = add80PctEthanol(robot, samples_list, EtOH80pct, 
                                              v_ethanol_2nd_stage_list, delay=pipetting_delay)
    logging.info("Wash-2: 80% ethanol added to all tubes.")
    logging.info("Wash-2: Now incubating the samples for %s seconds..." % (T_wash_2, ))
    waitAfterTimestamp(timestamp_ethanol_added, T_wash_2)
    logging.info("Wash-2: Ethanol incubation finished.")
    logging.info("Wash-2: Now removing ethanol from the sample tubes...")
    timestamp_ethanol_removed = removeSupernatantAllSamples(robot, samples_list, 
                                                            waste, ethanol_pipetting_speed, 
                                                            delay=pipetting_delay)
    logging.info("Wash-2: Ethanol removed from all the samples.")
    logging.info("Ethanol washes complete.")
    #robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed
    
    # Drying ethanol
    logging.info("Now drying the samples from the remaining ethanol for %s minutes..." % ((T_dry/60.0), ))
    waitAfterTimestamp(timestamp_ethanol_removed, T_dry)
    logging.info("Ethanol drying finished.")    


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
def elute(robot, sample, eluent, volume, settings, 
          mix_delay=0.5, mix_times=None, safe_z=50, pipetting_delay=1.0):
    
    # Loading parameters
    if mix_times is None:
        mix_times = int(returnProtocolParameter(settings, 'Elution times to mix'))
    
    robot.moveMagnetsAway(poweroff=True)
    robot.pickUpNextTip()
    robot.move(z=safe_z)
    robot.transferLiquid(eluent, sample, volume, delay=pipetting_delay)
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

def eluteAllSamples(robot, samples_list, eluent, V_eluent_list, settings, 
                    mix_delay=0.5, safe_z=50, pipetting_delay=1.0):
    counter = 0
    for sample, V_eluent in zip(samples_list, V_eluent_list):
        ts = elute(robot, sample, eluent, V_eluent, settings, 
                   mix_delay=mix_delay, safe_z=safe_z, pipetting_delay=pipetting_delay)
        if counter == 0:
            elution_start_timestamp = ts
        counter += 1
    return elution_start_timestamp

def separateEluate(robot, eluate_tube, result_tube, pipette_delay=1.0, source_tube_radius=2, safe_z=50):
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

def separateEluateAllTubes(robot, eluate_list, results_list, pipette_delay=1.0):
    for sample, result in zip(eluate_list, results_list):
        separateEluate(robot, sample, result, pipette_delay=pipette_delay)


def elution(robot, settings, samples_list, result_list, water):
    """
    Call this function in the protocol
    """
    # Loading parameters
    T_pull = returnProtocolParameter(settings, 'Beads pulling time after absorption') * 60.0
    
    v_eluent_list = getEluentVolume(settings)
    
    pipetting_delay = returnPipettingDelay(settings)
    
    eluent_pipetting_speed = returnEluentPipettingSpeed(settings)
    max_pipette_speed = returnMaxPipetteSpeed(settings)
    
    # Adding eluent
    logging.info("Now eluting the DNA from the samples.")
    logging.info("Now adding the eluent to all the samples.")
    # Setting the pipette speed for the eluent solution (usually water)
    robot.setSpeedPipette(eluent_pipetting_speed)
    elution_start_timestamp = eluteAllSamples(robot, samples_list, water, v_eluent_list, 
                                              settings, pipetting_delay=pipetting_delay)
    logging.info("Eluent added to all the samples.")
    logging.info("Now mixing the samples...")
    mixManySamples(robot, samples_list, elution_start_timestamp, settings)
    logging.info("Mixing finished.")
    
    # Pulling beads to the side
    logging.info("Now pulling the beads towards the side of the tubes for %s minutes" % ((T_pull/60.0), ))
    robot.moveMagnetsTowardsTube()
    time.sleep(T_pull)
    logging.info("Beads are now at the side of their tubes.")
    
    # Moving eluate to the results tubes
    logging.info("Now moving the eluates to their fresh tubes...")
    separateEluateAllTubes(robot, samples_list, result_list, pipette_delay=pipetting_delay)
    logging.info("Eluate transfer complete.")
    robot.setSpeedPipette(max_pipette_speed) # Resetting the max pipette speed


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
    v_beads_list = getBeadsVolumesForAllSamples(settings, positions_list)
    v_ethanol_1st_stage_list = getWashVolume(settings, 1)
    v_ethanol_2nd_stage_list = getWashVolume(settings, 2)
    v_eluent_list = getEluentVolume(settings)
    
    pipetting_delay = returnPipettingDelay(settings)
    
    max_pipette_speed = returnMaxPipetteSpeed(settings)
    beads_pipetting_speed = returnBeadsPipettingSpeed(settings)
    ethanol_pipetting_speed = returnEthanolPipettingSpeed(settings)
    eluent_pipetting_speed = returnEluentPipettingSpeed(settings)
    
    T_pull = returnProtocolParameter(settings, 'Beads pulling time after absorption') * 60.0
    T_wash_1 = returnProtocolParameter(settings, 'First stage ethanol wash time') * 60.0
    T_wash_2 = returnProtocolParameter(settings, 'Second stage ethanol wash time') * 60.0
    T_dry = returnProtocolParameter(settings, 'Time to dry after ethanol wash') * 60.0
    T_elute = returnProtocolParameter(settings, 'Elution time') * 60.0
    
    
    logging.info("This is the one-stage magnetic beads purification.")
    logging.info("It will remove any DNA and other molecules of low molecular weight.")
    logging.info("I will purify "+str(len(samples_list))+" samples")
    logging.info("I will use %s uL of magnetic beads to purify." % (v_beads_list, ))
    logging.info("I will elute the resulting DNA with %s uL of eluent" % (v_eluent_list, ))
    
    # Starting the physical protocol
    logging.info("Now adding magnetic beads...")
    timestamp_beads_added = addBeadsToAll(robot, samples_list, v_beads_list, beads, 
                                          pipetting_speed=beads_pipetting_speed, delay=pipetting_delay)
    logging.info("Beads addition complete.")
    logging.info("Now waiting for DNA absorption...")
    
    
    # Extra mixing samples with magnetic beads during the protocol.
    mixManySamples(robot, samples_list, timestamp_beads_added, settings)
    
    # Pulling beads to the side
    logging.info("DNA absorption complete.")
    logging.info("Now pulling the beads towards the side of the tube for %s minutes..." % ((T_pull/60.0), ))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    
    # Removing supernatant (the desired DNA of larger molecular weight is on the beads)
    logging.info("Beads are now on the side of the tube.")
    logging.info("Now removing the supernatant...")
    # Setting the pipette speed for the viscous beads supernatant
    ts = removeSupernatantAllSamples(robot, samples_list, waste, beads_pipetting_speed, 
                                     fast=True, delay=pipetting_delay)
    logging.info("Supernatant removed from all the tubes.")
    
    # Ethanol wash.
    ethanolWash(robot, settings, samples_list, EtOH80pct, waste)

    # Elution
    elution(robot, settings, samples_list, result_list, water)
    
    logging.info("One-stage purification finished.")
    

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
    v_beads_1st_stage_list = getBeadsVolume1stStageAllSamples(settings, positions_1st_stage_list)
    v_beads_2nd_stage_list = getBeadsVolume2ndStageAllSamples(settings, positions_1st_stage_list)
    
    v_ethanol_1st_stage_list = getWashVolume(settings, 1)
    v_ethanol_2nd_stage_list = getWashVolume(settings, 2)
    v_eluent_list = getEluentVolume(settings)

    pipetting_delay = returnPipettingDelay(settings)
    
    max_pipette_speed = returnMaxPipetteSpeed(settings)
    beads_pipetting_speed = returnBeadsPipettingSpeed(settings)
    ethanol_pipetting_speed = returnEthanolPipettingSpeed(settings)
    eluent_pipetting_speed = returnEluentPipettingSpeed(settings)
    
    T_pull = returnProtocolParameter(settings, 'Beads pulling time after absorption') * 60.0
    T_wash_1 = returnProtocolParameter(settings, 'First stage ethanol wash time') * 60.0
    T_wash_2 = returnProtocolParameter(settings, 'Second stage ethanol wash time') * 60.0
    T_dry = returnProtocolParameter(settings, 'Time to dry after ethanol wash') * 60.0
    T_elute = returnProtocolParameter(settings, 'Elution time') * 60.0

    logging.info("This is the two-stage magnetic beads purification.")
    logging.info("It will remove any DNA and other molecules of too low and too high molecular weight.")
    logging.info("I will purify "+str(len(samples_list))+" samples")
    logging.info("I will first use %s uL of magnetic beads for the long DNA cutoff, " % (v_beads_1st_stage_list, ))
    logging.info("and then use %s uL of magnetic beads for the short DNA cutoff, " % (v_beads_2nd_stage_list, ))
    logging.info("I will elute the resulting DNA with %s uL of eluent" % (v_eluent_list, ))
    
    
    # Starting the physical protocol
    
    # First cutoff.
    # --------------------------
    logging.info("------")
    logging.info("Starting the purification.")
    logging.info("------")
    logging.info("Now adding the %s uL of magnetic beads to the corresponding samples for the long DNA cutoff..." % (v_beads_1st_stage_list, ))
    timestamp_beads_added = addBeadsToAll(robot, samples_list, v_beads_1st_stage_list, beads,
                                          pipetting_speed=beads_pipetting_speed, delay=pipetting_delay)
    logging.info("Beads added to the samples.")
    
    logging.info("Now waiting for the DNA absorption...")
    # Extra mixing samples with magnetic beads during the protocol.
    mixManySamples(robot, samples_list, timestamp_beads_added, settings)
    logging.info("DNA absorption finished.")
    
    
    # Pulling beads to the side
    logging.info("Now pulling the beads towards the tube side")
    logging.info("Waiting for %s seconds while the magnets are pulling beads to the side" % (T_pull, ))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    logging.info("Beads are now pulled to the side of the tubes.")
    
    # Transferring to the intermediary tubes
    logging.info("Now transferring the samples to the fresh tubes for the small molecules removal...")
    transferAllSamplesToSecondStage(robot, samples_list, intermediate_list)
    
    
    # After tubes are transferred, moving magnets away.
    robot.moveMagnetsAway(poweroff=True)
    logging.info("Sample transfer complete.")
    
    
    # Second cutoff
    # -------------
    logging.info("Now adding the %s uL of magnetic beads to the samples for the small molecule removal..." % (v_beads_2nd_stage_list, ))
    timestamp_beads_added = addBeadsToAll(robot, intermediate_list, v_beads_2nd_stage_list, beads, 
                                          pipetting_speed=beads_pipetting_speed, delay=pipetting_delay)
    logging.info("Beads added to the samples.")
    
    # Extra mixing samples with magnetic beads during the protocol.
    logging.info("Now waiting for the DNA absorption...")
    mixManySamples(robot, intermediate_list, timestamp_beads_added, settings)
    logging.info("DNA absorption finished.")
    
    # Pulling beads to the side
    logging.info("DNA absorption finished.")
    logging.info("Now pulling the beads towards the tube side")
    logging.info("Waiting for %s seconds while the magnets are pulling beads to the side" % (T_pull, ))
    robot.moveMagnetsTowardsTube(poweroff=True)
    time.sleep(T_pull)
    logging.info("Beads are now pulled to the side of the tubes.")
    
    # Removing supernatant (the desired DNA of larger molecular weight is on the beads)
    ts = removeSupernatantAllSamples(robot, intermediate_list, waste, beads_pipetting_speed, 
                                     fast=True, delay=pipetting_delay)
    
    ethanolWash(robot, settings, intermediate_list, EtOH80pct, waste)
    elution(robot, settings, intermediate_list, result_list, water)
    
    logging.info("Two-stage purification finished.")
    
    
    
    

# Main body
# ===========================================================================================

if __name__ == '__main__':
    logging.info("=================================================================================")
    logging.info("/nThis is the script for purifying DNA mixture by removing any DNA molecules shorter then a certain size.")
    logging.info("I will start from running a few sanity checks")

    # Making sure the argument provided
    if isArgumentPassed():
        settings_file_path = sys.argv[1]   # Getting the settings
        logging.info("Found an argument: %s, OK" % settings_file_path)
    else:
        printHowToUse()
        sys.exit("Script terminated") 

    # Checking whether the samplesheet file exists
    if isSampleSheetExist(settings_file_path):
        logging.info("Checking whether the file %s exists... OK" % settings_file_path)
        # Loading data settings
        settings = loadSettings(settings_file_path)
    else:
        logging.error("Samplesheet not found in the path %s, or can't open that file." % settings_file_path)
        printHowToUse()
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
        f = purify_one_cutoff
    elif stages == 2:
        f = purifyTwoCutoffs
    else:
        logging.error("Wrong Number of Cutoffs provided in the samplesheet.")
        logging.error("This protocol only supports values 1 or 2, however, value %s was provided." % stages)
    
    # This starts actual purification.
    f(ber, settings)

    ber.powerStepperOff('A') # to prevent unnecessary heating. Must be off already, but just in case.
    ber.powerStepperOff()    # Powering off all steppers
    
    ber.close()
    
    