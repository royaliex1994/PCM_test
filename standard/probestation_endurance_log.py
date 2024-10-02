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

def cycle_waveform(V_RESET,V_SET):
    # Calculate waveforms
    sample_rate = awg.sampling_rate
    RESET = create_waveform(2e-9, 50e-9, 2e-9, V_RESET, 5e-7, sample_rate)
    SET = create_waveform(1e-6, 2e-7, 1e-6, V_SET, 5e-7, sample_rate)

    # Write waveforms
    awg.waveforms["SET"] = SET
    awg.waveforms["RESET"] = RESET

    sequence_config = [
        {"number": 1, "waveform": "SET"},
        {"number": 2, "waveform": "RESET"},
    ]

    setup_sequences(awg, sequence_config)

    # Set run mode to single Burst
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
    'Timebase Scale': '1e-6',
    'Timebase Position': '3e-6',  
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 1},
    'Channel 1 Scale': 0.02,  
    'Channel 1 Offset': 0.07,
    'Channel 2 Scale': 0.5,  
    'Channel 2 Offset': 1.7,
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
    'Timebase Scale': '1e-6',
    'Timebase Position': '3e-6',  
    'Trigger Source': 'CHANNEL2',
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 0.7},
    'Channel 1 Scale': 0.02,  
    'Channel 1 Offset': 0.06,
    'Channel 2 Scale': 0.5,  
    'Channel 2 Offset': 1.5,
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
    "stop_voltage": "2",
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
File_SampleName = "2-DIE-44"
File_PadName = "D1-3"
Sub_folder = '1th_endurance'
print(Sub_folder)

Record_ext = '_endurance.txt'

if Sub_folder == '0':
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/'
else:
    File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/' + Sub_folder + '/'

if not os.path.exists(File_Path):
    os.makedirs(File_Path)

Record_file = File_Root + '/' + File_SampleName + '/' + File_PadName + Record_ext

###################### Basic parameters ###########################

V_RESET = 1.8
V_SET = 1.2
V_sweep = 2
V_read = 0.1
rise_time = 2e-9
fall_time = 2e-9
delay = 1e-6
sample_rate = awg.sampling_rate
cycle_num = 8 #10e{cycle_num}
cycle_points = 200

cycles, step = generate_logscale_integers(cycle_num,cycle_points)

# Write-verify condition
LRS_lim = 1e4
HRS_lim = 1.0e6

######################## Measurement ###############################

# initialization
smu_sweep_params['stop_voltage'] = V_sweep
measure_with_smu(smu, esp32, smu_sweep_params, generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))

#####################################################################

# read
R_read = measure_with_smu(smu, esp32, smu_read_params, generate_filename(f'read_after_sweep_{V_sweep}V', File_Path, '.npz'))
print('Resistance after sweep =', R_read)
record_resistance(Record_file, V_sweep, R_read, 'after_sweep')

#define initial waveform
cycle_waveform(V_RESET,V_SET)

#####################################################################
# setup relay
relays(esp32, 'switch')
time.sleep(1)

for jj, ii in enumerate(step):

    # SET
    # define SET waveform
    sequence_config = [{"number": 1, "waveform": "SET"}]
    setup_sequences(awg, sequence_config)
    awg.burst_count = int(1)
    # setup oscilloscope
    setup_oscilloscope(scope, SET_settings)

    # setup relay
    relays(esp32, 'switch')
    time.sleep(0.5)

    # Output and Run
    awg.write("OUTPut1:STATe 1")
    awg.enabled = True

    # waiting for trigger:
    time_0 =trigger(scope, awg)
    times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
    # plot_waveform(times,voltages)
    np.savez_compressed(generate_filename(f'SET_{V_SET}V_{cycles[jj]}', File_Path, '.npz'), times_v=times_v,
                        voltages_v=voltages_v, times_i=times_i, voltages_i=voltages_i)

    #####################################################################

    # read
    R_read = measure_with_smu(smu, esp32, smu_read_params,
                              generate_filename(f'read_after_SET_{V_SET}V', File_Path, '.npz'))
    print('Resistance after SET =', R_read)
    record_resistance(Record_file, V_SET, R_read, f'after_SET_{cycles[jj]}')

    # RESET
    HRS = 1e1
    increase_num = 0
    print(f'V_RESET:{V_RESET}')
    while HRS < HRS_lim:
        if increase_num != 0:
            # initialization
            measure_with_smu(smu, esp32, smu_sweep_params,
                             generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))
            time.sleep(0.1)

        RESET = create_waveform(rise_time, 50e-9, fall_time, V_RESET, delay, sample_rate)
        awg.waveforms["RESET"] = RESET
        sequence_config = [{"number": 1, "waveform": "RESET"}]
        setup_sequences(awg, sequence_config)
        awg.burst_count = int(1)

        # setup oscilloscope
        RESET_settings['Channel 1 Scale'] = adjust_oscilloscope_scale(V_RESET * 0.02, "voltage")
        RESET_settings['Channel 1 Offset'] = adjust_oscilloscope_scale(V_RESET * 0.02, "voltage") * 2.8
        RESET_settings['Channel 2 Scale'] = adjust_oscilloscope_scale(V_RESET * 0.33, "voltage")
        RESET_settings['Channel 2 Offset'] = adjust_oscilloscope_scale(V_RESET * 0.33, "voltage") * 3
        RESET_settings['Trigger Level']['Level'] = V_RESET * 0.7
        setup_oscilloscope(scope, RESET_settings)

        # setup relay
        relays(esp32, 'switch')
        time.sleep(0.5)

        # Output and Run
        awg.write("OUTPut1:STATe 1")
        awg.enabled = True

        # waiting for trigger:
        time_0 =trigger(scope, awg)
        times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
        # plot_waveform(times,voltages)
        np.savez_compressed(generate_filename(f'RESET_{V_RESET}V_{cycles[jj]}', File_Path, '.npz'), times_v=times_v,
                            voltages_v=voltages_v, times_i=times_i, voltages_i=voltages_i)

        # read
        R_read = measure_with_smu(smu, esp32, smu_read_params,
                                  generate_filename(f'read_after_RESET_{V_RESET}V_{cycles[jj]}', File_Path, '.npz'))
        print('Resistance after RESET =', R_read)
        record_resistance(Record_file, V_RESET, R_read, f'after_RESET_{cycles[jj]}')
        HRS = R_read
        
        if HRS < HRS_lim:    
            V_RESET += 0.01
            increase_num += 1

        if V_RESET > 2.1:
            V_RESET = 2.1
            break

    #cycle
    if ii !=0:
        relays(esp32, 'switch')
        time.sleep(1)

        cycle_waveform(V_RESET,V_SET)
        setup_oscilloscope(scope, RESET_settings)
        scope.write('RUN')
        time.sleep(1)
        awg.burst_count = int(ii)
        # Output and Run
        awg.write("OUTPut1:STATe 1")
        awg.enabled = True
        print(f'wait for {ii * 6e-6 + 1}sec')

        trigger_endurance(scope, awg)

        time.sleep(ii * 6e-6 + 1)
        awg.enabled = False
        awg.write("OUTPut1:STATe 0")  # Ensure AWG is disabled

#Last run

# SET
# define SET waveform
sequence_config = [{"number": 1, "waveform": "SET"}]
setup_sequences(awg, sequence_config)
awg.burst_count = int(1)
# setup oscilloscope
setup_oscilloscope(scope, SET_settings)

# setup relay
relays(esp32, 'switch')
time.sleep(0.5)

# Output and Run
awg.write("OUTPut1:STATe 1")
awg.enabled = True

# waiting for trigger:
time_0 =trigger(scope, awg)
times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
# plot_waveform(times,voltages)
np.savez_compressed(generate_filename(f'SET_{V_SET}V_{cycles[-1]}', File_Path, '.npz'), times_v=times_v,
                    voltages_v=voltages_v, times_i=times_i, voltages_i=voltages_i)

#####################################################################

# read
R_read = measure_with_smu(smu, esp32, smu_read_params,
                          generate_filename(f'read_after_SET_{V_SET}V_{cycles[-1]}', File_Path, '.npz'))
print('Resistance after SET =', R_read)
record_resistance(Record_file, V_SET, R_read, f'after_SET_{cycles[-1]}')

# RESET
HRS = 1e1
increase_num = 0
while HRS < HRS_lim:
    if increase_num != 0:
        # initialization
        measure_with_smu(smu, esp32, smu_sweep_params,
                         generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))
        time.sleep(0.1)

    RESET = create_waveform(rise_time, 50e-9, fall_time, V_RESET, delay, sample_rate)
    awg.waveforms["RESET"] = RESET
    sequence_config = [{"number": 1, "waveform": "RESET"}]
    setup_sequences(awg, sequence_config)
    awg.burst_count = int(1)

    # setup oscilloscope
    setup_oscilloscope(scope, RESET_settings)

    # setup relay
    relays(esp32, 'switch')
    time.sleep(0.5)

    # Output and Run
    awg.write("OUTPut1:STATe 1")
    awg.enabled = True

    # waiting for trigger:
    time_0 =trigger(scope, awg)
    times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
    # plot_waveform(times,voltages)
    np.savez_compressed(generate_filename(f'RESET_{V_RESET}V_{cycles[-1]}', File_Path, '.npz'), times_v=times_v,
                        voltages_v=voltages_v, times_i=times_i, voltages_i=voltages_i)

    # read
    R_read = measure_with_smu(smu, esp32, smu_read_params,
                              generate_filename(f'read_after_RESET_{V_RESET}V_{cycles[-1]}', File_Path, '.npz'))
    print('Resistance after RESET =', R_read)
    record_resistance(Record_file, V_RESET, R_read, f'after_RESET_{cycles[-1]}')
    HRS = R_read

    V_RESET += 0.05
    increase_num += 1

    if V_RESET > 3:
        V_RESET = 3
        break


#plot_waveform(times, voltages)
awg.enabled = False
awg.write("OUTPut1:STATe 0")
