#!/usr/bin/env python3
import logging
import logging.handlers
import os
import subprocess
import json
import time
import signal
import pathlib
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
logger.addHandler(sh)
working_dir = os.path.dirname(__file__)
fh = logging.handlers.RotatingFileHandler(os.path.join(
    working_dir, 'fowarder.log'), maxBytes=2000, backupCount=4)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

dir = pathlib.Path(__file__).parent.absolute()
config_json = os.path.join(dir, 'config.json')


def load_config():
    with open(config_json) as f:
        return json.load(f)
# */5 * * * * /usr/bin/python3 /home/v4mpc/repo/local_port_forwader/forwarder.py >> /home/v4mpc/repo/local_port_forwader/cron.log 2>&1


config = load_config()
ssh_user = config['ssh_user']
ssh_host = config['ssh_host']
ssh_port = config['ssh_port']
timeout = config['timeout']
forward_port = config['forward_port']
local_ssh_port = config['local_ssh_port']
part_1 = f"{ssh_user}@{ssh_host}"
part_2 = f"-p{ssh_port}"
part_3 = f"{forward_port}:localhost:{local_ssh_port}"


def port_forward():
    logger.debug("Trying to Port Forward")
    cm = ["ssh", "-f", "-N", part_1, part_2, "-R", part_3]
    try:

        output = subprocess.run(cm, timeout=timeout,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if output.returncode > 0:
            logger.error(
                f"PortForwading Failed. {output.stderr.decode().rstrip()}")
    except Exception as e:
        logger.error(str(e))
    # logger.debug("PortForwading was Successful")
    logger.debug("Done trying")


def get_remote_pid():
    logger.debug('Getting Getting Remote PID')
    part_1 = f"{ssh_user}@{ssh_host}"
    part_2 = f"-p{ssh_port}"
    cmd = ['ssh', part_1,
           part_2, f'lsof -t -i:{forward_port}']
    try:
        cmd_out = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if cmd_out.returncode == 0:
            cmd_out = cmd_out.stdout.decode()
            pid = cmd_out.rstrip()
            logger.debug(f"Remote PID is {pid}")
            return pid
        else:
            logger.error(
                f'Could not get Remote PID. {cmd_out.stderr.decode().rstrip()}')
    except Exception as e:
        logger.error(str(e))
    # exit()


def get_local_pid():
    logger.debug('Getting local PID')
    p_cmd = f"ssh -f -N {part_1} {part_2} -R {part_3}"
    ps_list = get_local_ps_list()
    for pid, cmd in ps_list:
        if p_cmd == cmd:
            logger.debug(f'Local PID is {pid}')
            return pid
    logger.debug('No local PID')
    return None


def kill_remote_process(pid):
    logger.debug(f'Killing remote Process with PID {pid}')
    part_1 = f"{ssh_user}@{ssh_host}"
    part_2 = f"-p{ssh_port}"
    cmd = ['ssh', part_1,
           part_2, f'kill -9 {pid}']
    cmd_out = subprocess.run(cmd)
    logger.debug('Remote process killed')
    return False


def kill_local_process(pid):
    logger.debug(f'Killing local Process with PID {pid}')
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        pass


def update_local_pid(pid):
    logger.debug(f"Updating Process is in {config_json}")
    old_config = load_config()
    with open(config_json, 'w') as f:
        new_config = old_config
        new_config['local_process_id'] = pid
        json.dump(new_config, f)


def load_config():
    with open(config_json) as f:
        return json.load(f)


def get_local_ps_list():
    logger.debug('Getting Process list')
    return [(int(p), c) for p, c in [x.rstrip('\n').split(' ', 1)
                                     for x in os.popen('ps h -eo pid:1,command')]]


if __name__ == '__main__':
    remote_pid = get_remote_pid()
    local_pid = get_local_pid()
    if remote_pid and local_pid:
        logger.debug(f"SSH port forwading is RUNNING")
    else:
        kill_local_process(local_pid)
        if remote_pid:
            kill_remote_process(remote_pid)
        port_forward()
