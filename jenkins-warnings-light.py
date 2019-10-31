import datetime
import requests
import time
import sys
import ctypes

POLL_INTERVAL_SECONDS = 3
FAILED_JOB_COLORS = ['yellow', 'red']
WORKDAY_START_TIME = datetime.time(8, 45)
WORKDAY_END_TIME = datetime.time(18, 0)
DEVICE_ID = '3D0V2'

LIBFILE = './USB_RELAY_DEVICE.dll'
ON = "ON"
OFF = "OFF"

class L: pass   # Global object for the DLL
setattr(L, "dll", None)

def during_working_hours():
    now = datetime.datetime.today()
    return now.weekday() in range(0,5) and WORKDAY_START_TIME < now.time() and now.time() < WORKDAY_END_TIME

def get_number_of_failed_jenkins_jobs(view_url):
    req = requests.get(view_url + '/api/json?tree=jobs[color]')
    if req.status_code != 200:
        print("Failed to get status of Jenkins jobs, returned status: {}, content:\n{}".format(req.status_code, req.text), flush=True)
    
    job_results = [job for job in req.json()['jobs'] if job['color'] in FAILED_JOB_COLORS]
    return len(job_results)
	
def charpToString(charp):
  return str(ctypes.string_at(charp), 'ascii')
def stringToCharp(s) :   
  return bytes(s, "ascii")

def exc(msg):  return Exception(msg)

def fail(msg) : raise exc(msg)
  
def loadLib():
  # Load the C DLL ...
  if not L.dll :
    print("Loading DLL: %s" % (LIBFILE))
    try:
      L.dll = ctypes.CDLL(LIBFILE)
    except OSError:  
      fail("Failed load lib")
  else:
    print("lib already open")

usb_relay_lib_funcs = [
  # TYpes: h=handle (pointer sized), p=pointer, i=int, e=error num (int), s=string
  ("usb_relay_device_enumerate",               'h', None),
  ("usb_relay_device_close",                   'e', 'h'),
  ("usb_relay_device_open_with_serial_number", 'h', 'si'),
  ("usb_relay_device_get_num_relays",          'i', 'h'),
  ("usb_relay_device_get_id_string",           's', 'h'),
  ("usb_relay_device_next_dev",                'h', 'h'),
  ("usb_relay_device_get_status_bitmap",       'i', 'h'),
  ("usb_relay_device_open_one_relay_channel",  'e', 'hi'),
  ("usb_relay_device_close_one_relay_channel", 'e', 'hi'),
  ("usb_relay_device_close_all_relay_channel", 'e', None)
  ]
      
      
def getLibFunctions():
  """ Get needed functions and configure types; call lib. init.
  """
  assert L.dll
  
  #Get lib version (my extension, not in the original dll)
  libver = L.dll.usb_relay_device_lib_version()  
  print("%s version: 0x%X" % (LIBFILE, libver))
  
  ret = L.dll.usb_relay_init()
  if ret != 0 : fail("Failed lib init!")
  
  """
  Tweak imported C functions
  This is required in 64-bit mode. Optional for 32-bit (pointer size=int size)
  Functions that return and receive ints or void work without specifying types.
  """
  ctypemap = { 'e': ctypes.c_int, 'h':ctypes.c_void_p, 'p': ctypes.c_void_p,
            'i': ctypes.c_int, 's': ctypes.c_char_p}
  for x in usb_relay_lib_funcs :
      fname, ret, param = x
      try:
        f = getattr(L.dll, fname)
      except Exception:  
        fail("Missing lib export:" + fname)

      ps = []
      if param :
        for p in param :
          ps.append( ctypemap[p] )
      f.restype = ctypemap[ret]
      f.argtypes = ps
      setattr(L, fname, f)
      
def openDevById(deviceId):
  #Open by known ID:
  print("Opening " + deviceId)
  h = L.usb_relay_device_open_with_serial_number(stringToCharp(deviceId), 5)
  if not h: fail("Cannot open device with id=" + deviceId)
  global numch
  numch = L.usb_relay_device_get_num_relays(h)
  if numch <= 0 or numch > 8 : fail("Bad number of channels, can be 1-8")
  print("Number of relays on device with ID=%s: %d" % (deviceId, numch))
  return h
 
def unloadLib():
  global L
  L.dll.usb_relay_exit()
  L.dll = None
  print("Lib closed")

def closeDev(device):
  L.usb_relay_device_close(device)
	
if __name__ == '__main__':
    if len(sys.argv) == 1:
        raise Exception("No Jenkins view URL passed. Usage: python jenkins-failed-build-warning-light.py http://jenkins.example.com/view/Main")
    
    view_url = sys.argv[1]
    print("Start monitoring Jenkins view {}".format(view_url), flush=True)
    loadLib()
    getLibFunctions()
    device = openDevById(DEVICE_ID)
	
    L.usb_relay_device_close_all_relay_channel(device)
	
    current_state = OFF
    try:
        while True:
            if not during_working_hours():
                try:
                    number_of_failed_jobs = get_number_of_failed_jenkins_jobs(view_url)
                    if number_of_failed_jobs == 0:
                        print("Everything is OK", flush=True)
                        current_state = OFF
                        L.usb_relay_device_close_one_relay_channel(device, 1)
                    else:
                        print("There are {} failing jobs".format(number_of_failed_jobs, flush=True))
                        current_state = ON
                        L.usb_relay_device_open_one_relay_channel(device, 1)
                except Exception as e:
                    print("Failed to get update status of Jenkins jobs: {}".format(str(e)), flush=True)
            else:
                print("Nobody is in the office", flush=True)
                if current_state == ON:
                    current_state = OFF
                    L.usb_relay_device_close_all_relay_channel(device)
                
            time.sleep(POLL_INTERVAL_SECONDS)
    except (SystemExit, KeyboardInterrupt):
        L.usb_relay_device_close_all_relay_channel(device)
    finally:
        unloadLib()
        closeDev(device)
