#!/usr/bin/python
# AUTHOR: Ramesh Basukala <basukalarameshATgmailDOTcom>
# DATE: 02.18.2014
from pysphere import VIServer, VIProperty
import sys
import ast
import socket
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

server = VIServer()

DEBUG = 0 # DEBUG = 1 for debugging 

hostname = socket.gethostname()
email_from = "no-reply@"+hostname
email_to = ['email_recepient@yourdomain.com']
date_base = datetime.datetime.today()

def sendemail(vServer, html_Str):
    ''' Function to send an email '''
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = vServer + ": vCenter Device Config " + date_base.strftime('%Y-%m-%d %H-%M-%S')
    msg['From'] = email_from
    msg['To'] =  ', '.join(email_to)
    
    # Record the MIME types of both parts - text/plain and text/html.
    report_body_html = MIMEText(html_str, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(report_body_html)
    
    try:
        # Send an email via local SMTP server
        s = smtplib.SMTP('smtp.yourdomain.com')
        s.sendmail(email_from, email_to, msg.as_string())
        s.quit()
    except Exception:
        print "Error: unable to send email"

def readVirtualHostConfig(serverName):
    """ Function to read vmware guest configurations/status
    """
    if DEBUG: print serverName
    try:
        myvm = server.get_vm_by_name(serverName)
    except:
        return None
    
    props = VIProperty(server, server._do_service_content.CustomFieldsManager)

    custom_fields = dict((cf.key, cf.name) for cf in props.field)

    vm_config_dict = {}
    vm_config_dict['productionstatus'] = ''
    vm_config_dict['primarysysadmin'] = ''
    vm_config_dict['guestname'] = ''
    vm_config_dict['guestos'] = ''
    vm_config_dict['guestmemorymegabyte'] = ''
    vm_config_dict['numcpu'] = ''
    vm_config_dict['vmversion'] = ''
    vm_config_dict['vmxfile'] = ''
    vm_config_dict['vmstatus'] = ''
    vm_config_dict['vmtoolstatus'] = ''
    
    network_config = []
    try:
        networks_config = myvm.get_properties()['net']
    except:
        if DEBUG: print("Could not query device: %s" % serverName)
        return None
    if DEBUG: print ("Network config:")
        
    for n in networks_config:
        if DEBUG: print n
        if not n['network']:
            continue
        if DEBUG: print("%s: %s: %s: %s" % (n['network'], n['mac_address'], n['ip_addresses'][0], n['connected']))
        
        # VMXNET 3 - could not get ip address for some reason
        try:
            network_config.append("{'network': '%s', 'macaddress': '%s', 'address': '%s', 'connectionstatus': '%s'}" % (n['network'], n['mac_address'], n['ip_addresses'][0], n['connected']))
        except IndexError:
            pass
    vm_config_dict['network'] = network_config
        
    for cv in myvm.properties.customValue:
        if DEBUG: print "%s: %s"  % (custom_fields.get(cv.key), cv.value)
        if custom_fields.get(cv.key).lower() == 'primary sysadmin':
            vm_config_dict['primarysysadmin'] = cv.value
        elif custom_fields.get(cv.key).lower() == 'status':
            vm_config_dict['productionstatus'] = cv.value
        else:
            pass
        # Get Notes from VM
    if DEBUG: print("Notes: %s " % myvm.properties.config.annotation)
    vm_config_dict['notes'] = myvm.properties.config.annotation
    #print vm_config_dict
    
    disks = []
    if DEBUG: print("DISKS")
    for d in myvm.get_properties()['disks']:
        if DEBUG: print("label: %s Capacity(KB): %s" % (d['label'],d['device']['capacityInKB']))
        disks.append("{'label': '%s', 'capacitykilobyte': '%s'}" % (d['label'],d['device']['capacityInKB']))
    vm_config_dict['vmdisks'] = disks

    vm_config_dict['guestname'] = myvm.properties.config.name
    vm_config_dict['guestos'] = myvm.properties.config.guestFullName
    vm_config_dict['guestmemorymegabyte'] = myvm.properties.config.hardware.memoryMB
    vm_config_dict['numcpu'] = myvm.properties.config.hardware.numCPU
    vm_config_dict['vmversion'] = myvm.properties.config.version
    vm_config_dict['vmxfile'] = myvm.properties.config.files.vmPathName
    vm_config_dict['vmstatus'] = myvm.get_status()
    vm_config_dict['vmtoolstatus'] = myvm.get_tools_status()
   
    guestsnapshots = []
    snapshot_list = myvm.get_snapshots()
    if DEBUG: print "Snapshots: "
    for snapshot in snapshot_list:
        if DEBUG: print("   Name: %s" % snapshot.get_name())
        guestsnapshots.append(snapshot.get_name())
    
    vm_config_dict['snapshots'] = guestsnapshots
    return vm_config_dict

def html_output(data_dict):
    ''' Function to generate html output given data dictionary input '''
    color_odd = "#c7ebfd"
    color_even = "#77c9f4"
    html = """<HTML>
   <HEAD>
      <TITLE> VMWare Guests Configuration </TITLE>
      <STYLE>
         table, td {
            border:0px;
            border-spacing:0;
            border-collapse:collapse;
            table-layout:fixed;
            width: 1200px;
         }
         th {
            background-color:green;
            color:white;
            font-family:arial;
            font-size:9px;
            font-weight:bold; 
            border:1px solid white;
            border-spacing:0;
            border-collapse:collapse;
         }
         td {
            width: 175px;
            font-family:arial;
            font-size:9px;
            word-wrap:break-word;
            vertical-align:top;
         }
      </STYLE>

   </HEAD>
    
   <BODY>
      <TABLE>
         <TR><TH>Name</TH><TH>VM Status</TH><TH>Producation Status</TH><TH>Primary Sysadmin</TH><TH>OS</TH><TH>Memory (MB)</TH><TH>#CPU</TH><TH>VM Version</TH><TH>VM Tool Status</TH><TH>VMX</TH><TH>Network</TH><TH>Disks</TH><TH>Snapshots</TH><TH>Notes</TH></TR>
    """
    count = 0
    klist = data_dict.keys()
    klist.sort()
    for key in klist:
        guest = data_dict[key]
        if not guest: continue
        if count%2 == 0:
            html += "     <TR bgcolor='" + color_odd + "#c7ebfd'>"
        else:
            html += "     <TR bgcolor='" + color_even + "'>"
        html += "<TD>" + guest['guestname'] + "</TD><TD>" + guest['vmstatus'] + "</TD><TD>" + guest['productionstatus']+ "</TD><TD>" + guest['primarysysadmin'] + "</TD>"
        html += "<TD>" + guest['guestos'] + "</TD><TD>" + str(guest['guestmemorymegabyte']) + "</TD><TD>" + str(guest['numcpu']) + "</TD><TD>" + guest['vmversion'] + "</TD>"
        html += "<TD>" + guest['vmtoolstatus'] + "</TD><TD>" + guest['vmxfile'] + "</TD>"
        
        html += "<TD>"
        for hn in guest['network']:
            # Convert string into dict
            dict_hn = ast.literal_eval(hn)
            html += "%s: %s: %s: %s <BR />" % (dict_hn['network'], dict_hn['macaddress'], dict_hn['address'], dict_hn['connectionstatus'])  
        html += "</TD>"
        
        html += "<TD>"
        for d in guest['vmdisks']:
            ##print d
            disk_dict = ast.literal_eval(d)
            html += "%s: %s <BR />" % (disk_dict['label'], disk_dict['capacitykilobyte'])
        html += "</TD>"
        
        html += "<TD>"
        for s in guest['snapshots']:
            html += s + "<BR />"
        html += "</TD>"
        
        html += "<TD>" + guest['notes'] + "</TD>"
        
        html += "</TR>\n"
        count = count+1
    
    html += """
      </TABLE>
   </BODY>
</HTML>
"""    
    return html
    
if __name__ == "__main__":
    vServer = "vcenter-server.domain"
    input_server_file = "vms.txt"
    if sys.argv[1]:
        input_server_file = sys.argv[1]
    server.connect(vServer, "<USERNAME>", "<PASSWORD>")
    # Read names of server from file in following format, server name is case
    # sensitive.
    #vm_guests = ['Server1', 'SERVER2', 'server3', 'SERver4']
    with open(input_server_file) as f:
        vm_guests = [line.rstrip('\n') for line in f ]
    if DEBUG: print vm_guests 
    res = {}
    for guest in vm_guests:
        # Assuming all hosts are nammed as uppercase on vCenter
        # Remove this comment in case all VM names are standardized as all CAPS
        guest_upper = guest
        # guest_upper = guest.upper()
        res[guest_upper] = readVirtualHostConfig(guest_upper)
    html_str = html_output(res)
    sendemail(vServer, html_str)
    server.disconnect()
