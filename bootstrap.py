#!/usr/bin/env python
# coding=utf-8

"""Usage:
/usr/bin/bootstrap --num=32 --cmd='/usr/bin/frontik --config=/etc/hh-xhh/frontik.cfg --app=xhh --port=15{num:0>2} --lead_process={is_lead_process}'
available placeholders:
{num} - process index number
{shutdown_exitcode} - if any child process returns this exit code all processes must be terminated
{is_lead_process} - to mark the process as lead. this can be used to perform specific logic once for all processes. see '--lead_process_index' option
"""

import argparse
import logging
import signal
import subprocess
import sys
import time

_PROCESSES = []


def start():
    parser = argparse.ArgumentParser(description='Simple supervisor for docker')
    parser.add_argument('--cmd', type=str, help='Command to be executed')
    parser.add_argument('--num', type=int, help='Processes count')
    parser.add_argument('--log', type=str, help='Logfile path (uses stderr if empty)')
    parser.add_argument('--lead_process_index', type=int, default=0, help='lead process index, 0-based')
    parser.add_argument('--shutdown_exitcode', type=int, default=228, help='Not recoverable shutdown code')
    args = parser.parse_args()

    if args.log is None:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(asctime)s %(message)s')
    else:
        logging.basicConfig(filename=args.log, level=logging.DEBUG, format='%(asctime)s %(message)s')

    signal.signal(signal.SIGTERM, sigterm_action)

    for i in range(args.num):
        start_process(i, args)

    while True:
        for i, proc in enumerate(_PROCESSES):
            return_code = proc.poll()
            if return_code is not None:
                if args.shutdown_exitcode and return_code == args.shutdown_exitcode:
                    logging.info('child #%s exited with code %s - untolerable fail. shutting all down', i, return_code)
                    sigterm_action(signal.SIGTERM, None)
                else:
                    logging.info('child #%s was shut down, exit code: %s', i, return_code)
                    cmd_formatted = _get_cmd(args, i)
                    logging.info('restarting process #%s, executing "%s"', i, cmd_formatted)

                    _PROCESSES[i] = subprocess.Popen(cmd_formatted.split())

            time.sleep(1)

        if not _PROCESSES:
            logging.info('all children terminated, exiting')
            sys.exit(0)


def sigterm_action(signum, stack):
    logging.info('received SIGTERM')

    term_processes = _PROCESSES[:]
    _PROCESSES[:] = []

    for i, proc in enumerate(term_processes):
        logging.info('sending SIGTERM to process #%s', i)
        proc.send_signal(signum)


def start_process(process_num, args):
    cmd_formatted = _get_cmd(args, process_num)
    logging.info('starting process #%s, executing "%s"', process_num, cmd_formatted)
    _PROCESSES.append(subprocess.Popen(cmd_formatted.split()))


def _get_cmd(args, process_index):
    return args.cmd.format(num=process_index,
                           shutdown_exitcode=args.shutdown_exitcode,
                           is_lead_process=process_index == args.lead_process_index,)


if __name__ == '__main__':
    start()
