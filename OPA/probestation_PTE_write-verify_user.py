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
    'Trigger Level': {'Channel': 'CHANNEL2', 'Level': 0.5},
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
    "NPLC": "0.1",
    "points": "51",
    "compliance_current": "0.01",
    "sweep_direction": "DOUB"
}

smu_sweep_params = {
    "start_voltage": "0",
    "stop_voltage": "5",
    "NPLC": "0.1",
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
RESET = create_waveform(2e-9, 5e-8, 2e-9, 2, 1e-6, sample_rate)
SET = create_waveform(2e-9, 5e-8, 2e-9, 0.8, 1e-6, sample_rate)
READ = create_waveform(2e-6, 2e-6, 2e-6, 0.3, 1e-6, sample_rate)

# Write waveforms
awg.waveforms["RESET"] = RESET
awg.waveforms["SET"] = SET
awg.waveforms["READ"] = READ

sequence_config = [
    {"number": 1, "waveform": "READ"},
    {"number": 2, "waveform": "RESET"},
    {"number": 3, "waveform": "READ"},
    {"number": 4, "waveform": "SET"},
    {"number": 5, "waveform": "READ"}
]

setup_sequences(awg, sequence_config)

# Set run mode to single Burst
# awg.write("MARK:MODE AUTO")
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

###################### Basic parameters ###########################

V_RESET_0 = 0.8
V_sweep = 10
V_read = 0.1
T_RESET = 5e-8
rise_time = 2e-9
fall_time = 2e-9
delay = 1e-6

for i in range(25):
    ###################### sample info ###########################
    File_Root = "C:/Users/lisaadmin/Desktop/data/test"
    File_SampleName = "3-DIE-11_OPA"
    File_PadName = "G1-3"
    Sub_folder = str(i+3) + 'th_SET'
    print(Sub_folder)

    Record_ext = '_OPA.txt'

    if Sub_folder == '0':
        File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/'
    else:
        File_Path = File_Root + '/' + File_SampleName + '/' + File_PadName + '/' + Sub_folder + '/'

    if not os.path.exists(File_Path):
        os.makedirs(File_Path)

    Record_file = File_Root + '/' + File_SampleName + '/' + File_PadName + Record_ext

    # Write-verify condition
    LRS_lim = 1.6e4
    HRS_lim = 2.1e5


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

    # RESET
    RESET = create_waveform(2e-9, T_RESET, 2e-9, V_RESET_0, delay, sample_rate)
    awg.waveforms["RESET"] = RESET
    sequence_config = [{"number": 1, "waveform": "RESET"}]
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
    np.savez_compressed(generate_filename(f'RESET_{V_RESET_0}V', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)

    #####################################################################

    # read
    R_read = measure_with_smu(smu, esp32, smu_read_params,
                     generate_filename(f'read_after_RESET_{V_RESET_0}V', File_Path, '.npz'))
    print('Resistance after RESET =', R_read)
    record_resistance(Record_file, V_RESET_0, R_read, 'after_RESET')

    #######################################################################

    # PTE measurement

    for T_SET in np.logspace(-8.7, -5, 30):
        tt = '{:.1e}'.format(T_SET)
        print(tt)
        for V_SET in np.linspace(0.1, 0.4, num=30):
            V_SET_str = '{:.2f}'.format(V_SET)
            V_SET = float(V_SET_str)
            print(V_SET)

            #####################################################################

            # define SET waveform
            SET = create_waveform(rise_time, T_SET, fall_time, V_SET, delay, sample_rate)
            pulse_time = rise_time + T_SET + fall_time
            total_time = rise_time + T_SET + fall_time + 2*delay

            # write SET waveform
            awg.waveforms["SET"] = SET
            sequence_config = [{"number": 1, "waveform": "SET"}]
            setup_sequences(awg, sequence_config)

            # setup oscilloscope
            SET_settings['Timebase Scale'] = adjust_oscilloscope_scale(pulse_time * 0.2, "timebase")
            SET_settings['Timebase Position'] = adjust_oscilloscope_scale(pulse_time * 0.2, "timebase") * 2 + 1e-8
            SET_settings['Channel 1 Scale'] = adjust_oscilloscope_scale(V_SET * 0.09, "voltage")
            SET_settings['Channel 1 Offset'] = adjust_oscilloscope_scale(V_SET * 0.09, "voltage") * 3
            SET_settings['Channel 2 Scale'] = adjust_oscilloscope_scale(V_SET * 1.5, "voltage")
            SET_settings['Channel 2 Offset'] = adjust_oscilloscope_scale(V_SET * 1.5, "voltage") * 3
            SET_settings['Trigger Level']['Level'] = V_SET*2
            setup_oscilloscope(scope, SET_settings)

            # setup relay
            relays(esp32, 'switch')
            time.sleep(0.1)

            # Output and Run
            awg.write("OUTPut1:STATe 1")
            awg.enabled = True

            # waiting for trigger:
            trigger(scope, awg)
            times_i, voltages_i, times_v, voltages_v = get_waveform_data(scope)
            #plot_waveform(times,voltages)
            np.savez_compressed(generate_filename(f'SET_{V_SET}V_{tt}s', File_Path, '.npz'), times_v=times_v, voltages_v=voltages_v,times_i=times_i, voltages_i=voltages_i)

            #####################################################################

            # read
            R_read = measure_with_smu(smu, esp32, smu_read_params, generate_filename(f'read_after_SET_{V_SET}V', File_Path, '.npz'))
            print('Resistance after SET =', R_read)
            record_resistance(Record_file, V_SET, R_read, f'after_SET_{tt}')

            #####################################################################
            count = 0
            LRS = 1e10
            while LRS > LRS_lim:
                
                # initialization
                measure_with_smu(smu, esp32, smu_sweep_params, generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))

                #####################################################################

                # read
                R_read = measure_with_smu(smu, esp32, smu_read_params,
                                 generate_filename(f'read_after_sweep_{V_sweep}V', File_Path, '.npz'))
                print('Resistance after sweep =', R_read)
                record_resistance(Record_file, V_sweep, R_read, 'after_sweep')
                LRS = R_read
                count += 1
                if count >= 3:
                    print('initialiyation check break due to the cycle limit')
                    break

            #####################################################################

            # RESET
            HRS = 1e1
            for V_RESET in np.linspace(V_RESET_0,0.9,10):
                if HRS < HRS_lim:
                    print('V_RESET = ', V_RESET)
                    if not V_RESET == V_RESET_0:
                        # initialization
                        measure_with_smu(smu, esp32, smu_sweep_params,
                                         generate_filename(f'sweep_{V_sweep}V', File_Path, '.npz'))
                        RESET = create_waveform(rise_time, T_RESET, fall_time, V_RESET, delay, sample_rate)
                        awg.waveforms["RESET"] = RESET
                        time.sleep(0.1)

                    sequence_config = [{"number": 1, "waveform": "RESET"}]
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
                    # plot_waveform(times,voltages)
                    np.savez_compressed(generate_filename(f'RESET_{V_RESET}V', File_Path, '.npz'), times_v=times_v,
                                        voltages_v=voltages_v, times_i=times_i, voltages_i=voltages_i)

                    # read
                    R_read = measure_with_smu(smu, esp32, smu_read_params,
                                              generate_filename(f'read_after_RESET_{V_RESET}V', File_Path, '.npz'))
                    print('Resistance after RESET =', R_read)
                    record_resistance(Record_file, V_RESET, R_read, 'after_RESET')
                    HRS = R_read
                else:
                    break
            #####################################################################

relays(esp32,'off')
