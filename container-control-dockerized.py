#/usr/bin/python3

import re
import urllib
import urllib.request
import json
import argparse
import os

DONTSTOPLIST = ["borgmatic", "dockerproxy"]
MOVEATTHEEND = ["npm-app", "npm-db"]

def get_containers_status(socket, is_url):
	if is_url:
		base_url = socket
		with urllib.request.urlopen(f"{base_url}containers/json?all=1") as response:
			html = response.read()

		answer = json.loads(html)
		out_dict = dict()
		for container in answer:
			out_dict[container['Names'][0][1:]] = container['State']
		return out_dict

def get_running_containers(socket, is_url):
	if is_url:
		base_url = socket
		url = f'{base_url}containers/json?' + 'filters={"status":["running"]}'
		with urllib.request.urlopen(url) as response:
			html = response.read()

		answer = json.loads(html)
		running_containers = []
		for container in answer:
			if container['Names'][0][1:] not in DONTSTOPLIST:
				running_containers.append(container['Names'][0][1:])
		for container in MOVEATTHEEND:
			running_containers.append(running_containers.pop(running_containers.index(container)))
		return running_containers

def is_correct_url(string_to_test):
	url_regex = "https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}(\.[a-z]{2,4})?\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
	result = re.search(url_regex, string_to_test)
	return result

def get_relevant_containers():
	filename = "./current_containers.lst"
	if not os.path.exists(filename):
		raise FileNotFoundError("current_containers not found ! Be sure to execute stop THEN start")
	with open(filename, 'r', encoding="utf8") as file:
		output_list = [line.rstrip() for line in file]
	return output_list

def start(socket, is_url):
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



def stop(socket, is_url):
	print("Stopping the containers")
	containers_to_stop = get_running_containers(socket, is_url)
	filename = "./current_containers.lst"
	if os.path.exists(filename):
		if os.path.exists("./old_containers.lst"):
			# If the old file exists we delete it to continue
			os.remove("./old_containers.lst")
		os.rename(filename, "./old_containers.lst")
	with open(filename, 'w', encoding="utf8") as file:
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


def status(socket, is_url):
	print("Fetching the status of the containers")
	dict_status=get_containers_status(socket, is_url)
	print(dict_status)
	os.putenv("BORGMATIC_CONTAINERS_STATUS", str(dict_status))
	os.system("bash")


def main():
	# Defining the argument
	parser = argparse.ArgumentParser(description="A script to fetch and control the start and stop of containers in order to backup them")
	parser.add_argument('Action',
                     metavar='ACTION',
                     type=str,
                     help='the action to perform between : start, stop and status')
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
	if is_url:
		if not is_correct_url(socket):
			raise ValueError(
				f"Incorrect URL format: {socket}\nIf the socket is not mapped to an url do not use the --url flag!")
		if socket[-1] != "/":
			socket += '/'

	if action == "start":
		start(socket, is_url)
	elif action == "stop":
		stop(socket, is_url)
	elif action == "status":
		status(socket, is_url)
	else:
		raise ValueError(f"Unknown ACTION:{action}")


if __name__ == "__main__":
	main()