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
------------------------     Setting Waveform      ------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''


# Calculate waveforms
sample_rate = awg.sampling_rate
TRI = create_waveform(1e-6, 1e-8, 1e-6, 0.2, 1e-6, sample_rate)

# Write waveforms
awg.waveforms["TRI"] = TRI

sequence_config = [{"number": 1, "waveform": "TRI"}]

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
------------------------     Setting oscilloscope      --------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

RESET_settings = {
    'Acquisition Type': 'NORM',
    'Channel 1 Probe': 1,
    'Channel 2 Probe': 10,
    'Timebase Scale': '5e-7',
    'Timebase Position': '6e-7',  
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 0.5},
    'Channel 1 Scale': 0.02,  
    'Channel 1 Offset': 0.06,
    'Channel 2 Scale': 0.2,  
    'Channel 2 Offset': 0.65,
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
    'Timebase Position': '2e-3',  # 20 microseconds
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 0.5},
    'Channel 1 Scale': 0.02,  # 50 mV per division
    'Channel 1 Offset': 0.06,  # 100 mV offset
    'Channel 2 Scale': 0.2,  
    'Channel 2 Offset': 0.65,
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
------------------------     Setting Measurement      ---------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------
---------------------------------------------------------------------------'''

File_Root = "C:/Users/lisaadmin/Desktop/data/y.zhou"
File_SampleName = "3-DIE-08"
File_PadName = "C2-1"
Sub_folder = 'OTS'
print(Sub_folder)

Record_ext = '.txt'

if Sub_folder == '0':
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/'
else:
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/' + Sub_folder + '/'

if not os.path.exists(File_Path):
    os.makedirs(File_Path)

Record_file = File_Root + '/' + File_SampleName + '/' + File_PadName + Record_ext

###################### Basic parameters ###########################

V_RESET = 0.6
V_sweep = 5
V_read = 0.1
rise_time = 2e-9
fall_time = 2e-9
delay = 1e-6

# Write-verify condition
LRS_lim = 2e3
HRS_lim = 1e6

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
# setup relay
relays(esp32, 'switch')
time.sleep(1)

for i in range(10):
    setup_oscilloscope(scope, RESET_settings)
    time.sleep(1)
    awg.burst_count = int(1)
    # Output and Run
    awg.write("OUTPut1:STATe 1")
    awg.enabled = True
    
    trigger(scope, awg)
        
    # 获取波形数据

    times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
    np.savez_compressed(generate_filename(f'OTS_{1000*i+1}V', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)
    

    # 99 cycles
    setup_oscilloscope(scope,SET_settings)
    time.sleep(1)
    awg.burst_count = int(999)
    # Output and Run
    awg.write("OUTPut1:STATe 1")
    awg.enabled = True
    
    trigger(scope, awg)
        
    # 获取波形数据

    times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
    np.savez_compressed(generate_filename(f'OTS_{1000*i+999}V', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)
    print("Data saved to 'waveform_data.csv'.")
#plot_waveform(times, voltages)
awg.enabled = False
awg.write("OUTPut1:STATe 0")


