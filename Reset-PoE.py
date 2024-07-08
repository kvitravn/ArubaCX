import requests
import urllib3
import keyring
import time
import json

#Switches to Login to
ip_add = input("Enter IP address of Switch Stack: ")

#Devices to find in LLDP table
dev_description = "Aruba AP"

#Interface dictionary
dev_list=[]

#PoE Disable Config
poe_dis_json = {
    "config": {
        "admin_disable": True,
    }
}
#PoE Enable Config
poe_en_json = {
  "config": {
    "admin_disable": False,
    }
}

#Write Output to File
file_path = "poe-reset.log"
#Stored creds to log into API
x = keyring.get_credential(service_name="aruba_cx",username="admin")
username = x.username
password = x.password
creds = {"username": username,"password": password}

# Disable warnings we don't have certs for https sessions on switch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Login
session = requests.Session()
login = session.post(f"https://{ip_add}/rest/v10.04/login", data=creds, verify=False)
print(f"This is the login code: {login.status_code}")
print(f"This is the cookie_jar:\n {login.cookies}")

#Get VSF stack members
vsf = session.get(f"https://{ip_add}/rest/v10.11/system/vsf_members", verify=False)
vsf_json = vsf.json()
print(vsf_json)
number_of_switches = len(vsf_json)
print(number_of_switches)
switch_mem = 1
chassis_mem = 1
interface_num = 1

while switch_mem <= number_of_switches:
    if interface_num <= 48:
        switch_mem_str = str(switch_mem)
        chassis_mem_str = str(chassis_mem)
        int_mem_str = str(interface_num)
        int_number = switch_mem_str+"/"+chassis_mem_str+"/"+int_mem_str
        #Get LLDP info for interface
        get_lldp = session.get(f"https://{ip_add}/rest/v10.11/system/interfaces/{switch_mem_str}%2F{chassis_mem_str}%2F{int_mem_str}/lldp_neighbors?attributes=&depth=2", verify=False)
        lldp_data = get_lldp.json()
        print(lldp_data)
        for key in lldp_data:
            chassis_description = lldp_data[key]["neighbor_info"]["chassis_description"]
            print(chassis_description)
            if dev_description in chassis_description:
                dev_list.append(int_number)
            
        interface_num += 1
        if interface_num >= 48:
            interface_num = 1
            switch_mem +=1        
    else:
        print(dev_list)

for int in dev_list:
    module_int = int.split('/')
    print(module_int)
    poe_disable = session.put(f"https://{ip_add}/rest/v10.11/system/interfaces/{module_int[0]}%2F{module_int[1]}%2F{module_int[2]}/poe_interface", json=poe_dis_json, verify=False)
    if poe_disable.status_code == 200:
        poe_disable_log = (f'{int} PoE is Disabled')
    else:
        poe_disable_log = (f'{int} PoE failed to disable' + ' '+ poe_disable.text)
    time.sleep(2)
    poe_enable = session.put(f"https://{ip_add}/rest/v10.11/system/interfaces/{module_int[0]}%2F{module_int[1]}%2F{module_int[2]}/poe_interface", json=poe_en_json, verify=False)
    if poe_enable.status_code == 200:
        poe_enable_log = (f'{int} PoE is Enabled')
    else:
        poe_enable_log = (f'{int} PoE failed to enable' + ' '+ poe_enable.text)
    poe_logs = [
        poe_disable_log,
        poe_enable_log
    ]
    with open (file_path, 'a') as file:
        for line in poe_logs:
            file.write(line + "\n")
#Logout
logout = session.post(f"https://{ip_add}/rest/v10.04/logout", verify=False)
print(f"This is the logout code: {logout.status_code}")