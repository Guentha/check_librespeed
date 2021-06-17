#!/usr/bin/python3

from subprocess import run, PIPE, CompletedProcess
import json
import argparse
from pathlib import Path

# region Global variables
# Icinga2 state values
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
# endregion

# region Functions
def build_command(arguments: argparse.Namespace) -> str:
    """
    Build the command for the librespeed-cli program.
    :param arguments: Arguments object.
    :return: A string with the build command to execute.
    """
    working_dir = Path(__file__).parent
    command = str(working_dir) + "/Librespeed-cli/librespeed-cli"
    if arguments.list is True:
        command += " --list"

    else:
        command += " --secure"
        command += " --json"

        if arguments.server is not None:
            command += " --server {}".format(arguments.server)

        if arguments.mebibytes is True:
            command += " --mebibytes"

    return command


def run_speedtest(command: str) -> CompletedProcess:
    """
    Run the previously build command.
    :param command: The command string to execute.
    :return: CompletedProcess object.
    """
    speedtest_output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    return speedtest_output


def prepare_monitoring_out(speedtest_out: CompletedProcess) -> str:
    """
    Prepare the output for the monitoring.
    :param speedtest_out: CompletedProcess object from the subprocess module.
    :return: A string with the formated monitoring output.
    """
    output_dict = json.loads(speedtest_out.stdout)
    output_str: str = "Speedtest to server '{}' at {} from client ip '{}':\n" \
                      "Ping: {}ms\n" \
                      "Jitter: {}ms\n" \
                      "Download: {}Mbps\n" \
                      "Upload: {}Mbps".format(output_dict['server']['name'], output_dict['timestamp'],
                                           output_dict['client']['ip'], int(output_dict['ping']),
                                           output_dict['jitter'], output_dict['download'],
                                           output_dict['upload'])

    return output_str


def determine_icinga_state(speedtest_out: CompletedProcess, warn_thresholds: str, crit_thresholds: str) -> int:
    """
    Checks with which code the program should exit.
    :param speedtest_out: CompletedProcess object from the subprocess module.
    :param warn_thresholds: Warning thresholds provided with the arguments in the format "<download>;<upload>;<ping>;<jitter>".
    :param crit_thresholds: Critical thresholds provided with the arguments in the format "<download>;<upload>;<ping>;<jitter>".
    :return: An integer with presents the exit code of the program.
    """
    state = UNKNOWN
    speedtest_out_dict = json.loads(speedtest_out.stdout)
    download: float = speedtest_out_dict['download']
    upload: float = speedtest_out_dict['upload']
    ping: float = speedtest_out_dict['ping']
    jitter: float = speedtest_out_dict['jitter']

    warn_list = warn_thresholds.split(";")
    crit_list = crit_thresholds.split(";")

    download_warn = int(warn_list[0])
    download_crit = int(crit_list[0])
    upload_warn = int(warn_list[1])
    upload_crit = int(crit_list[1])
    ping_warn = int(warn_list[2])
    ping_crit = int(crit_list[2])
    jitter_warn = int(warn_list[3])
    jitter_crit = int(crit_list[3])

    if (not download_warn <= 0 and download_crit < download < download_warn) or \
            (not upload_warn <= 0 and upload_crit < upload < upload_warn) or \
            (0 < ping_warn < ping < ping_crit) or \
            (0 < jitter_warn < jitter < jitter_crit):

        state = WARNING

    if (not download_crit <= 0 and download < download_crit) or \
            (not upload_crit <= 0 and upload < upload_crit) or \
            (0 < ping_crit < ping) or \
            (0 < jitter_crit < jitter):

        state = CRITICAL

    if download > download_warn and upload > upload_warn and (ping < ping_warn or ping_warn <= 0) and \
            (jitter < jitter_warn or jitter_warn <= 0):
        state = OK

    return state


def performance_data(speedtest_out: CompletedProcess, warn_thresholds: str, crit_thresholds: str, mebibytes: bool) -> str:
    """
    Generate the performance data for the monitoring.
    :param speedtest_out: CompletedProcess object from the subprocess module.
    :param warn_thresholds: Warning thresholds provided with the arguments in the format "<download>;<upload>;<ping>;<jitter>".
    :param crit_thresholds: Critical thresholds provided with the arguments in the format "<download>;<upload>;<ping>;<jitter>".
    :param mebibytes: A boolean if performance data should returned in MiBs instead of MBs.
    :return: A formated string to attach to the plugin output.
    """
    speedtest_out_dict = json.loads(speedtest_out.stdout)
    download: float = speedtest_out_dict['download']
    upload: float = speedtest_out_dict['upload']
    ping: float = speedtest_out_dict['ping']
    jitter: float = speedtest_out_dict['jitter']
    bytes_sent: int = speedtest_out_dict['bytes_sent']
    bytes_received: int = speedtest_out_dict['bytes_received']

    warn_list = warn_thresholds.split(";")
    crit_list = crit_thresholds.split(";")

    download_warn = int(warn_list[0])
    download_crit = int(crit_list[0])
    upload_warn = int(warn_list[1])
    upload_crit = int(crit_list[1])
    ping_warn = int(warn_list[2])
    ping_crit = int(crit_list[2])
    jitter_warn = int(warn_list[3])
    jitter_crit = int(crit_list[3])

    perf_data = " | "
    speed_unit = "MB"
    if mebibytes is True:
        speed_unit = "MiB"

    perf_data += " 'download'={0}{3};{1}{3};{2}{3};;".format(str(download), str(download_warn), str(download_crit),
                                                             speed_unit)
    perf_data += " 'upload'={0}{3};{1}{3};{2}{3};;".format(str(upload), str(upload_warn), str(upload_crit), speed_unit)
    perf_data += " 'ping'={0}ms;{1}ms;{2}ms;;".format(str(int(ping)), str(ping_warn), str(ping_crit))
    perf_data += " 'jitter'={0}ms;{1}ms;{2}ms;;".format(str(jitter), str(jitter_warn), str(jitter_crit))
    perf_data += " 'bytes_sent'={}".format(str(bytes_sent))
    perf_data += " 'bytes_received'={}".format(str(bytes_received))

    return perf_data


def icinga_out(prepared_out: str, determined_state: int, **kwargs):
    """
    Attaches the current state in front of the output and exits the script with the given state and ouput.
    :param prepared_out: String the plugin should print out.
    :param determined_state: The state the plugin should return as integer.
    :param kwargs: If performance data should be attached to the output.
    :return: Nothing.
    """
    if determined_state == OK:
        prepared_out = "[OK] " + prepared_out

    elif determined_state == WARNING:
        prepared_out = "[WARNING] " + prepared_out

    elif determined_state == CRITICAL:
        prepared_out = "[CRITICAL] " + prepared_out

    else:
        prepared_out = "[UNKNOWN] " + prepared_out

    for key, values in kwargs.items():
        if "performance_data" == key:
            prepared_out += values

    print(prepared_out)
    exit(determined_state)


def check_thresholds(warning: str, critical: str):
    """
    Checks if the provides thresholds are valid.
    :param warning: The warning threshold string provided with the arguments.
    :param critical: The critical threshold string provided with the arguments.
    :return: Nothing.
    """
    error = False
    message = "[UNKNOWN] "
    warn_list = warning.split(";")
    crit_list = critical.split(";")

    download_warn = int(warn_list[0])
    download_crit = int(crit_list[0])
    upload_warn = int(warn_list[1])
    upload_crit = int(crit_list[1])
    ping_warn = int(warn_list[2])
    ping_crit = int(crit_list[2])
    jitter_warn = int(warn_list[3])
    jitter_crit = int(crit_list[3])

    if (download_warn < download_crit and not download_crit <= 0) and not download_warn <= 0:
        error = True
        message += " Download warning threshold must be zero or higher than the critical threshold!\n"

    if (upload_warn < upload_crit and not upload_crit <= 0) and not upload_warn <= 0:
        error = True
        message += " Upload warning threshold must be zero or higher than the critical threshold!\n"

    if (ping_warn > ping_crit and not ping_crit <= 0) and not ping_warn <= 0:
        error = True
        message += " Ping warning threshold must be zero or lower than the critical threshold!\n"

    if (jitter_warn > jitter_crit and not jitter_crit <= 0) and not jitter_warn <= 0:
        error = True
        message += " Jitter warning threshold must be zero or lower than the critical threshold!\n"

    if error:
        print(message)
        exit(UNKNOWN)
# endregion

# region Main program
if __name__ == "__main__":
    # region Add arguments
    arguments = argparse.ArgumentParser(prog=Path(__file__).name, usage="%(prog)s [options]",
                                        description="Nagios/Icinga2 Monitoring script for checking the internet speed."
                                                    "Values returned in bit/s. Speedtest are performed via HTTPS.")
    arguments.add_argument('-w', '--warning', help="The warning thresholds. Usage: <download>;<upload>;<ping>;<jitter>"
                                                   "Zero disables the check for the given type. Default: 50;20;75;0",
                           type=str, metavar="<download>;<upload>;<ping>;<jitter>", default="50;20;75;0")
    arguments.add_argument('-c', '--critical',
                           help="The critical thresholds. Usage: <download>;<upload>;<ping>;<jitter>. "
                                "Zero disables the check for the given type. Default: 25;10;100;0",
                           type=str, metavar="<download>;<upload>;<ping>;<jitter>", default="25;10;100;0")
    arguments.add_argument('--perfdata', help="Create performance data. Default: False", action="store_true")
    arguments.add_argument('-s', '--server', help="Which server to use for the speedtest. Provide the number"
                                                  " listed with the argument '--list'. Default choose a random one.",
                           type=int, metavar="<integer>")
    arguments.add_argument('-l', '--list', help="List available servers for the speedtest. Default: False",
                           action="store_true")
    arguments.add_argument('--mebibytes', help="Use 1024 bytes as 1 kilobyte instead of 1000. Default: False",
                           action="store_true")
    args = arguments.parse_args()
    # endregion
    # region Run program
    full_command = build_command(arguments=args)

    if args.list is not True:
        check_thresholds(args.warning, args.critical)
        spte_out = run_speedtest(full_command)
        prep_icinga_out = prepare_monitoring_out(spte_out)
        state = determine_icinga_state(spte_out, args.warning, args.critical)
        if args.perfdata is True:
            perf_data = performance_data(spte_out, args.warning, args.critical, args.mebibytes)
            icinga_out(prep_icinga_out, state, performance_data=perf_data)

        else:
            icinga_out(prep_icinga_out, state)

    elif args.list is True:
        print(run_speedtest(full_command).stdout)
    # endregion
# endregion