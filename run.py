import os
import json
import subprocess
import datetime
import argparse
import numpy as np
from netaddr import IPNetwork

asn_database = json.load(open("bgp_database/netblocks_database.json"))
config_file = json.load(open("ports-config.json"))
batch_len = 4

database = {
    "last_scan" : "",
    "scanned_category" : [],
    "data" : {}
}

all_netblocks = []


parser = argparse.ArgumentParser()
parser.add_argument("-a", "--asn", help = "add ASN number")
args = parser.parse_args()
asn_num = args.asn.strip().upper()

out = open(f"outputs/{asn_num}.json", "w")
all_ports = config_file["ports"]

print(f"scan started and json file initiated ... ")

masscan_ports_cmd = ",".join(all_ports)
database["last_scan"] = str(datetime.datetime.now())

def get_netblocks():
    global batch_len
    netblocks_data = asn_database[asn_num[2:]]
    net_length = len(netblocks_data)
    print(f"{asn_num} has {net_length} netblocks")
    if(net_length == 0):
        json.dump(database,out,indent=4)
        out.close()
        print("Zero netblocks found for the ASN\nExiting process")
        exit()
    if(net_length > 0 and net_length < 4):
        batch_len = net_length
    for _net in netblocks_data:
        cidr = _net.strip()
        if(int(cidr.split("/")[1]) < 18):
            block = IPNetwork(cidr)
            netblocks = [str(x) for x in list(block.subnet(18))]
            all_netblocks.extend(netblocks)
        else:
            all_netblocks.append(cidr)

get_netblocks()


############## splitting and scanning all netblocks ##################

net_list = list(set(all_netblocks))
nets_list = np.array(net_list)
list_len = len(nets_list)
print(f"Netblocks length is {str(list_len)}")
print(f"Batch size is : {str(batch_len)}")
minus = list_len%batch_len
round_val = (list_len-minus)
loop_len = int(round_val/batch_len)
split_data = [i*batch_len for i in range(1,loop_len+1)]
split_data.append(split_data[-1]+minus)
split_nets = np.array_split(nets_list,split_data)
split_nets.pop()
if(batch_len < 4):
    split_nets.pop()

for _ind,_val in enumerate(split_nets,start=1):
    print(f"Batch number {_ind} is processing ...")
    batch_nets = list(_val)
    config_file = open("temp/config.txt", "w")

    for __ind,_net in enumerate(batch_nets,start=1):
        print(_net)
        config_file.write(f"{_net}\n")
        config_file.write(f"job-{str(__ind)}\n")

    config_file.close()
    print("Config file created for scanning process")
    ##### scanning snippet ########
    try:
        output = subprocess.check_output("cat temp/config.txt | parallel --jobs="+str(len(batch_nets))+" --max-args=2  'masscan --open {1} -p"+masscan_ports_cmd+" --rate 2000 --wait 1 -Pn -n --randomize-hosts -oJ temp/outputs/{2}.json'",stderr=subprocess.STDOUT,shell=True)
        print("Scan process done ... ready to write all files ..")

        for _file in os.listdir("temp/outputs"):
            filesize = os.path.getsize(f"temp/outputs/{_file}")
            if(filesize != 0):
                result_file = json.load(open(f"temp/outputs/{_file}"))
                for _res in result_file:
                    _ip = _res["ip"]
                    _ports = _res["ports"]
                    if(_ip in database["data"]):
                        database["data"][_ip].extend(_ports)
                    else:
                        database["data"][_ip] = _ports
        
    except Exception as e:
        print(e)

    print(f"Full process done for batch {_ind}")

for _file in os.listdir("temp/outputs"):
    os.remove(f"temp/outputs/{_file}")

json.dump(database,out,indent=4)
out.close()
print("All done")
