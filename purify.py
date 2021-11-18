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
        self.elution_times_to_mix = int(self.returnProtocolParameter('Elution times to mix'))
        self.absorption_times_to_mix = int(self.returnProtocolParameter('Times to mix while absorbing'))
        self.initial_sample_vol_list = self._returnSampleParameterList('Initial sample volume')
        self.number_of_samples = len(self.initial_sample_vol_list)
        self.positions_to_purify_list = self.positionsToPurify()
        self.positions_2nd_stage_tubes = self.positionsToPurify2ndStage()
        
        self.beads_tube_type = self._getTubeType('Beads')
        self.waste_tube_type = self._getTubeType('Waste')
        self.eluent_tube_type = self._getTubeType('Eluent')
        self.ethanol_tube_type = self._getTubeType('Ethanol')
        
        self.beads_rack_name = self._getRackName('Beads')
        self.waste_rack_name = self._getRackName('Waste')
        self.eluent_rack_name = self._getRackName('Eluent')
        self.ethanol_rack_name = self._getRackName('Ethanol')
        
        self.beads_column_in_rack, self.beads_row_in_rack = self._getTubePositionInRack('Beads')
        self.waste_column_in_rack, self.waste_row_in_rack = self._getTubePositionInRack('Waste')
        self.eluent_column_in_rack, self.eluent_row_in_rack = self._getTubePositionInRack('Eluent')
        self.ethanol_column_in_rack, self.ethanol_row_in_rack = self._getTubePositionInRack('Ethanol')
        
        self.V_beads = self._getReagentVolume('Beads')
        self.V_waste = self._getReagentVolume('Waste')
        self.V_eluent = self._getReagentVolume('Eluent')
        self.V_ethanol = self._getReagentVolume('Ethanol')
        
        self.beads_vol_1st_stage_list = self._getBeadsVolForAllSamples(stage=1)
        # Will get some meaningful data only if cutoffs setting is 2.
        self.beads_vol_2nd_stage_list = self._getBeadsVolForAllSamples(stage=self.cutoffs)
        self.V_beads_list = self.beads_vol_1st_stage_list # Pass 2nd stage list if needed.
        
        self.wash_1_vol_list = self._returnSampleParameterList('First stage ethanol wash volume')
        self.wash_2_vol_list = self._returnSampleParameterList('Second stage ethanol wash volume')
        self.eluent_vol_list = self._returnSampleParameterList('Elution volume')
        
        # Time to wait for different processes (in seconds)
        self.T_pull = self.returnProtocolParameter('Beads pulling time after absorption') * 60.0
        self.T_wash_1 = self.returnProtocolParameter('First stage ethanol wash time') * 60.0
        self.T_wash_2 = self.returnProtocolParameter('Second stage ethanol wash time') * 60.0
        self.T_dry = self.returnProtocolParameter('Time to dry after ethanol wash') * 60.0
        self.T_elute = self.returnProtocolParameter('Elution time') * 60.0
        self.T_absoprtion = self.returnProtocolParameter('DNA absorption time') * 60.0
        
        # Robot geometry settings
        self.z_safe = 50.0  # Height at which it is safe to move at any x,y coordinate.
        
        # Tip settings
        # What to do with the used tip. 'waste' - dump to waste; 'back' - return 
        # to the same place in the tip rack.
        self.used_tip_fate = 'waste' 

        
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
        reagent = reagent.capitalize()
        rack_name = self.returnProtocolParameter(reagent+' tube rack')
        if rack_name == 'samples' or rack_name == 'reagents':
            return rack_name
        else:
            logging.error("_getRackType: settings file has a wrong rack name specified.")
            logging.error("For the reagent '%s', the correct rack name may be 'samples' or 'reagents'" % reagent)
            logging.error("but the name %s was provided." % rack_name)
            return 

    def _getTubeType(self, reagent):
        reagent = reagent.capitalize()
        return self.returnProtocolParameter(reagent+' tube type')

    def _getReagentVolume(self, reagent):
        reagent = reagent.capitalize()
        if reagent == 'Beads':
            param_name = reagent+' initial volume'
        else:
            param_name = reagent+' volume'
        return self.returnProtocolParameter(param_name)

    def _getTubePositionInRack(self, reagent):
        if reagent == 'Beads':
            col = int(self.returnProtocolParameter(reagent+' tube column'))
            row = int(self.returnProtocolParameter(reagent+' tube well'))
        elif reagent == 'Waste' or reagent == 'Eluent' or reagent == 'Ethanol':
            col = 0
            row = int(self.returnProtocolParameter(reagent+' tube position'))
            
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






class items():
    """
    Handles items, such as samples, reagents and intermediate tubes, etc.
    """
    
    def __init__(self, robot, settings):
        self.settings = settings
        self.robot = robot
        
        self.initial_sample_vol_list = self.settings.initial_sample_vol_list
        self.number_of_samples = self.settings.number_of_samples
        self.cutoffs = self.settings.cutoffs
        
        # Initializing samples
        self.samples_list = self.initSamples()
        self.intermediate_list = self.initIntermediate()
        self.result_list = self.initResults()
        # Assign whatever next stage samples would be.
        self.next_stage_tubes_list = self.result_list
        
        self.beads = self.initReagent('Beads')
        self.waste = self.initReagent('Waste')
        self.eluent = self.initReagent('Eluent')
        self.ethanol = self.initReagent('Ethanol')
        
        self.first_sample = self.samples_list[0]
        
    
    def initSamples(self):
        return bl.createSamplesToPurifyList(self.robot, self.initial_sample_vol_list)
        
    def initIntermediate(self):
        if self.cutoffs == 2:
            return bl.createSamplesToPurifyList(self.robot, number_of_tubes=self.number_of_samples,
                        start_from_position=6)
        else:
            return
    
    def initResults(self):
        return bl.createPurifiedSamplesList(self.robot, self.number_of_samples)

    def getRack(self, rack_name, reagent_name):
        if rack_name == 'samples':
            return self.robot.samples_rack
        elif rack_name == 'reagents':
            return self.robot.reagents_rack
        else:
            logging.error("There is no rack with the name '%s', specified for the %s" % (rack_name, reagent_name,))
            return
    
    def initReagent(self, reagent):
        reagent = reagent.capitalize()
        rack_name = self.settings._getRackName(reagent)
        rack = self.getRack(rack_name, reagent)
        tube_type = self.settings._getTubeType(reagent)
        col, row = self.settings._getTubePositionInRack(reagent)
        sample_name = reagent+'_tube'
        v = self.settings._getReagentVolume(reagent)
        tube = bl.createSample(tube_type, sample_name, rack, col, row, v)
        return tube

    def samplesToIntermediate(self):
        # The logic behind the "samples":
        # A protocol has many tubes; among those are:
        # - The tubes with the initial, "dirty" sample
        # - Optionally the "intermediate" tubes, where the sample is transferred between stages
        # - Results tubes
        # Protocol functions will always work with "samples" only (so I don't have to 
        # specify to each function which sample to go to, and they are the same regardless on
        # whether the sample or intermediate is used.)
        # Therefore, the class has the ability to reassign "samples" to the new tubes series.
        
        self.samples_list = self.intermediate_list
        




class protocol():
    def __init__(self, robot, settings):
        self.robot = robot
        self.settings = settings
        self.tubes = items(self.robot, self.settings)
        # Used in different functions to measure the time passed since last operation.
        # Example: need to wait five minutes since the start of the operation.
        self.timestamp = time.time()    # Initializing only.
        self.step = 'not started'
        self.incubation_time = 0  # Incubation time (in seconds)
        self.default_pipette_speed = self.robot.getSpeedPipette()

    
    def moveToSafe(self):
        self.robot.move(self.settings.z_safe)
    
    def dumpTip(self):
        """
        Decides what to do with the used tip.
        """
        self.moveToSafe()
        if self.settings.used_tip_fate == 'waste':
            self.robot.dumpTipToWaste()          # To the waste
        elif self.settings.used_tip_fate == 'back':
            self.robot.returnTipBack()           # Back to the rack, so it can be reused later
        else:
            logging.warning("Wrong tip fate provided. Dumping the tip to waste.")
            self.robot.dumpTipToWaste()
        self.moveToSafe()
    
    def pickUpTip(self):
        if self.robot.tip_attached == 0:
            self.moveToSafe()
            self.robot.pickUpNextTip()                   # Picking up next tip
            self.moveToSafe()
    
    def mix(self, sample):
        self.moveToSafe()
        self.robot.mixByScript(sample)
        self.moveToSafe()
    
    def mixManySamples(self):
        logging.info("Now mixing the samples...")
        for sample in self.tubes.samples_list:
            self.pickUpTip()
            self.mix(sample)
            self.dumpTip()
        logging.info("Mixing finished.")
    
    def pullBeads(self, pull_time):
        logging.info("Now pulling the beads towards the side of the tubes for %s minutes" % ((pull_time/60.0), ))
        self.robot.moveMagnetsTowardsTube()
        time.sleep(pull_time)
        logging.info("Beads are now at the side of their tubes.")
    
    
    def getDelayBetweenActions(self, full_delay, number_of_actions):
        if number_of_actions <= -1:
            return full_delay
        else:
            return full_delay / (number_of_actions + 1)
        
    def getAlreadyWaitedTime(self):
        return time.time() - self.timestamp
    
    def autoUpdateIncubationTime(self):
        self.incubation_time = self.incubation_time - self.getAlreadyWaitedTime()
        if self.incubation_time < 0:
            self.incubation_time = 0
    
    def incubate(self, times_to_mix=0):
        """
        Waits for the certain time with an option to mix the sample (depending on the settings).
        """
        incubation_time_min = self.incubation_time/60.0
        logging.info("Now incubating the samples for %s minutes." % incubation_time_min)
        logging.info("During incubation, I will mix each sample for %s times." % times_to_mix)
        while self.incubation_time > 0 and times_to_mix >= 0:
            delay_between_mixes = self.getDelayBetweenActions(self.incubation_time, times_to_mix)
            wait_time = delay_between_mixes - self.getAlreadyWaitedTime()
            if wait_time < 0:
                wait_time = 0
            time.sleep(wait_time)   # Incubating
            # After incubation is done
            self.autoUpdateIncubationTime() # Updating the incubation time
            self.timestamp = time.time()    # Updating the timestamp
            if times_to_mix > 0:
                self.mixManySamples()       # If protocol asks to mix, do so.
            times_to_mix = times_to_mix - 1 # One less time to mix left.
        logging.info("Incubation finished.")
        
    def transferLiquid(self, source, dest, v=None, touch_wall=True):
        dry_tube = False
        # If volume is not provided, will pipette all the volume present in the source
        if v is None:
            v = source.getVolume()
            dry_tube = True
        self.robot.transferLiquid(source, dest, v, dry_tube=dry_tube, safe_z=self.settings.z_safe,
                delay=self.settings.pipetting_delay, touch_wall=touch_wall)
    
    def transferLiquidSterile(self, source, dest, v=None, touch_wall=True):
        self.pickUpTip()
        self.transferLiquid(source, dest, v=v, touch_wall=touch_wall)    
        self.dumpTip()
        
    def transferLiquidManyTubes(self, sources, destinations, v_list=None, pipette_speed=None, 
                    sterile=True, touch_wall=True):
        # Changing the pipetting speed if provided. Otherwise using default.
        if pipette_speed is not None:
            self.robot.setSpeedPipette(pipette_speed)
        # If volume list is not provided, generating list of None; meaning 
        # all the liquid from the source will be transferred to destination.
        if v_list is None:
            v_list = [None for x in sources]
        for s, d, v in zip(sources, destinations, v_list):
            if sterile:
                self.transferLiquidSterile(s, d, v, touch_wall=touch_wall)
            else:
                self.transferLiquid(s, d, v, touch_wall=touch_wall)
        self.robot.setSpeedPipette(self.default_pipette_speed)


    def addBeads(self):
        logging.info("Now adding magnetic beads...")
        self.robot.moveMagnetsAway(poweroff=True)    # Magnets away from the tubes
        self.pickUpTip()
        self.mix(self.tubes.beads)
        
        # Transferring beads suspension from beads tubes to the sample tubes.
        # Using the same tip. Not touching sample tubes.
        destinations = self.tubes.samples_list
        sources = [self.tubes.beads for x in destinations]
        self.transferLiquidManyTubes(sources, destinations, self.settings.V_beads_list, touch_wall=False,
                sterile=False, pipette_speed=self.settings.beads_pipetting_speed)
        logging.info("Beads addition complete.")
        
        # Mixing beads suspension with the sample
        logging.info("Now mixing the beads with the samples, prior to absorption.")
        self.timestamp = time.time()
        self.mixManySamples()
        logging.info("Mixing complete.")
        

    def absorbDnaOntoBeads(self):
        self.addBeads()
        self.incubate(times_to_mix=self.settings.absorption_times_to_mix)
        self.pullBeads(pull_time=self.settings.T_pull)
        
    
    def transferSamplesToSecondStage(self):
        self.transferLiquidManyTubes(self.tubes.samples_list, self.tubes.intermediate_list,
                    pipette_speed=self.settings.beads_pipetting_speed)
        # Now the samples are in the intermediate tubes.
        self.tubes.samples_list = self.tubes.intermediate_list
        self.settings.V_beads_list = self.settings.beads_vol_2nd_stage_list


    def removeSupernatant(self, pipette_speed=None):
        logging.info("Discarding the supernatant to the waste.")
        sources = self.tubes.samples_list
        destinations = [self.tubes.waste for x in sources]
        self.timestamp = time.time()
        self.transferLiquidManyTubes(sources, destinations, touch_wall=False,
                pipette_speed=pipette_speed)
        logging.info("Supernatant removal complete.")
    
    
    def addEthanol(self, vol_list):
        self.pickUpTip()
        self.timestamp = time.time()
        destinations = self.tubes.samples_list
        sources = [self.tubes.ethanol for x in destinations]
        self.transferLiquidManyTubes(sources, destinations, vol_list, touch_wall=False, sterile=False,
                pipette_speed=self.settings.ethanol_pipetting_speed)
        self.dumpTip()
    
    
    def ethanolWashStage(self, wash, wait_time):
        self.incubation_time = wait_time    # Setting incubation time for ethanol wash.
        logging.info("Wash-%s: Now adding 80 percent ethanol to all the samples..." % (wash,))
        self.addEthanol(self.settings.wash_1_vol_list)
        logging.info("Wash-%s: 80 percent ethanol added to all tubes." % wash)
        logging.info("Wash-%s: Now incubating the samples for %s seconds..." % (wash, wait_time))
        self.incubate()
        logging.info("Wash-%s: Ethanol incubation finished." % wash)
        logging.info("Wash-%s: Now removing ethanol from the sample tubes..." % wash)
        self.removeSupernatant(pipette_speed=self.settings.ethanol_pipetting_speed)
        logging.info("Wash-%s: Ethanol removed from all the samples." % wash)
        
    
    def ethanolWash(self):
        logging.info("Now performing two ethanol washes.")
        self.ethanolWashStage(1, self.settings.T_wash_1)
        self.ethanolWashStage(2, self.settings.T_wash_2)
        logging.info("Ethanol washes complete.")
        
        logging.info("Now drying the samples from the remaining ethanol for %s minutes..." % ((self.settings.T_dry/60.0), ))
        self.incubation_time = self.settings.T_dry
        self.incubate()
        logging.info("Ethanol drying finished.")
    
    
    def washingBeadsFromWallDuringElution(self, sample, dx, dz, v, delay):
        z_top = sample.getSampleTopAbsZ(added_length=self.robot._calcExtraLength())
        z_curr = z_top + dz
        self.robot.move(z=z_curr)
        self.robot.moveAxisDelta('X', dx)
        self.robot.movePipetteToVolume(v)
        time.sleep(delay)
    
    def elutionMix(self, sample, volume=None, how='low'):
        """
        Parameter "how" can be either 'low' or 'high'
        """
        # Uptaking liquid
        if volume is None:
            volume = sample.getVolume()
        self.robot.uptakeLiquid(sample, volume, lag_vol=5)
        time.sleep(self.settings.pipetting_delay)
        
        # Washing steps, releasing liquid while moving along the wall
        # TODO: Replace those by establishing a "move" command which simultaneously 
        # moves X, Z and A coordinates.
        if how == 'low':
            dispense_vol = volume / 4.0
            dispense_delay = self.settings.pipetting_delay / 4.0
            self.washingBeadsFromWallDuringElution(sample, 3.0, 24.0, dispense_vol, dispense_delay)
            self.washingBeadsFromWallDuringElution(sample, 0.0, 28.0, 2*dispense_vol, dispense_delay)
            self.washingBeadsFromWallDuringElution(sample, -0.629, 32.0, 3*dispense_vol, dispense_delay)
            self.washingBeadsFromWallDuringElution(sample, -0.629, 36.0, 4*dispense_vol, dispense_delay)
        else:
            self.washingBeadsFromWallDuringElution(sample, 3.4, 5.0, volume+50, 
                        self.settings.pipetting_delay)
        
        # Moving back to center, above liquid
        x, y = sample.getCenterXY()
        self.robot.move(x=x, y=y)
        z_curr = sample.calcAbsLiquidLevelFromVol(volume+100, added_length=self.robot._calcExtraLength())
        self.robot.move(z=z_curr)
        
        # Pipetting out all liquid, returning plunger back to 0.
        self.robot.movePipetteToVolume(volume+50)
        time.sleep(self.settings.pipetting_delay)
        self.robot.movePipetteToVolume(0)    
    
    
    def addEluent(self, sample, eluent, volume):
        self.robot.moveMagnetsAway(poweroff=True)
        self.pickUpTip()
        self.transferLiquid(eluent, sample, volume)
        
        for i in range(self.settings.elution_times_to_mix):
            self.elutionMix(sample, how='high')
            self.elutionMix(sample, how='high')
            self.elutionMix(sample, how='low')
        self.elutionMix(sample, how='low')
        self.elutionMix(sample, how='low')
        
        self.dumpTip()
        
    def addEluentToAll(self):
        self.timestamp = time.time()
        logging.info("Now adding the eluent to all the samples.")
        for sample, v_eluent in zip(self.tubes.samples_list, self.settings.eluent_vol_list):
            self.addEluent(sample, self.tubes.eluent, v_eluent)
        logging.info("Eluent added to all the samples.")
    
    def elution(self):
        logging.info("Now eluting the DNA from the samples.")
        # Setting the pipette speed for the eluent solution (usually water)
        self.robot.setSpeedPipette(self.settings.eluent_pipetting_speed)
        # Adding eluent
        self.addEluentToAll()
        self.incubation_time = self.settings.T_elute
        self.incubate(times_to_mix=self.settings.elution_times_to_mix)
        self.robot.setSpeedPipette(self.settings.default_pipette_speed) # Resetting the max pipette speed
        
        self.pullBeads(self.settings.T_pull)
        
        # Moving eluate to the results tubes
        logging.info("Now moving the eluates to their fresh tubes...")
        self.transferLiquidManyTubes(self.tubes.samples_list, self.tubes.result_list, 
                pipette_speed=self.settings.eluent_pipetting_speed)
        logging.info("Eluate transfer complete.")


    def purify(self):
        logging.info("This is the %s-stage magnetic beads purification." % self.settings.cutoffs)
        
        self.absorbDnaOntoBeads()   # First stage
        
        # Checking if this is a two-stage cutoff
        if self.settings.cutoffs == 2:
            self.transferSamplesToSecondStage()
            self.absorbDnaOntoBeads()   # Second stage
        
        self.removeSupernatant(pipette_speed=self.settings.beads_pipetting_speed)
        self.ethanolWash()
        self.elution()
        
        logging.info("%s-stage purification finished." % self.settings.cutoffs)
        
        


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

def getSettingsPathFromArg():
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
        s = settings(settings_file_path)
        return settings_file_path
    else:
        logging.error("Samplesheet not found in the path %s, or can't open that file." % settings_file_path)
        printHowToUse()
        sys.exit("Script terminated") 
        

# Main body
# ===========================================================================================

if __name__ == '__main__':
    logging.info("=================================================================================")
    logging.info("/nThis is the script for purifying DNA mixture by removing any DNA molecules shorter then a certain size.")
    logging.info("I will start from running a few sanity checks")

    settings_file_path = getSettingsPathFromArg()
    s = settings(settings_file_path)
    
    # Initializing  the robot and homing it.
    ber = bl.robot(cartesian_port_name=s.cartesian_port, loadcell_port_name=s.load_cell_port, 
            tips_type=s.tip_rack_type)
    ber.home()
    
    p = protocol(ber, s)
    # This starts an actual purification.
    p.purify()

    ber.powerStepperOff('A') # to prevent unnecessary heating. Must be off already, but just in case.
    ber.powerStepperOff()    # Powering off all steppers
    
    ber.close()
    
    