#!/usr/bin/python3

from subprocess import run, PIPE, CompletedProcess
import json
import argparse
from pathlib import Path

# Global variables
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


def build_command(**kwargs) -> str:
    working_dir = Path(__file__).parent
    command = str(working_dir) + "/Librespeed-cli/librespeed-cli"
    command += " --secure"
    command += " --json"

    return command


def run_speedtest(command: str):
    speedtest_output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    return speedtest_output


def prepare_monitoring_out(speedtest_out: CompletedProcess) -> str:
    output_dict = json.loads(speedtest_out.stdout)
    output_str: str = "Speedtest to server '{0}' at {1} from client ip '{2}':\n" \
                      "Ping: {3}ms\n" \
                      "Jitter: {4}ms\n" \
                      "Download: {5}\n" \
                      "Upload: {6}".format(output_dict['server']['name'], output_dict['timestamp'],
                                           output_dict['client']['ip'], output_dict['ping'],
                                           output_dict['jitter'], output_dict['download'],
                                           output_dict['upload'])

    return output_str


def determine_icinga_state(speedtest_out: CompletedProcess, warn_thresholds: str, crit_thresholds: str) -> int:
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

    #ToDo: Add check if warning thresholds are high/lower as the critical ones
    if (download_warn > download_crit):
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
    else:
        pass

    return state


def performance_data(speedtest_out: CompletedProcess, warn_thresholds: str, crit_thresholds: str) -> str:
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

    perf_data = " | "
    perf_data += " 'download'={0}MB;{1}MB;{2}MB;;".format(str(download), str(download_warn), str(download_crit))
    perf_data += " 'upload'={0}MB;{1}MB;{2}MB;;".format(str(upload), str(upload_warn), str(upload_crit))
    perf_data += " 'ping'={0}ms;{1}ms;{2}ms;;".format(str(ping), str(ping_warn), str(ping_crit))
    perf_data += " 'jitter'={0}ms;{1}ms;{2}ms;;".format(str(jitter), str(jitter_warn), str(jitter_crit))

    return perf_data


def icinga_out(prepared_out: str, determined_state: int, **kwargs):
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


if __name__ == "__main__":
    # region Add arguments
    arguments = argparse.ArgumentParser()
    arguments.add_argument('-w', '--warning', help="The warning thresholds. Usage: <download>;<upload>;<ping>;<jitter>"
                                                   "Zero disables the check for the given type. Default: 50;20;75;0",
                           type=str, metavar="<download>;<upload>;<ping>;<jitter>", default="50;20;75;0")
    arguments.add_argument('-c', '--critical',
                           help="The critical thresholds. Usage: <download>;<upload>;<ping>;<jitter>. "
                                "Zero disables the check for the given type. Default: 25;10;100;0",
                           type=str, metavar="<download>;<upload>;<ping>;<jitter>", default="25;10;100;0")
    arguments.add_argument('--perfdata', help="Create performance data. Default: False", action="store_true")
    args = arguments.parse_args()
    # endregion
    # region Run program
    full_command = build_command()
    spte_out = run_speedtest(full_command)
    prep_icinga_out = prepare_monitoring_out(spte_out)
    state = determine_icinga_state(spte_out, args.warning, args.critical)
    if args.perfdata is True:
        perf_data = performance_data(spte_out, args.warning, args.critical)
        icinga_out(prep_icinga_out, state, performance_data=perf_data)

    else:
        icinga_out(prep_icinga_out, state)
    # endregion
