

import json
import wotkitpy
import random
import sys

if len(sys.argv) != 4:
    raise Exception("Invlid number of arguments. To call this script properlyuse following format:\n\n python test.py  api_url username password");

api_url = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]    

proxy = wotkitpy.WotkitProxy(**{"api_url": api_url, "username": username, "password": password})
sensor_name = "traffic-general"
sensor_id = 42607


proxy.get_sensor_by_id(sensor_id)
proxy.get_sensor_by_name(sensor_name)
proxy.query_all_sensors(**{"tags": "street"})

test_name = "mark_test_" + str(random.randint(0, 92312312))

test_sensor_registration = {
  "name": test_name,
  "tags": [
    "traffic",
    "road"
  ],
  "fields": [
    {
      "required": False,
      "type": "NUMBER",
      "name": "lat",
      "longName": "latitude"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "lng",
      "longName": "longitude"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "direction",
      "longName": "Direction"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "value",
      "longName": "Operational Lanes"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "restrictedlanes",
      "longName": "Restricted Lanes"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "endtime",
      "longName": "End Time"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "starttime",
      "longName": "Start Time"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "updatedtime",
      "longName": "Record Last Updated Time"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "comment",
      "longName": "Comments"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "impact",
      "longName": "Impact on traffic"
    },
    {
      "units": "seconds",
      "required": False,
      "type": "NUMBER",
      "name": "delaytime",
      "longName": "Delay Time"
    },
    {
      "required": False,
      "type": "STRING",
      "name": "occurrence",
      "longName": "Probability of occurrence"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "latfrom",
      "longName": "latitude from"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "lngfrom",
      "longName": "longitude from"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "latto",
      "longName": "latitude to"
    },
    {
      "required": False,
      "type": "NUMBER",
      "name": "lngto",
      "longName": "longitude to"
    }
  ],
  "visibility": "PUBLIC",
  "longitude": -0.113995,
  "longName": "Current planned events that affect traffic",
  "latitude": 51.506178,
  "description": "Sensor data parsed from http://hatrafficinfo.dft.gov.uk/feeds/datex/England/CurrentPlanned/content.xml"
}

full_test_name = username + "." + test_name

proxy.register_sensor(test_sensor_registration)


proxy.delete_sensor(full_test_name)

proxy.update_sensor(sensor_id, {"id": sensor_id, "description": "help", "name": sensor_name, "longName": "UK Traffic Data"})


proxy.subscribe_sensor(sensor_id)
proxy.get_sensor_subscriptions()
proxy.unsubscribe_sensor(sensor_id)


proxy.get_sensor_fields(sensor_id)
proxy.get_sensor_fields(sensor_id, "lng")

proxy.update_sensor_field(sensor_id, "whatever", {"name": "whatever", "type": "NUMBER", "longName": "ideal travel time"})
proxy.delete_sensor_field(sensor_id, "whatever")


proxy.register_sensor(test_sensor_registration)
test_sensor = proxy.get_sensor_by_name(test_name)
if not test_sensor:
    raise Exception("Failed to get just registred sensor")

test_sensor_id = test_sensor["id"]
data = json.loads("""{ "endtime":"2013-08-16T15:00:00+01:00","starttime":"2013-08-16T06:00:00+01:00","recordedtime":"2013-08-05T11:47:44+01:00","latfrom":52.6922,"direction":"southBound","lng":-2.104171,"lngto":-2.104171,"lngfrom":-2.104171,"impact":"freeFlow","latto":52.6922,"delaytime":0,"restrictedlanes":0,"value":2,"occurrence":"certain","comment":"On the M6 southbound exit slip at junction J12 , minor delays are possible due to an entertainment event . Expect disruption until 3:00 pm.","lat":52.6922}""")

proxy.send_data_post_by_name(test_name, data)
proxy.send_data_post(test_sensor_id, data)

bulk_data = json.loads("""[{"timestamp":"2013-08-16T14:00:53.590716Z","endtime":"2013-08-16T15:00:00+01:00","starttime":"2013-08-16T06:00:00+01:00","recordedtime":"2013-08-05T11:47:44+01:00","latfrom":52.6922,"direction":"southBound","lng":-2.104171,"lngto":-2.104171,"lngfrom":-2.104171,"impact":"freeFlow","latto":52.6922,"delaytime":0,"restrictedlanes":0,"value":2,"occurrence":"certain","comment":"On the M6 southbound exit slip at junction J12 , minor delays are possible due to an entertainment event . Expect disruption until 3:00 pm.","lat":52.6922},{"timestamp":"2013-08-16T14:00:53.594578Z","endtime":"2013-08-16T17:00:00+01:00","starttime":"2013-08-16T06:00:00+01:00","recordedtime":"2013-08-07T09:37:29+01:00","latfrom":51.694508,"direction":"northBound","lng":0.423586,"lngto":0.423586,"lngfrom":0.423586,"impact":"heavy","latto":51.694508,"delaytime":600,"restrictedlanes":0,"value":1,"occurrence":"certain","comment":"On the A12 from The M25 towards Ipswich exit slip to the A414 , there are currently delays of 10 mins due to an entertainment event . Expect disruption until 5:00 pm.","lat":51.694508}]""")

proxy.send_bulk_data_put_by_name(test_name, bulk_data)
proxy.send_bulk_data_put(test_sensor_id, bulk_data)

proxy.delete_data(test_sensor_id, "2013-08-16T14:00:53.590716Z")
raw_datas = proxy.get_raw_data(test_sensor_id)

for raw_data in raw_datas:
    timestamp = raw_data.get('timestamp')
    if timestamp == "2013-08-16T14:00:53.590716Z":
        raise Exception("failed to delete data")


proxy.query_sensors(**{"text": "test", "limit": 50})
#print proxy.query_all_sensors(**{"text": "gully"})

proxy.get_formatted_data(test_sensor_id)
"""
try:
    print proxy.get_aggregated_data(**{"before": 1000, "text": "test"})
except:
    print "error in getting aggregated data\n"
    pass
"""


proxy.send_actuator_message(test_sensor_id, **{"message": "testmsg"})

print "subscribing"
subscribed_data = proxy.subscribe_actuator(test_sensor_id)

print subscribed_data

# more to come

proxy.delete_sensor(test_sensor_id)

proxy.get_wotkit_user(username)
proxy.create_wotkit_user({"username": "testuser" + test_name, "password": "test", "firstname": "help", "lastname": "whatever"})
