from PET import *



'''------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
------------------------     Connect Instruments      ---------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

awg = connect_to_awg('169.254.42.153')
scope = connect_to_scope('USB0::0x0957::0x179B::MY56273412::0::INSTR')
smu = connect_to_smu('USB0::0x0957::0x8B18::MY51141455::0::INSTR')
esp32 = connect_to_esp32('COM4', 115200)
time.sleep(1)

'''------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
------------------------     Setting oscilloscope      --------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

RESET_settings = {
    'Acquisition Type': 'NORM',
    'Channel 1 Probe': 1,
    'Channel 2 Probe': 10,
    'Timebase Scale': '2e-8',
    'Timebase Position': '4e-8',  
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 1},
    'Channel 1 Scale': 0.1,  
    'Channel 1 Offset': 0.3,
    'Channel 2 Scale': 1,  
    'Channel 2 Offset': 3,
    'Waveform Source': 'CHANNEL1',
    'Waveform Byte Order': 'LSBFirst',
    'Waveform Format': 'WORD',
    'Waveform Points Mode': 'RAW',
    'Waveform Points': 800000,
    'Trigger Mode': ':SINGle',
    'Wait for Operation Complete': '*WAI'
}

SET_settings = {
    'Acquisition Type': 'NORM',
    'Channel 1 Probe': 1,
    'Channel 2 Probe': 10,
    'Timebase Scale': '5e-4',  # 5 microseconds per division
    'Timebase Position': '5e-4',  # 20 microseconds
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 1},
    'Channel 1 Scale': 0.2,  # 50 mV per division
    'Channel 1 Offset': 1,  # 100 mV offset
    'Channel 2 Scale': 1,  
    'Channel 2 Offset': 3,
    'Waveform Source': 'CHANNEL1',
    'Waveform Byte Order': 'LSBFirst',
    'Waveform Format': 'WORD',
    'Waveform Points Mode': 'RAW',
    'Waveform Points': 800000,
    'Trigger Mode': ':SINGle',
    'Wait for Operation Complete': '*WAI'
}

'''------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
------------------------     Setting SMU     ------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

smu_read_params = {
    "start_voltage": "0",
    "stop_voltage": "0.1",
    "NPLC": "1",
    "points": "51",
    "compliance_current": "0.01",
    "sweep_direction": "DOUB"
}

smu_sweep_params = {
    "start_voltage": "0",
    "stop_voltage": "10",
    "NPLC": "1",
    "points": "51",
    "compliance_current": "0.01",
    "sweep_direction": "DOUB"
}

'''------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
--------------------     Setting default Waveform      --------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

# Calculate waveforms
sample_rate = awg.sampling_rate
RESET = create_waveform(2e-9, 1e-6, 2e-9, 1, 1e-6, sample_rate)
SET = create_waveform(2e-9, 5e-8, 2e-9, 0.6, 1e-6, sample_rate)
READ = create_waveform(2e-6, 2e-6, 2e-6, 0.3, 1e-6, sample_rate)
TRI = create_waveform(1e-6, 1e-8, 1e-6, 0.2, 1e-6, sample_rate)

# Write waveforms
awg.waveforms["RESET"] = RESET
awg.waveforms["SET"] = SET
awg.waveforms["READ"] = READ
awg.waveforms["TRI"] = TRI

sequence_config = [
    {"number": 1, "waveform": "READ"},
    {"number": 2, "waveform": "RESET"},
    {"number": 3, "waveform": "READ"},
    {"number": 4, "waveform": "SET"},
    {"number": 5, "waveform": "READ"}
]

setup_sequences(awg, sequence_config)

# Set run mode to single Burst
awg.write("MARK:MODE AUTO")
awg.setting_ch[1].enable = True
awg.run_mode = "BURST"
awg.trigger_source = 'MAN'  # Manual
awg.burst_count = int(1)

'''------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
--------------------     Setting PTE Measurement      ---------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

###################### sample info ###########################
File_Root = "C:/Users/lisaadmin/Desktop/data/test"
File_SampleName = "3-DIE-25"
File_PadName = "A2-1"
Sub_folder = '0'

Record_ext = '_1.txt'

if Sub_folder == '0':
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/'
else:
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/' + Sub_folder + '/'

if not os.path.exists(File_Path):
    os.makedirs(File_Path)

Record_file = File_Root + '/' + File_SampleName + '/' + File_PadName + Record_ext

###################### Basic parameters ###########################

V_RESET = 2.5
V_sweep = 10
V_read = 0.1
rise_time = 2e-9
fall_time = 2e-9
delay = 1e-6


######################## Measurement ###############################

# initialization
smu_sweep_params['stop_voltage'] = V_sweep
measure_with_smu(smu, esp32, smu_sweep_params, generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))

#####################################################################

# read
R_read = measure_with_smu(smu, esp32, smu_read_params, generate_filename(f'read_after_sweep_{V_sweep}V', File_Path, '.npz'))
print('Resistance after sweep =', R_read)
record_resistance(Record_file, V_sweep, R_read, 'after_sweep')


#####################################################################

# Analog switch

# RESET
sequence_config = [
    {"number": 1, "waveform": "RESET"}
    ]
setup_sequences(awg, sequence_config)

# setup oscilloscope
setup_oscilloscope(scope, RESET_settings)

# setup relay
relays(esp32, 'switch')
time.sleep(0.1)

# Output and Run
awg.write("OUTPut1:STATe 1")
awg.enabled = True

# waiting for trigger:
trigger(scope, awg)
times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
np.savez_compressed(generate_filename(f'RESET_{V_RESET}V', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)

#####################################################################
time.sleep(1)
# read
R_read = measure_with_smu(smu, esp32, smu_read_params,
                 generate_filename(f'read_after_RESET_{V_RESET}V', File_Path, '.npz'))
print(f'Resistance after RESET =', R_read)
record_resistance(Record_file, V_RESET, R_read, f'after_RESET')



#RESET analog
RESET = create_waveform(2e-9, 10e-9, 2e-9, 1, 1e-6, sample_rate)
awg.waveforms["RESET"] = RESET
sequence_config = [{"number": 1, "waveform": "RESET"}]
setup_sequences(awg, sequence_config)

# setup oscilloscope
RESET_settings['Timebase Scale'] =1e-8
RESET_settings['Channel 1 Scale'] =0.05
RESET_settings['Channel 1 Offset'] =0.15


##for i in range(1):
##    # setup oscilloscope
##    setup_oscilloscope(scope, RESET_settings)
##
##    # setup relay
##    relays(esp32, 'switch')
##    time.sleep(0.1)
##
##    # Output and Run
##    awg.write("OUTPut1:STATe 1")
##    awg.enabled = True
##
##    # waiting for trigger:
##    trigger(scope, awg)
##    times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
##    np.savez_compressed(generate_filename(f'RESET_{V_RESET}V', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)
##
##    #####################################################################
##
##    # read
##    R_read = measure_with_smu(smu, esp32, smu_read_params,
##                     generate_filename(f'read_after_RESET_{V_RESET}V', File_Path, '.npz'))
##    print(f'Resistance after RESET {i+1} =', R_read)
##    record_resistance(Record_file, V_RESET, R_read, f'after_RESET_{i+1}')


relays(esp32,'off')
