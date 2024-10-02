from pymeasure.instruments.activetechnologies import AWG401x_AWG, SequenceEntry
import time
import pyvisa as visa
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import serial
from pyvisa.errors import VisaIOError


def connect_to_awg(address):
    """
    Establishes a connection to an arbitrary waveform generator (AWG) using its IP address.

    Parameters:
    - address (str): The IP address of the AWG, formatted as a string.

    Returns:
    - AWG401x_AWG: An instance of the AWG connection if successful, None otherwise.

    Raises:
    - Exception: Catches and logs any exceptions that occur during connection.
    """
    try:
        awg = AWG401x_AWG(f"TCPIP::{address}::INSTR")
        awg.reset()
        print("Connected to AWG and reset.")
        return awg
    except Exception as e:
        print(f"Failed to connect to AWG: {e}")
        return None


def connect_to_scope(resource_string):
    """
    Connects to an oscilloscope using a VISA resource string and resets it.

    Parameters:
    - resource_string (str): The VISA resource string to identify the oscilloscope.

    Returns:
    - visa.Resource: The oscilloscope object if the connection is successful, None otherwise.

    Raises:
    - VisaIOError: Catches and logs any I/O errors that occur during the connection.
    """
    try:
        rm = visa.ResourceManager()
        scope = rm.open_resource(resource_string)
        scope.timeout = 10000
        scope.write('*RST')
        scope.write('*CLS')
        print("Oscilloscope reset and cleared.")
        return scope
    except VisaIOError as e:
        print(f"Failed to connect to Oscilloscope: {e}")
        return None


def connect_to_smu(resource_string):
    """
    Establishes a connection to a Source Measure Unit (SMU) using the specified resource string.

    Parameters:
    - resource_string (str): The VISA resource string of the SMU.

    Returns:
    - visa.Resource: The connected resource object if successful, None otherwise.

    This function initializes the connection, resets the instrument, and clears its status.
    """
    try:
        rm = visa.ResourceManager()
        smu = rm.open_resource(resource_string)  # Corrected to use the function parameter
        smu.timeout = 100000  # Set the timeout to 60 seconds
        smu.write('*RST')  # Reset the instrument
        smu.write('*CLS')  # Clear the instrument
        print("SMU reset and cleared.")
        return smu
    except VisaIOError as e:
        print(f"Failed to connect to SMU: {e}")
        return None


def connect_to_esp32(port, baud_rate):
    """
    Establishes a serial connection to an ESP32 device. Initially connects at 9600 baud to
    ensure communication, then reconnects at the specified baud rate.

    Parameters:
    - port (str): The COM port to connect to.
    - baud_rate (int): The baud rate at which the communication should occur after initial setup.

    Returns:
    - serial.Serial: The serial connection object if the connection is successful, None otherwise.

    Raises:
    - serial.SerialException: Catches and logs any errors related to serial communication.
    """
    try:
        # Initially open serial port to ensure communication starts correctly
        with serial.Serial(port, 9600):
            print("Initial connection to ESP32 established at 9600 baud.")
        # Reopen with desired baud rate
        ser = serial.Serial(port, baud_rate)
        print(f"Connected to ESP32 at {baud_rate} baud.")
        return ser
    except serial.SerialException as e:
        print(f"Failed to connect to ESP32: {e}")
        return None


def setup_oscilloscope(scope, settings):
    """
    Configures the oscilloscope based on a dictionary of settings.

    Parameters:
    - scope (visa.Resource): The oscilloscope object to configure.
    - settings (dict): A dictionary containing key-value pairs for oscilloscope settings.

    The settings dictionary should include keys like 'Acquisition Type', 'Channel 1 Probe', 'Trigger Level', etc.,
    with appropriate values for each. Missing keys will cause the setting to be skipped.

    Raises:
    - ValueError: If a required setting is missing or any command fails to execute properly.
    """
    try:
        # Set basic and channel-specific settings only if they are provided
        scope.write('CHAN1:DISP ON')
        scope.write('CHAN2:DISP ON')
        print(1)
        if 'Acquisition Type' in settings:
            scope.write(f'ACQ:TYPE {settings["Acquisition Type"]}')
        if 'Channel 1 Probe' in settings:
            scope.write(f'CHAN1:PROB {settings["Channel 1 Probe"]}')
        if 'Channel 2 Probe' in settings:
            scope.write(f'CHAN2:PROB {settings["Channel 2 Probe"]}')
        if 'Timebase Scale' in settings:
            scope.write(f'TIMebase:SCALe {settings["Timebase Scale"]}')
        if 'Timebase Position' in settings:
            scope.write(f'TIMebase:Position {settings["Timebase Position"]}')

        # Set trigger settings
        trigger_settings = settings.get('Trigger Level')
        if trigger_settings:
            scope.write(f'TRIGger:EDGE:SOURce {settings.get("Trigger Source")}')
            scope.write(f'TRIGger:LEVel {trigger_settings["Channel"]},{trigger_settings["Level"]}')

        # More channel and waveform settings
        if 'Channel 1 Scale' in settings:
            scope.write(f'CHAN1:SCAL {settings["Channel 1 Scale"]}')
        if 'Channel 1 Offset' in settings:
            scope.write(f'CHAN1:OFFS {settings["Channel 1 Offset"]}')
        if 'Channel 2 Scale' in settings:
            scope.write(f'CHAN2:SCAL {settings["Channel 2 Scale"]}')
        if 'Channel 2 Offset' in settings:
            scope.write(f'CHAN2:OFFS {settings["Channel 2 Offset"]}')
        if 'Waveform Source' in settings:
            scope.write(f'WAVeform:SOURce {settings["Waveform Source"]}')
        if 'Waveform Byte Order' in settings:
            scope.write(f'WAVeform:BYTeorder {settings["Waveform Byte Order"]}')
        if 'Waveform Format' in settings:
            scope.write(f'WAVeform:FORMat {settings["Waveform Format"]}')
        if 'Waveform Points Mode' in settings:
            scope.write(f'WAVeform:POINts:MODE {settings["Waveform Points Mode"]}')
        if 'Waveform Points' in settings:
            scope.write(f'WAVeform:POINts {settings["Waveform Points"]}')

        # Trigger and wait handling
        if 'Trigger Mode' in settings:
            scope.write(settings['Trigger Mode'])

        # Optionally check and print termination status
        print(scope.query(':TER?'))
        scope.write('*WAI')

    except Exception as e:
        raise ValueError(f"Error configuring oscilloscope: {e}")


def adjust_oscilloscope_scale(value, scale_type):
    """
    Adjusts the given value to the nearest higher or equal available scale based on the specified type.

    Parameters:
    - value (float): The value to be adjusted to the nearest scale.
    - scale_type (str): The type of scale to adjust the value against, either 'timebase' or 'voltage'.

    Returns:
    - float: The scale value that is the nearest higher or equal to the provided value.

    Raises:
    - ValueError: If the scale_type is not recognized.

    Examples:
    - adjust_oscilloscope_scale(3e-9, "timebase") will return 5e-9.
    - adjust_oscilloscope_scale(0.007, "voltage") will return 0.01.
    """
    # Define timebase and voltage scales arrays
    timebase_scales = [1e-7, 2e-7, 5e-7, 1e-6, 2e-6,5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3]  # seconds/division
    voltage_scales = [1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 5e-1, 1, 2, 5]  # volts/division

    # Select the appropriate scale array
    if scale_type == "timebase":
        scales = timebase_scales
    elif scale_type == "voltage":
        scales = voltage_scales
    else:
        raise ValueError(f"Unknown scale type '{scale_type}'. Expected 'timebase' or 'voltage'.")

    # Find and return the closest scale that is greater than or equal to the value
    for scale in scales:
        if value <= scale:
            return scale
    return scales[-1]  # If the target value exceeds all available scales, return the largest scale


def get_waveform_data(scope):
    """
    Retrieves waveform data and its preamble from an oscilloscope, then calculates and returns time and voltage arrays.

    Parameters:
    - scope (visa.Resource): The oscilloscope object to query data from.

    Returns:
    - tuple: Contains two numpy arrays, the first for times and the second for voltages, corresponding to the waveform data.

    Raises:
    - ValueError: If there are issues parsing the preamble or data.
    """
    try:
        #Channel1
        # Query the preamble to interpret the data correctly
        scope.write(f'WAVeform:SOURce CHAN1')
        preamble_1 = scope.query('WAVeform:PREamble?').split(',')
        y_increment_1 = float(preamble_1[7])
        y_origin_1 = float(preamble_1[8])
        y_reference_1 = float(preamble_1[9])
        x_increment_1 = float(preamble_1[4])
        x_origin_1 = float(preamble_1[5])

        # Retrieve the waveform data; using 'H' to get full 16-bit range
        raw_data_1 = scope.query_binary_values('WAVeform:DATA?', datatype='H', is_big_endian=False, container=np.array)

        # Ensure the instrument has completed all pending operations before querying data
        scope.write("*WAI")

        # Calculate the voltage values from raw data
        voltages_i = (raw_data_1 - y_reference_1) * y_increment_1 + y_origin_1

        # Calculate the time array based on the number of data points and the increment
        times_i = np.arange(len(voltages_i)) * x_increment_1 + x_origin_1

        ##Channel2
        scope.write(f'WAVeform:SOURce CHAN2')
        preamble_2 = scope.query('WAVeform:PREamble?').split(',')
        y_increment_2 = float(preamble_2[7])
        y_origin_2 = float(preamble_2[8])
        y_reference_2 = float(preamble_2[9])
        x_increment_2 = float(preamble_2[4])
        x_origin_2 = float(preamble_2[5])
        raw_data_2 = scope.query_binary_values('WAVeform:DATA?', datatype='H', is_big_endian=False, container=np.array)
        scope.write("*WAI")
        voltages_v = (raw_data_2 - y_reference_2) * y_increment_2 + y_origin_2
        times_v = np.arange(len(voltages_v)) * x_increment_2 + x_origin_2

        return times_i, voltages_i,times_v,voltages_v
    except Exception as e:
        raise ValueError(f"Failed to retrieve or parse waveform data: {e}")


def plot_waveform(times, voltages):
    """
    Plots a waveform from time and voltage data.

    Parameters:
    - times (list or numpy.array): Array of time data points.
    - voltages (list or numpy.array): Array of voltage data points corresponding to the times.

    The function creates a plot of the voltages versus times, labeling the axes and adding a grid for clarity.
    """
    plt.clf()
    plt.figure(figsize=(10, 6))  # Set the size of the plot
    plt.plot(times, voltages)  # Plot the time-voltage data
    plt.xlabel('Time (s)')  # Label for the x-axis
    plt.ylabel('Voltage (V)')  # Label for the y-axis
    plt.title('Waveform')  # Title of the plot
    plt.grid(True)  # Enable grid
    plt.draw()
    plt.pause(0.2)  # Display the plot
    plt.close()


def create_waveform(rise_time, hold_time, fall_time, amplitude, delay_time, sample_rate):
    """
    Generates a custom waveform with specified rise, hold, fall, and delay times, ensuring the amplitude does not exceed a specific range.

    Parameters:
    - rise_time (float): Time for the waveform to rise from 0 to the maximum amplitude.
    - hold_time (float): Time the waveform holds at the maximum amplitude.
    - fall_time (float): Time for the waveform to fall from the maximum amplitude to 0.
    - amplitude (float): The maximum amplitude of the waveform, constrained by an absolute value of 3.
    - delay_time (float): Initial and final delay time before and after the waveform.
    - sample_rate (float): Number of samples per second.

    Returns:
    - list: A list of amplitude values representing the waveform.

    Raises:
    - ValueError: If any of the times or the amplitude are negative, if the amplitude exceeds ±3, or if the sample_rate is not positive.
    """
    # Check for negative values in time durations and sample rate, and for amplitude constraints
    if any(x < 0 for x in [rise_time, hold_time, fall_time, delay_time]) or sample_rate <= 0:
        raise ValueError("Time durations and sample rate must be non-negative, and sample rate must be positive.")
    if abs(amplitude) > 3:
        raise ValueError("Amplitude must not exceed ±3.")

    # Calculate the number of points for each section of the waveform
    delay_points = int(delay_time * sample_rate)
    rise_points = int(rise_time * sample_rate)
    hold_points = int(hold_time * sample_rate)
    fall_points = int(fall_time * sample_rate)

    # Create each section of the waveform
    waveform = [0] * delay_points  # Initial delay
    waveform.extend((i / rise_points * amplitude for i in range(rise_points)))  # Rise phase
    waveform.extend([amplitude] * hold_points)  # Hold phase
    waveform.extend((amplitude - i / fall_points * amplitude for i in range(fall_points)))  # Fall phase
    waveform.extend([0] * delay_points)  # Final delay

    return waveform


def setup_sequences(awg, sequence_config):
    """
    Initialize the AWG by resizing to the number of sequences and setting up each sequence entry with the specified waveform.

    Args:
        awg (AWG object): The arbitrary waveform generator.
        sequence_config (list of dicts): Configuration for each sequence entry including waveform details.
    """
    # Resize AWG entries to match the number of configurations
    awg.entries.resize(len(sequence_config))
    print(f"AWG initialized with {len(sequence_config)} entries.")

    # Setup each sequence entry with the corresponding waveform
    for config in sequence_config:
        sequence = SequenceEntry(awg, number_of_channels=2, sequence_number=config["number"])
        sequence.ch[1].waveform = config["waveform"]
        print(f"Sequence {config['number']} set with waveform {config['waveform']}")


def get_smu_measurement(smu, params):
    """
    Configures the SMU for a voltage sweep according to specified parameters and fetches the measurement data.
    Returns the data organized as NumPy arrays.

    Parameters:
    - smu (visa.Resource): The SMU device resource.
    - params (dict): A dictionary containing configuration parameters for the SMU.

    Returns:
    - tuple of np.ndarray: Contains arrays for time, source voltage, voltage, current, and resistance.

    Raises:
    - ValueError: If required parameters are missing or if the directory does not exist.
    - RuntimeError: If there is a failure in setting up the SMU or fetching the data.
    """
    try:
        smu.write("SOUR:FUNC VOLT")
        smu.write(f"SOUR:VOLT:START {params['start_voltage']}")
        smu.write(f"SOUR:VOLT:STOP {params['stop_voltage']}")
        smu.write(f"SOUR:VOLT:POIN {params['points']}")
        smu.write("SOUR:VOLT:MODE SWE")
        smu.write(f"SOUR:SWE:STA {params['sweep_direction']}")
        smu.write("SOUR:SWE:RANG AUTO")
        smu.write("SENS:FUNC 'CURR','VOLT','RES'")
        smu.write("SENS:CURR:RANG:AUTO:LLIM 1E-7")
        smu.write(f"SENS:CURR:NPLC {params['NPLC']}")
        smu.write(f"SENS:CURR:PROT {params['compliance_current']}")
        smu.write("SENS:CURR:RANG:AUTO:MODE RES")
        smu.write("SENS:CURR:RANG:AUTO:THR 80")
        smu.write("TRIG:SOUR AINT")
        count = str(int((2 * int(params['points']))) if params['sweep_direction'] == "DOUB" else params['points'])
        smu.write(f"TRIG:COUN {count}")

        smu.write("INIT")
        smu.write("*WAI")
        measure_time = np.array(smu.query_ascii_values("FETC:ARR:TIME?"))
        source_voltage = np.array(smu.query_ascii_values("FETC:ARR:SOUR?"))
        voltage = np.array(smu.query_ascii_values("FETC:ARR:VOLT?"))
        current = np.array(smu.query_ascii_values("FETC:ARR:CURR?"))
        resistance = np.array(smu.query_ascii_values("FETC:ARR:RES?"))
        smu.write("OUTP1 OFF")
        smu.write("*WAI")
    except Exception as e:
        raise RuntimeError(f"Failed to configure or fetch data from SMU: {e}")

    return measure_time, source_voltage, voltage, current, resistance

def get_smu_list_measurement(smu, params):
    """
    Configures the SMU for a voltage sweep according to specified parameters and fetches the measurement data.
    Returns the data organized as NumPy arrays.

    Parameters:
    - smu (visa.Resource): The SMU device resource.
    - params (dict): A dictionary containing configuration parameters for the SMU.

    Returns:
    - tuple of np.ndarray: Contains arrays for time, source voltage, voltage, current, and resistance.

    Raises:
    - ValueError: If required parameters are missing or if the directory does not exist.
    - RuntimeError: If there is a failure in setting up the SMU or fetching the data.
    """
    try:
        count = int(params['points'])
        v = np.ones(count)*float(params['voltage'])
        v_list = list(v)
        v_str = ', '.join(f'{x}' for x in v_list)
        smu.write("SOUR:FUNC VOLT")
        smu.write("SOUR:VOLT:MODE LIST")
        smu.write("SOUR:LIST:RANG AUTO")
        smu.write(f"SOUR:LIST:VOLT {v_str}")
        smu.write("SENS:FUNC 'CURR','VOLT','RES'")
        smu.write("SENS:CURR:RANG:AUTO:LLIM 1E-7")
        smu.write(f"SENS:CURR:NPLC {params['NPLC']}")
        smu.write(f"SENS:CURR:PROT {params['compliance_current']}")
        smu.write("SENS:CURR:RANG:AUTO:MODE RES")
        smu.write("SENS:CURR:RANG:AUTO:THR 80")
        smu.write("TRIG:SOUR AINT")

        smu.write(f"TRIG:COUN {count}")

        smu.write("INIT")
        smu.write("*WAI")
        measure_time = np.array(smu.query_ascii_values("FETC:ARR:TIME?"))
        source_voltage = np.array(smu.query_ascii_values("FETC:ARR:SOUR?"))
        voltage = np.array(smu.query_ascii_values("FETC:ARR:VOLT?"))
        current = np.array(smu.query_ascii_values("FETC:ARR:CURR?"))
        resistance = np.array(smu.query_ascii_values("FETC:ARR:RES?"))
        smu.write("OUTP1 OFF")
        smu.write("*WAI")
    except Exception as e:
        raise RuntimeError(f"Failed to configure or fetch data from SMU: {e}")

    return measure_time, source_voltage, voltage, current, resistance


def relays(ser, status):
    """
    Control the on/off status of relays connected to various devices.

    Args:
        ser (serial.Serial): The serial connection object.
        status (str): The operation mode for the relays ('switch', 'measure').

    Raises:
        ValueError: If an unknown status is passed.
    """
    commands = {
        'switch': ['ON0'],
        'measure': ['ON1'],
        'off':['OFF0']
    }

    if status not in commands:
        raise ValueError("Unknown status: '{}'".format(status))
    
    for command in commands[f'{status}']:
        if status != 'off':
            ser.write(command.encode())
        print(f"Relay status set to '{status}' with {command}")
        time.sleep(0.5)


def trigger(scope, awg, timeout=0.2, poll_interval=0.05):
    """
    Polls the oscilloscope to check if a trigger has occurred and controls the AWG based on the status.

    Parameters:
    - scope (instrument): The oscilloscope instrument to query.
    - awg (instrument): The arbitrary waveform generator to control.
    - timeout (float): Timeout in seconds to attempt re-triggering the AWG if no trigger is detected.
    - poll_interval (float): Time interval in seconds between status checks.

    This function disables the AWG when the oscilloscope reports a successful trigger.
    If the trigger isn't detected within a specified timeout, the AWG is triggered again.
    """
    time_count = 0
    while True:
        status = scope.query(":TER?").strip()
        if status == '+1':
            time_0 = datetime.now()
            awg.enabled = False
            awg.write("OUTPut1:STATe 0")  # Ensure AWG is disabled
            break
        time.sleep(poll_interval)
        time_count += poll_interval
        if time_count > timeout:
            awg.trigger()  # Re-trigger AWG and reset time_count
            time_0 = datetime.now()
            # time_count = 0
    return time_0

def trigger_endurance(scope, awg, timeout=0.2, poll_interval=0.05):
    """
    Polls the oscilloscope to check if a trigger has occurred and controls the AWG based on the status.

    Parameters:
    - scope (instrument): The oscilloscope instrument to query.
    - awg (instrument): The arbitrary waveform generator to control.
    - timeout (float): Timeout in seconds to attempt re-triggering the AWG if no trigger is detected.
    - poll_interval (float): Time interval in seconds between status checks.

    This function disables the AWG when the oscilloscope reports a successful trigger.
    If the trigger isn't detected within a specified timeout, the AWG is triggered again.
    """
    time_count = 0
    while True:
        time.sleep(poll_interval)
        time_count += poll_interval
        if time_count > timeout:
            awg.trigger()  # Re-trigger AWG and reset time_count
            time.sleep(0.1)
            break


def measure_with_smu(smu, ser, params, filename):
    """
    Activates relays for measurement, configures the SMU based on provided parameters, and retrieves measurement data.

    Parameters:
    - smu (visa.Resource): The SMU device to be used for the measurements.
    - params (dict): A dictionary containing parameters for the SMU configuration.

    Returns:
    - pandas.DataFrame: DataFrame containing the measurement data retrieved from the SMU.

    Raises:
    - Exception: Generic exceptions caught from underlying functions with an explanation.
    """
    try:
        relays(ser, 'measure')
        time.sleep(0.1)
        measure_time, source_voltage, voltage, current, resistance = get_smu_measurement(smu, params)
        np.savez_compressed(filename, time=measure_time, source_voltage=source_voltage, voltage=voltage,
                            current=current, resistance=resistance)
        
        # Calculate the average of the middle 10 resistance values
        mid_index = len(resistance) // 2
        middle_values = resistance[mid_index - 5:mid_index + 5]
        average_resistance = np.mean(middle_values)

        return average_resistance
    except Exception as e:
        print(f"An error occurred during SMU measurement: {e}")
        raise

def measure_with_smu_list(smu, ser, params, filename):
    """
    Activates relays for measurement, configures the SMU based on provided parameters, and retrieves measurement data.

    Parameters:
    - smu (visa.Resource): The SMU device to be used for the measurements.
    - params (dict): A dictionary containing parameters for the SMU configuration.

    Returns:
    - pandas.DataFrame: DataFrame containing the measurement data retrieved from the SMU.

    Raises:
    - Exception: Generic exceptions caught from underlying functions with an explanation.
    """
    try:
        relays(ser, 'measure')
        time_now = datetime.now()
        measure_time, source_voltage, voltage, current, resistance = get_smu_list_measurement(smu, params)
        np.savez_compressed(filename, time=measure_time, source_voltage=source_voltage, voltage=voltage,
                            current=current, resistance=resistance)

        # Calculate the average of the middle 10 resistance values
        mid_index = len(resistance) // 2
        middle_values = resistance[mid_index - 5:mid_index + 5]
        average_resistance = np.mean(middle_values)
        return average_resistance, time_now
    except Exception as e:
        print(f"An error occurred during SMU measurement: {e}")
        raise

def generate_filename(prefix, directory, extension=".csv"):
    """
    Generates a filename with a timestamp, prefix, and specified file extension, placed in the given directory.

    Parameters:
    - prefix (str): Prefix for the filename to help identify the file type or content.
    - directory (str): The directory where the file will be saved.
    - extension (str): The file extension; defaults to ".csv".

    Returns:
    - str: The full path of the new file with the constructed filename.

    Example filename: "2024-04-20_142030_mydata.npz"
    """
    # Generate the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    # Construct the filename with the timestamp first, then the prefix
    new_filename = '{}_{}{}'.format(timestamp, prefix, extension)
    # Return the full path to the new file
    return os.path.join(directory, new_filename)


def record_resistance(file_name, voltage, resistance, event):
    """
    Records measurement data to a specified CSV file, appending each entry on a new line.

    Parameters:
    - file_name (str): The path to the CSV file where the data will be recorded.
    - timestamp (str): Timestamp for when the measurement was taken.
    - voltage (float): Voltage value to record, formatted to one decimal place.
    - resistance (float): Resistance value to record.
    - event (str): Description of the event or context of the measurement.

    The function appends a new line in the format "timestamp,event,voltage,resistance" to the CSV file.

    Returns:
    - None
    """
    # Ensure the directory for the file exists
    directory = os.path.dirname(file_name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Generate the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Prepare the data string
    voltage_str = '{:.2f}'.format(voltage)
    content = f"{timestamp},{event},{voltage_str},{resistance}\n"

    try:
        # Attempt to open the file and append the data
        with open(file_name, "a") as file:
            file.write(content)
        print(f'Recorded data to {file_name}')
    except Exception as e:
        print(f'Failed to record data: {e}')

def generate_logscale_integers(n, m):
    # Initially generate m points on a logarithmic scale
    log_space = np.logspace(0, n, num=m, base=10)
    # Convert the floating point numbers to integers and remove duplicates
    integers = np.unique(np.round(log_space).astype(int))

    # If the generated points are fewer than m, increase the number of points until the condition is met
    jj = m
    while len(integers) < m:
        jj += 1
        log_space = np.logspace(0, n, num=jj, base=10)
        integers = np.unique(np.round(log_space).astype(int))

    # Final sorted list of integers, ensuring there are m values
    result = np.sort(integers[:m])

    # Calculate the differences between consecutive integers
    differences = np.diff(result)-1

    return result, differences
