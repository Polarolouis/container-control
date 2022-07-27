#/usr/bin/python3

import re
import urllib
import urllib.request
import json
import argparse
import os

SCRIPT_DIR = filepath = os.path.dirname(os.path.abspath(__file__))
config_path = SCRIPT_DIR + '/config.json'

if not os.path.exists(config_path):
	print(f"The config file ({config_path}) doesn't seem to exist, creating an empty config file")
	with open(config_path, 'w', encoding='utf8') as config_file:
		config = {"dont_stop":[], "move_at_the_end":[]}
		json.dump(config, config_file)

with open(config_path, 'r', encoding='utf8') as config_file:
	config = json.load(config_file)

print(config)

DONTSTOPLIST = config["dont_stop"]
MOVEATTHEEND = config["move_at_the_end"]

#print(DONTSTOPLIST)
#print(MOVEATTHEEND)

def get_containers_status(socket, is_url, verbose):
	if is_url:
		base_url = socket
		if verbose:
			print("Making request to Docker API")
		with urllib.request.urlopen(f"{base_url}containers/json?all=1") as response:
			html = response.read()
		if verbose:
			print("Converting request to dict format")
		answer = json.loads(html)
		out_dict = dict()
		if verbose:
			print("Extracting containers names")
		for container in answer:
			out_dict[container['Names'][0][1:]] = container['State']
		return out_dict

def get_running_containers(socket, is_url, verbose):
	if verbose:
		print("Getting running containers :")
	if is_url:
		base_url = socket
		url = f'{base_url}containers/json?' + 'filters={"status":["running"]}'
		with urllib.request.urlopen(url) as response:
			html = response.read()

		answer = json.loads(html)
		containers_names = [container['Names'][0][1:] for container in answer]
		if verbose:
			print(f"Currently those containers are running : {containers_names}")
		running_containers = []
		for container_name in containers_names:
			if container_name not in DONTSTOPLIST and container_name not in MOVEATTHEEND:
				running_containers.append(container_name)
		if verbose:
			print(f"The following containers were excluded as they are in the DONT STOP LIST : {DONTSTOPLIST}")
		for container_name in MOVEATTHEEND:
			if container_name in containers_names:
				running_containers.append(container_name)
#			running_containers.append(running_containers.pop(running_containers.index(container)))
		if verbose:
			print(f"The following containers were appended at the end of the list as they are in the MOVE AT THE END list : {MOVEATTHEEND}")
		return running_containers

def is_correct_url(string_to_test, verbose):
	if verbose:
		print("Using the RegExp to validate the URL")
	url_regex = "https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}(\.[a-z]{2,4})?\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
	result = re.search(url_regex, string_to_test)
	if verbose:
		print(f"Is a correct URL : {result}")
	return result

def get_relevant_containers():
	filepath = SCRIPT_DIR + "/current_containers.lst"
	if not os.path.exists(filename):
		raise FileNotFoundError("current_containers file not found ! Be sure to execute stop THEN start")
	if verbose:
		print(f"Opening {filepath} to read the relevant containers to stop")
	with open(filename, 'r', encoding="utf8") as file:
		output_list = [line.rstrip() for line in file]
	return output_list

def start(socket, is_url, verbose):
	print("Starting the containers")
	containers_to_start = get_relevant_containers()
	max_length = 0
	for container in containers_to_start:
		if len(container) > max_length:
			max_length = len(container)
	for container in containers_to_start:
		if is_url:
			url = socket + f"containers/{container}/start"
			req = urllib.request.Request(url, method="POST")
			try:
				resp = urllib.request.urlopen(req)
			except urllib.error.HTTPError as err:
				pass
			if resp.getcode() != 204 and resp.getcode() != 304:
				print(f"{container:<{max_length}} | Error when starting command, status code : {resp.getcode()}")
			else:
				print(f"{container:<{max_length}} | Successfully started : {resp.getcode()}")



def stop(socket, is_url, verbose):
	print("Stopping the containers")
	containers_to_stop = get_running_containers(socket, is_url, verbose)
	filepath = SCRIPT_DIR + "/current_containers.lst"
	old_current_containers_path = SCRIPT_DIR + "/old_containers.lst"
	if os.path.exists(filepath):
		if verbose:
			print("current_containers.lst already exists")
		if os.path.exists(old_current_containers_path):
			# If the old file exists we delete it to continue
			if verbose:
				print("old_containers.lst already exists, removing")
			os.remove(old_current_containers_path)
		if verbose:
			print("Moving current_containers.lst -> old_containers.lst")
		os.rename(filepath, old_current_containers_path)
	with open(filepath, 'w', encoding="utf8") as file:
		if verbose:
			print("Writing containers to current_containers.lst")
		max_length = 0
		for container in containers_to_stop:
			if len(container) > max_length:
				max_length = len(container)
		for container in containers_to_stop:
			file.write(container + "\n")
			if is_url:
				url = socket + f"containers/{container}/stop"
				req = urllib.request.Request(url, method="POST")
				with urllib.request.urlopen(req) as resp:
					if resp.getcode() != 204 and resp.getcode() != 304:
						print(f"{container:<{max_length}} | Error when stopped command, status code : {resp.getcode()}")
					else:
						print(f"{container:<{max_length}} | Successfully stopped : {resp.getcode()}")


def status(socket, is_url, verbose):
	print("Fetching the status of the containers")
	dict_status=get_containers_status(socket, is_url, verbose)
	print(dict_status)


def main():
	# Defining the argument
	parser = argparse.ArgumentParser(description="A script to fetch and control the start and stop of containers in order to backup them")
	parser.add_argument('Action',
                     metavar='ACTION',
                     type=str,
                     help='the action to perform between : start, stop and status')
	parser.add_argument('-v', '--verbose',
				help="enable verbose mode",
				action='store_true')
	parser.add_argument('-s',
                     metavar='SOCKET',
                     nargs='?',
                     type=str,
                     default="/var/run/docker.sock",
                     help='the path or URL to the Docker Engine API socket. Default to : /var/run/docker.sock')
	parser.add_argument('--url',
                     action='store_true',
                     help='optional flag to specify if the socket can be an URL')

	args = parser.parse_args()
	action = args.Action
	socket = args.s
	is_url = args.url
	verbose = args.verbose

	if is_url:
		if not is_correct_url(socket, verbose):
			raise ValueError(
				f"Incorrect URL format: {socket}\nIf the socket is not mapped to an url do not use the --url flag!")
		if socket[-1] != "/":
			socket += '/'

	if action == "start":
		start(socket, is_url, verbose=verbose)
	elif action == "stop":
		stop(socket, is_url, verbose=verbose)
	elif action == "status":
		status(socket, is_url, verbose=verbose)
	else:
		raise ValueError(f"Unknown ACTION:{action}")


if __name__ == "__main__":
	main()
