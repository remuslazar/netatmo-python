#!/usr/bin/env python
# -*- coding: utf-8 -*-

import httplib, urllib, json, shelve, time, sys, getopt, ConfigParser, os

class NetatmoApi:
	"""Talk to the Netatmo API and do the OAuth2 dance"""

	host = "api.netatmo.net"
	request_token_path = "/oauth2/token"

	def __init__(self, client_id, client_secret):
		self.client_id = client_id
		self.client_secret = client_secret
		# get the directory where this script resides
		mydir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
		self.db = shelve.open(os.path.join(mydir, "netatmo"))
		self.__check_token()

	def __del__(self):
		self.db.close()

	# prompt for user credentials for the initial token request
	def __prompt_credentials(self):
		username = raw_input(u'Username: ')
		password = raw_input(u'Password: ')
		return (username, password)

	def __http(self,params):
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		conn = httplib.HTTPSConnection(self.host)
		conn.request("POST", self.request_token_path, urllib.urlencode(params), headers)
		response = conn.getresponse()
		if (response.status != 200):
			raise Exception("Invalid response status %s." % response.status)
		return json.loads(response.read())

	def __get_token(self):
		credentials = self.__prompt_credentials()
		return self.__http({
			"grant_type": "password",
			"client_id": self.client_id,
			"client_secret": self.client_secret,
			"username": credentials[0],
			"password": credentials[1]
		})

	def __refresh_token(self,refresh_token):
		return self.__http({
			"grant_type": "refresh_token",
			"refresh_token": refresh_token,
			"client_id": self.client_id,
			"client_secret": self.client_secret
		})

	def __save_auth(self,auth):
		self.db["auth"] = auth
		self.db["ts"] = int(time.time())

	def __check_token(self):
		if not "auth" in self.db:
			self.__save_auth(self.__get_token())
		elif self.db["ts"] + int(self.db["auth"]["expires_in"]) < int(time.time()): # access token has expired
			self.__save_auth(self.__refresh_token(self.db["auth"]["refresh_token"]))

	def cmd(self, cmd):
		conn = httplib.HTTPSConnection(self.host)
		conn.request("GET", "/api/"+cmd+"?access_token="+self.db["auth"]["access_token"])
		response = conn.getresponse()
		if (response.status != 200):
			raise Exception("Invalid response status %s." % response.status)
		return json.loads(response.read())

config = ConfigParser.ConfigParser()

# get the directory where this script resides
mydir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

# read the config file in that dir
config.read(os.path.join(mydir, 'netatmo.conf'))

# netatmo instance
netatmoApi = NetatmoApi(config.get('api', 'client_id'),
						config.get('api', 'client_secret'))

def get_output(csvMode=False, debug=False):
	devicelist = netatmoApi.cmd("devicelist")
	if debug:
		import pprint
		return pprint.pformat(netatmoApi.cmd("devicelist"))
	else:
		values = (
			  devicelist["body"]["devices"][0]["dashboard_data"]["Temperature"]
			, devicelist["body"]["devices"][0]["dashboard_data"]["Humidity"]
			, devicelist["body"]["devices"][0]["dashboard_data"]["Pressure"]
			, devicelist["body"]["devices"][0]["dashboard_data"]["CO2"]
			, devicelist["body"]["modules"][0]["dashboard_data"]["Temperature"]
			, devicelist["body"]["modules"][0]["dashboard_data"]["Humidity"]
		)
		if devicelist:
			return ';'.join(map(str, values)) if csvMode else 'Indoor: %.1f°C (%.0f%%, %1.fmbar, %0.fppm CO2), outdoor: %.1f°C (%.0f%%)' % values

def main():
	# cmd line params handling
	try:
		opts, args = getopt.getopt(sys.argv[1:], ":cd", ["--csv", "--debug"])
	except getopt.GetoptError as err:
		print str(err)
		sys.exit(2)
	csvMode = False
	debug = False
	for o,a in opts:
		if o in ("-c", "--csv"):
			csvMode = True
		elif o in ("-d", "--debug"):
			debug = True
		else:
			assert False, "unhandled option"
	# get the output and send it to the client
	print get_output(csvMode, debug)

if __name__ == "__main__":
	main()
