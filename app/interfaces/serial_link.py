"""Arduino MEGA serial link contract. SAFETY-CRITICAL
Changing this file is classified 'interface-affecting' and trips the
Power org's interface-board policy. Kept tiny on purpose."""
BAUD = 115200
PORT = "/dev/ttyACM0"
MESSAGE_FORMAT = "sensor_id:int,value:float,timestamp:int"
