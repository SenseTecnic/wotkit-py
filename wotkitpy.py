"""A Python client for communicating to the WoTKit API using the requests library.

.. module:: wotkitpy
.. moduleauthor:: Mark Duppenthaler <mduppes@gmail.com>

The MIT License (MIT)

Copyright (c) 2013, Sensetecnic Systems.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

import json
import requests

from datetime import datetime
import logging
import traceback

if __name__ == "main":
    logging.basicConfig()
    
log = logging.getLogger(__name__)

QUERY_MAX_SENSORS = 1000
REGISTER_MAX_SENSORS = 100

class WotkitException(Exception):
    pass

class WotkitConfigException(Exception):
    pass

def _get_required_field(field, **kwargs):
    """Returns settings[field]. If it doesn't exist it raises an exception """
    value = kwargs.get(field, None)
    if not value:
        raise WotkitConfigException("Missing required argument %s." % field)
    return value

def get_wotkit_timestamp():
    """Returns the current timestamp in the ISO format WoTKit recognizes.
    :rtype: str. """
    dt = datetime.utcnow().isoformat()
    if '.' not in dt:
        dt = dt + '.000000'
    
    return dt + 'Z'

def _load_response_json(response):
    """Load a the JSON response into Python format."""    
    try:
        return json.loads(response.text, encoding = response.encoding)
    except Exception as e:
        raise WotkitException("Invalid JSON. Error: " + str(e))
     
class WotkitProxy():
    """Acts as a network proxy to the WotKit based on the configuration supplied.
    
    Example:
    wotkit_proxy = WotkitProxy( WOTKIT_URL_HERE, USERNAME, PASSWORD)
    wotkit_proxy.get_sensor_by_id(SENSOR_ID_HERE)

    """
    
    def __init__(self, **kwargs):
        """Configures the settings necessary for connecting to the WoTKit.

        :param api_url: The base url for the WoTKit API. 
        :type api_url: str. 
        :param username: The default username or key ID that will be used. (OPTIONAL)
        :type username: str.
        :param password: The default password or key password that will be used. (OPTIONAL)
        :type password: str.

        :raises: WotkitConfigException """
        self.api_url = _get_required_field("api_url", **kwargs)
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
    
    def _get_login_credentials(self, username = None, password = None):
        """Returns a (username, password) tuple. Uses the defaults supplied upon initialization if username or password are empty."""
        if username and password:
            return (username, password)
        else:
            return (self.username, self.password)
    
    def get_sensor_by_name(self, sensor_name, username = None, password = None):
        '''Get a sensor by name.

        :param sensor_name: Sensor name to get (no username component prepended, ie. if the full name is admin.sensor_name, use sensor_name).
        :type sensor_name: str.
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :rtype: dict representing sensor data, or None if sensor does not exist. 
        :raises: WotkitException if a status code is not 200 or 404'''
        
        user, pwd = self._get_login_credentials(username, password)
        return self.get_sensor_by_id(user + "." + sensor_name, user, pwd)

    def get_sensor_by_id(self, sensor_id, username = None, password = None):
        '''Get a sensor by ID.

        :param sensor_id: Sensor ID to get.
        :type sensor_id: str.
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :rtype: dict representing sensor data, or None if sensor does not exist. 
        :raises: WotkitException if a status code is not 200 or 404'''
        
        sensor_id = str(sensor_id)
        auth_credentials = self._get_login_credentials(username, password)
        
        url = self.api_url+'/sensors/'+sensor_id
        try:
            response = requests.get(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in getting sensor " + sensor_id + ". Error: " + str(e))

        if response.status_code == 200:
            log.debug("Success getting sensor " + sensor_id)
            return _load_response_json(response)
        elif response.status_code == 404:
            log.debug("Sensor doesn't exist " + sensor_id)
            return None
        else:
            raise WotkitException("Error in getting sensor " + sensor_id + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def query_all_sensors(self, **kwargs):
        """Searches all sensors that match the search query. A wrapper function on top of query_sensors that performs multiple API calls to retrieve all matches for search results more than 1000 sensors.

        .. note:: When multiple API calls are made the search result could potentially be off sync with the WoTKit due to updates occuring to the sensors as the search is being performed.

        :param scope: "all", "subscribed", or "contributed". "all" - all sensors the current user has access to. "subscribed" - the sensors the user has subscribed to. "contributed" - the sensors the user has contributed to the system.
        :type scope: str.
        :param tags: list of comma separated tags.
        :type tags: str.
        :param orgs: list of comma separated organization names.
        :type orgs: str.
        :param visibility: filter by the visibility of the sensors, either of "public", "organization", or "private"
        :type visibility: str.
        :param text: text to search for in the name, long name and description.
        :type text: str.
        :param active: when true, only returns sensors that have been updated in the last 15 minutes.
        :type active: bool.
        :param location: geo coordinates for a bounding box to search within. Format is yy.yyy,xx.xxx:yy.yyy,xx.xxx, and the order of the coordinates are North,West:South,East. Example: location=56.89,-114.55:17.43,-106.219.
        :type location: str.

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.

        :rtype: list of dict's containing each sensor's data. Empty list of no matches. 
        :raises: WotkitException if a status code is not 200's"""
        sensors = {}
        kwargs["offset"] = 0
        kwargs["limit"] = QUERY_MAX_SENSORS
        while True:
            result_sensors = self.query_sensors(**kwargs)
            if not result_sensors:
                break
            log.debug("Searching.. found %d sensors.." % len(result_sensors))
            for result_sensor in result_sensors:
                sensors[result_sensor['id']] = result_sensor
            kwargs["offset"] += QUERY_MAX_SENSORS
        return sensors.items()

    def query_sensors(self, **kwargs):
        """Searches sensors that match the search query. 
        
        :param scope: "all", "subscribed", or "contributed". "all" - all sensors the current user has access to. "subscribed" - the sensors the user has subscribed to. "contributed" - the sensors the user has contributed to the system.
        :type scope: str.
        :param tags: list of comma separated tags.
        :type tags: str.
        :param orgs: list of comma separated organization names.
        :type orgs: str.
        :param visibility: filter by the visibility of the sensors, either of "public", "organization", or "private"
        :type visibility: str.
        :param text: text to search for in the name, long name and description.
        :type text: str.
        :param active: when true, only returns sensors that have been updated in the last 15 minutes.
        :type active: bool.
        :param location: geo coordinates for a bounding box to search within. Format is yy.yyy,xx.xxx:yy.yyy,xx.xxx, and the order of the coordinates are North,West:South,East. Example: location=56.89,-114.55:17.43,-106.219.
        :type location: str.

        :param offset: offset into list of sensors for paging.
        :type offset: int.
        :param limit: limit to show for paging. The maximum number of sensors to display is 1000.
        :type limit: int.

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.

        :raises: WotkitException if a status code is not 200's"""

        auth_credentials = self._get_login_credentials(kwargs.get("username"), kwargs.get("password"))
        
        valid_params = set(["scope", "tags", "orgs", "visibility", "text", "active", "location", "offset", "limit"])        
        search_params = dict([ (key, str(value)) for key, value in kwargs.items() if key in valid_params ])
        
        try:
            response = requests.get(self.api_url + "/sensors", params=search_params, auth=auth_credentials)
        except Exception as e:
            raise WotkitException("Error in querying sensor. Params: " + str(search_params) + ", Error: " + str(e))
        
        if not response.ok:
            raise WotkitException("Error in querying sensor. Params: " + str(search_params) + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
        
        return _load_response_json(response)

    def register_sensor(self, registration_dict, username = None, password = None):
        """Registers a new sensor to the WoTKit. 
        
        :param registration_dict: A Python dictionary that represents the JSON registration data. (ie. json.dumps(registration_dict) must not fail).  "name", "longName", and "description" are required. "longitude", "latitude" are optional and will default to 0. "visibility" is optional and will default to "public", if it is "organization" a valid "organization" must be supplied. "tags", "fields", "organization" are optional. The sensor name must be at least 4 characters long, contain only lowercase letters, numbers, dashes and underscores, and can start with a lowercase letter or an underscore only.  
        :type registration_dict: dict. 
        
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        auth_credentials = self._get_login_credentials(username, password)
        url = self.api_url+'/sensors'
        json_data = json.dumps(registration_dict)
        headers = {"content-type": "application/json"}
        try:
            response = requests.post(url = url, auth=auth_credentials, data = json_data, headers = headers)
        except Exception as e:
            raise WotkitException("Error in registering sensor to url: " + url + ". Registration Data: " + str(registration_dict) + ". Error: " + str(e))
        
        if response.ok:
            log.debug("Success registering sensor for sensor: " + str(registration_dict["name"]))
            return True
        else:
            msg = "Error while registering sensor '%s' to url: %s \nResp: %s"
            resp = json.loads(response.content)
            raise WotkitException(msg % (registration_dict["name"], url, resp))

    def register_multiple_sensors(self, registration_list, username = None, password = None):
        """Registers multiple new sensor to the WoTKit. If there are more than 100 sensor's in registration_list, performs multiple bulk registration requests to the WoTKit.
        
        :param registration_list: A Python list that represents the JSON registration data. (ie. json.dumps(registration_dict) must not fail). For more detail look at register_sensor since the registration_list is just a list of single registration_dict's. 
        :type registration_list: list of dict 
        
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        auth_credentials = self._get_login_credentials(username, password)
        url = self.api_url+'/sensors'

        headers = {"content-type": "application/json"}
        
        for registration_chunk in [ registration_list[i:i+REGISTER_MAX_SENSORS] for i in range(0, len(registration_list), REGISTER_MAX_SENSORS) ]:
            json_data = json.dumps(registration_chunk)
            try:
                response = requests.put(url = url, auth=auth_credentials, data = json_data, headers = headers)
            except Exception as e:
                raise WotkitException("Error in registering multiple sensors to url: " + url + ". Registration Chunk: " + str(registration_chunk) + ". Error: " + str(e))

            if not response.ok:
                msg = "Error in registering multiple sensors to url: " + url + ". Registration Chunk: " + str(registration_chunk) + ". Code: " + str(response.status_code) + ". Response: " + json.loads(response.text)
                raise msg

        log.debug("Success registering multiple sensors to url: " + url)
        return True
        
    def update_sensor(self, sensor_id, update_dict, username = None, password = None):
        """Updates a sensor on the WoTKit. 

        :param sensor_id: Sensor ID to update.
        :type sensor_id: str.
        :param update_dict: A Python dictionary that represents the JSON update data. (ie. json.dumps(update_dict) must not fail). Look at registration for more details. Updating a sensor is the same as registering a new sensor other than PUT is used and the sensor name or id is included in the URL. 
        :type update_dict: dict. 
        
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        auth_credentials = self._get_login_credentials(username, password)
        sensor_id = str(sensor_id)
        url = self.api_url + "/sensors/" + sensor_id
        json_data = json.dumps(update_dict)
        headers = {"content-type": "application/json"}
        try:
            response = requests.put(url = url, auth=auth_credentials, data = json_data, headers = headers)
        except Exception as e:
            raise WotkitException("Error in updating sensor to url: " + url + ". Update Data: " + str(update_dict) + ". Error: " + str(e))
        
        if response.ok:
            log.debug("Success updating sensor schema for url " + url)
            return True
        else:
            raise WotkitException("Error while updating sensor %s to url: %s  " % (sensor_id, url) + ", Reason: " + str(response.text))


    def delete_sensor(self, sensor_id, username = None, password = None):
        """Delete sensor from WoTKit.
        
        :param sensor_id: Sensor ID to delete.
        :type sensor_id: str.
        
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 204"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/sensors/" + sensor_id
        auth_credentials = self._get_login_credentials(username, password)
        
        try:
            delete_response = requests.delete(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in deleting sensor at url: " + url + ". Error: " + str(e)) 
        
        if delete_response.ok:
            log.debug("Deleted sensor %s" % sensor_id)
            return True
        else:
            msg = "Failed to delete sensor %s: code: %d. Message: %s" % (sensor_id, delete_response.status_code, delete_response.text.encode(delete_response.encoding))
            raise WotkitException(msg)

    def get_sensor_subscriptions(self, username = None, password = None):
        """View sensors that user is subscribed to.
        
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's
        :rtype: list of sensors subscribed"""
        
        url = self.api_url + "/subscribe"
        auth_credentials = self._get_login_credentials(username, password)
        try:
            response = requests.get(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in getting sensor subscriptions at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in getting subscriptions\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
        
    def subscribe_sensor(self, sensor_id, username = None, password = None):
        """Subscribe to sensor for user.

        :param sensor_id: Sensor ID to subscribe.
        :type sensor_id: str.
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/subscribe/" + sensor_id
        auth_credentials = self._get_login_credentials(username, password)
        try:
            response = requests.put(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in sensor subscribe at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return True
        else:
            raise WotkitException("Error in sensor subscribe for sensor: " + sensor_id + ".\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
            
    def unsubscribe_sensor(self, sensor_id, username = None, password = None):
        """Unsubscribe sensor for user.

        :param sensor_id: Sensor ID to unsubscribe.
        :type sensor_id: str.
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/subscribe/" + sensor_id
        auth_credentials = self._get_login_credentials(username, password)
        try:
            response = requests.delete(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in sensor unsubscribe at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return True
        else:
            raise WotkitException("Error in sensor unsubscribe for sensor: " + sensor_id + ".\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
    
    def get_sensor_fields(self, sensor_id, field_name = None, username = None, password = None):
        """Get sensor fields.

        :param sensor_id: Sensor ID to get fields.
        :type sensor_id: str.
        :param field_name: If specified, only gets this field name.
        :type field_name: str
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's
        :rtype: list of sensor fields, or dict of sensor field if field_name was specified"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/sensors/" + sensor_id + "/fields"
        if field_name:
            url += "/" + field_name
        auth_credentials = self._get_login_credentials(username, password)
        
        try:
            response = requests.get(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in getting sensor fields at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in getting sensor fields for sensor: " + sensor_id + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
    
    def update_sensor_field(self, sensor_id, field_name, field_data, username = None, password = None):
        """Update sensor field.

        :param sensor_id: Sensor ID to update field.
        :type sensor_id: str.
        :param field_name: Updates this field name. If it doesn't exist, it creates a new field.
        :type field_name: str
        :param field_data: Field data. "name" and "type" are required "name" in an existing field cannot be updated. 
        :type field_data: dict 
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/sensors/" + sensor_id + "/fields/" + field_name

        auth_credentials = self._get_login_credentials(username, password)
        json_data = json.dumps(field_data)
        try:
            response = requests.put(url, data = json_data, auth = auth_credentials, headers={"content-type": "application/json"})
        except Exception as e:
            raise WotkitException("Error in updating sensor field at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return True
        else:
            raise WotkitException("Error in updating sensor field at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def delete_sensor_field(self, sensor_id, field_name, username = None, password = None):
        """Delete sensor field.

        :param sensor_id: Sensor ID to delete field.
        :type sensor_id: str.
        :param field_name: Delete this field name. None of the default fields can be deleted (lat, lng, value, message).
        :type field_name: str

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        
        sensor_id = str(sensor_id)
        url = self.api_url + "/sensors/" + sensor_id + "/fields/" + field_name

        auth_credentials = self._get_login_credentials(username, password)
        try:
            response = requests.delete(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in deleting sensor field at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return True
        else:
            raise WotkitException("Error in deleting sensor field at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
      
    def send_data_post_by_name(self, sensor_name, data, username = None, password = None):
        """ Wrapper around send_data_post that allows sending new data to a given sensor name .
        
        :param sensor_name: Sensor name to send data to (no username component prepended, ie. if the full name is admin.sensor_name, use sensor_name).
        :type sensor_name: str.
        :param data: Data to send to this sensor. 
        :type data: dict
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""

        user, pwd = self._get_login_credentials(username, password)
        return self.send_data_post(user + "." + sensor_name, data, user, pwd)

    def send_data_post(self, sensor_id, data, username = None, password = None):
        """ Send new data to a sensor.
        
        :param sensor_id: Sensor ID to send data to.
        :type sensor_id: str.
        :param data: Data to send to this sensor. 
        :type data: dict
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        #use SenseTecnic
        #log.info("Sending data to wotkit for sensor " + sensor + ": " + str(attributes))
        sensor_id = str(sensor_id)
        auth_credentials = self._get_login_credentials(username, password)
        url = self.api_url+'/sensors/'+sensor_id+'/data'
        try:
            response = requests.post(url = url, auth=auth_credentials, data = data)
        except Exception as e:
            raise WotkitException("Error in sending new data by POST to sensor at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            log.debug("Success sending POST sensor data to url: " + url)
            return True
        else:
            raise WotkitException("Error in sending new data by POST to sensor at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
            


    def send_bulk_data_put_by_name(self, sensor_name, data, username = None, password = None):
        """ Wrapper around send_bulk_data_put that allows sending new data to a given sensor name .

        :param sensor_name: Sensor name to send data to (no username component prepended, ie. if the full name is admin.sensor_name, use sensor_name).
        :type sensor_name: str.
        :param data: Data to send to this sensor. Compared with sending single new data by POST, each data item must contain a timestamp. The current timestamp can be obtained by calling get_wotkit_timestamp().
        :type data: list of dict
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""

        user, pwd = self._get_login_credentials(username, password)
        self.send_bulk_data_put(user + "." + sensor_name, data, user, pwd)
        

    def send_bulk_data_put(self, sensor_id, data, username = None, password = None):
        """ Send multiple data dictionaries to WoTKit. 
        .. note:: data sent this way is not processed in real time. 
        
        :param sensor_id: Sensor ID to send data to.
        :type sensor_id: str.
        :param data: Data to send to this sensor. Compared with sending single new data by POST, each data item must contain a timestamp. The current timestamp can be obtained by calling get_wotkit_timestamp().
        :type data: list of dict
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
        sensor_id = str(sensor_id)
        json_data = json.dumps(data)
        
        auth_credentials = self._get_login_credentials(username, password)
        url = self.api_url+'/sensors/'+sensor_id+'/data'
        
        try:
            response = requests.put(url = url, auth=auth_credentials, data = json_data, headers = {"content-type": "application/json"})
        except Exception as e:
            raise WotkitException("Error in sending bulk sensor data via PUT to url: " + url + ". Error: " + str(e))
        if response.ok:
            log.debug("Success sending bulk PUT data to sensor url: " + url)
            return True
        else:
            raise WotkitException("Error in sending bulk data by PUT to sensor at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
    
    def delete_data(self, sensor_id, timestamp, username = None, password = None):
        """ Delete all data corresponding with timestamp.

        :param sensor_id: Sensor ID to delete data from.
        :type sensor_id: str.
        :param timestamp: Timestamp in numeric UNIX timestamp or ISO form string.
        :type timestamp: int or str
        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
        :raises: WotkitException if a status code is not 200's"""
    
        sensor_id = str(sensor_id)
        
        auth_credentials = self._get_login_credentials(username, password)
        url = self.api_url+'/sensors/'+sensor_id+'/data/' + str(timestamp)
        
        try:
            response = requests.delete(url = url, auth=auth_credentials)
        except Exception as e:
            raise WotkitException("Error in deleting sensor data to url: " + url + ". Error: " + str(e))
        if response.ok:
            log.debug("Success deleting data to sensor url: " + url)
            return True
        else:
            raise WotkitException("Error in deleting sensor data at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def get_raw_data(self, sensor_id, **kwargs):
        """Get raw data from a WoTKit sensor.
        
        :param sensor_id: Sensor ID to get data from.
        :type sensor_id: str.
        
        :param start: the absolute start time of the range of data selected in milliseconds. (Defaults to current time.) May only be used in combination with another parameter.
        :type start: int
        :param end: the absolute end time of the range of data in milliseconds
        :type end: int
        :param after: the relative time after the start time, e.g. after=300000 would be 5 minutes after the start time (Start time MUST also be provided.)
        :type after: int
        :param afterE: the number of elements after the start element or time. (Start time MUST also be provided.)
        :type afterE: int
        :param before: the relative time before the start time. E.g. data from the last hour would be before=3600000 (If not provided, start time default to current time.)
        :type before: int
        :param beforeE: the number of elements before the start time. E.g. to get the last 1000, use beforeE=1000 (If not provided, start time default to current time.)
        :type beforeE: int
        :param reverse: true: order the data from newest to oldest; false (default):order from oldest to newest
        :type reverse: bool

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
            
        :raises: WotkitException if a status code is not 200's
        :rtype: list of sensor data"""
        
        sensor_id = str(sensor_id)
        auth_credentials = self._get_login_credentials(kwargs.get("username"), kwargs.get("password"))

        valid_params = set(["start", "end", "after", "afterE", "before", "beforeE", "reverse"])
        search_params = dict([ (key, str(value)) for key, value in kwargs.items() if key in valid_params ])
        url = self.api_url+'/sensors/'+sensor_id+'/data'
        try:
            response = requests.get(url, auth = auth_credentials, params=search_params)
        except Exception as e:
            raise WotkitException("Error in getting raw data at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in getting raw data at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def get_formatted_data(self, sensor_id, **kwargs):
        """Get formatted data from a WoTKit sensor suitable for Google Visualizations.
        
        :param sensor_id: Sensor ID to get data from.
        :type sensor_id: str.
        
        Same parameters as get_raw_data. Additionally:

        :param tqx: A set of colon-delimited key/value pairs for standard parameters
        :type tqx: str
        :param tq: A SQL clause to select and process data fields to return
        :type tq: str
            
        :raises: WotkitException if a status code is not 200's
        :rtype: str that is javascript"""
        
        sensor_id = str(sensor_id)
        auth_credentials = self._get_login_credentials(kwargs.get("username"), kwargs.get("password"))

        valid_params = set(["start", "end", "after", "afterE", "before", "beforeE", "reverse", "tqx", "tq"])
        search_params = dict([ (key, str(value)) for key, value in kwargs.items() if key in valid_params ])
        url = self.api_url+'/sensors/'+sensor_id+'/dataTable'
        try:
            response = requests.get(url, auth = auth_credentials, params=search_params)
        except Exception as e:
            raise WotkitException("Error in getting formatted data at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return response.text.encode(response.encoding)
        else:
            raise WotkitException("Error in getting formatted data at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def get_aggregated_data(self, **kwargs):
        """Get data from multiple sensors queried using the same parameters.
        
        :param scope: "all", "subscribed", or "contributed". "all" - all sensors the current user has access to. "subscribed" - the sensors the user has subscribed to. "contributed" - the sensors the user has contributed to the system.
        :type scope: str.
        :param tags: list of comma separated tags.
        :type tags: str.
        :param orgs: list of comma separated organization names.
        :type orgs: str.
        :param visibility: filter by the visibility of the sensors, either of "public", "organization", or "private"
        :type visibility: str.
        :param text: text to search for in the name, long name and description.
        :type text: str.
        :param active: when true, only returns sensors that have been updated in the last 15 minutes.
        :type active: bool.
        :param start: the absolute start time of the range of data selected in milliseconds. (Defaults to current time.) May only be used in combination with another parameter.
        :type start: int
        :param end: the absolute end time of the range of data in milliseconds
        :type end: int
        :param after: the relative time after the start time, e.g. after=300000 would be 5 minutes after the start time (Start time MUST also be provided.)
        :type after: int
        :param afterE: the number of elements after the start element or time. (Start time MUST also be provided.)
        :type afterE: int
        :param before: the relative time before the start time. E.g. data from the last hour would be before=3600000 (If not provided, start time default to current time.)
        :type before: int
        :param beforeE: the number of elements before the start time. E.g. to get the last 1000, use beforeE=1000 (If not provided, start time default to current time.)
        :type beforeE: int
        :param orderBy: "sensor" groups by sensor id or "time" orders by timestamp (default). 
        :type orderBy: str
        :raises: WotkitException if a status code is not 200's
        :rtype: list of sensor data"""
            
        valid_params = set(["start", "end", "after", "afterE", "before", "beforeE", "orderBy", "scope", "tags", "orgs", "visibility", "text", "active"])        
        search_params = dict([ (key, str(value)) for key, value in kwargs.items() if key in valid_params ])
        url = self.api_url+'/data'

        auth_credentials = self._get_login_credentials(kwargs.get("username"), kwargs.get("password"))

        valid_params = set(["start", "end", "after", "afterE", "before", "beforeE", "reverse"])
        search_params = dict([ (key, str(value)) for key, value in kwargs.items() if key in valid_params ])

        try:
            response = requests.get(url, auth = auth_credentials, params=search_params)
        except Exception as e:
            raise WotkitException("Error in getting aggregated data at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in getting aggregated data at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    def send_actuator_message(self, sensor_id, **kwargs):
        """ Send actuator message to a sensor. 
        
        :param sensor_id: Sensor ID 
        :type sensor_id: str.

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
            
        :raises: WotkitException if a status code is not 200's"""
                             
        sensor_id = str(sensor_id)
        url = self.api_url+'/sensors/' + sensor_id + "/message"
        auth_credentials = self._get_login_credentials(kwargs.pop("username", None), kwargs.pop("password", None))

        try:
            response = requests.post(url, auth = auth_credentials, params=kwargs)
        except Exception as e:
            raise WotkitException("Error in sending actuator message at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return True
        else:
            raise WotkitException("Error in sending catuator message at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
                             
    def subscribe_actuator(self, sensor_id, **kwargs):
        """ Subscribe to actuator. 
        
        :param sensor_id: Sensor ID 
        :type sensor_id: str.

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
            
        :raises: WotkitException if a status code is not 200's
        :rtype: dict containing subscription id"""
                             
        sensor_id = str(sensor_id)
        url = self.api_url+'/control/sub/' + sensor_id
        auth_credentials = self._get_login_credentials(kwargs.pop("username", None), kwargs.pop("password", None))

        try:
            response = requests.post(url, auth = auth_credentials, params=kwargs)
        except Exception as e:
            raise WotkitException("Error in subscribing to actuator at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in subscribing to actuator at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))
                             
    def query_actuator(self, subscription_id, wait_time, **kwargs):
        """ Query actuator
        
        :param subscription_id: Subscription ID for actuator
        :type subscription_id: str.
	:param wait_time: Seconds to wait for message, Max 20.
	:type wait_time: int

        :param username: If provided with password, overrides the default login credentials supplied on initialization.
        :type username: str.
        :param password: Used in combination with username.
        :type password: str.
            
        :raises: WotkitException if a status code is not 200's
        :rtype: dict of control messages"""
                             
        subscription_id = str(subscription_id)
        url = self.api_url+'/control/sub/' + subscription_id + "?wait=" + str(wait_time)
        auth_credentials = self._get_login_credentials(kwargs.pop("username", None), kwargs.pop("password", None))

        try:
            response = requests.get(url, auth = auth_credentials)
        except Exception as e:
            raise WotkitException("Error in querying actuator at url: " + url + ". Error: " + str(e))
        
        if response.ok:
            return _load_response_json(response)
        else:
            raise WotkitException("Error in querying actuator at url: " + url + "\n Response Code: " + str(response.status_code) + "\n Response Text: " + response.text.encode(response.encoding))

    """ Admin functions """
    def get_wotkit_user(self, user_id, username = None, password = None):
        '''Get wotkit user with user_id. Requires admin credentials in WotkitConfig'''
        user_id = str(user_id)
        url = self.api_url + "/users/" + user_id
        auth_credentials = self._get_login_credentials(username, password)
        response = requests.get(url, auth = auth_credentials)
        
        if not response.ok:
            log.info("Wotkit account username %s not found." % user_id)
            return None 
        else:
            return json.loads(response.text)
    
    def create_wotkit_user(self, data, username = None, password = None):
        '''Creates user given in data dictionary. Requires admin credentials in WotkitConfig'''
        url = self.api_url + "/users"
        auth_credentials = self._get_login_credentials(username, password)
        json_data = json.dumps(data)
        headers = {"content-type": "application/json"}
        
        response = requests.post(url, auth = auth_credentials, data = json_data, headers = headers)
        
        if response.ok:
            log.info("Created wotkit account: " + str(data))
            return True
        else:
            msg = "Failed to create wotkit account: " + str(data) + ", code: " + str(response.status_code) + "message: " + response.text.encode(response.encoding)
            log.warning(msg)
            raise WotkitException(msg)
    
    def update_wotkit_user(self, user_id, data, username = None, password = None):
        '''Updates user user_id with data dictionary. Requires admin credentials in WotkitConfig'''
        user_id = str(user_id)
        url = self.api_url + "/users/" + user_id
        auth_credentials = self._get_login_credentials(username, password)
        json_data = json.dumps(data)
        headers = {"content-type": "application/json"}
        response = requests.put(url, auth = auth_credentials, data = json_data, headers = headers)
        
        if response.ok:
            log.info("Updated wotkit account: " + str(data))
            return True
        else:
            log.warning("Failed to update wotkit account: " + str(data) + ", code: " + str(response.status_code) + ", reason: " + str(response.text))
            log.warning(response.text)
            raise WotkitException(response.text)
