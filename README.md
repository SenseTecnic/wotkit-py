wotkit-py
=========

Python client for the wotkit. This client uses the requests library to connect to the WoTKiT using HTTP.


Installation
==========
The client can easily be installed to a Python (virtual) environment: 

```
pip install wotkitpy
```

Example Usage
===========

```
from wotkitpy import WotkitProxy
wotkit_config = {"api_url": "api_url_here",
                 "username": "username_here",
                 "password": "password_here"
                 }
wotkit_proxy = WotkitProxy(**wotkit_config)

sensor_data = wotkit_proxy.get_sensor_by_id(SENSOR_ID)
```

