# Requirement :  msiempy (https://github.com/mfesiem/msiempy)

import msiempy.alarm
import re
import argparse
import requests
from urllib.parse import urljoin, urlparse

def parse_args():
    parser = argparse.ArgumentParser(description="""Acknowledge irrelevants IPS - High Severity Event alarms""")
    parser.add_argument('--time_range','-t', metavar='time_range', help='Timerange, choose from '+', '.join(msiempy.FilteredQueryList.POSSIBLE_TIME_RANGE),  
        choices=msiempy.FilteredQueryList.POSSIBLE_TIME_RANGE, default='CURRENT_DAY')
    parser.add_argument('--start_time','--t1', metavar='time', help='Start trigger date')
    parser.add_argument('--end_time','--t2', metavar='time', help='End trigger date')
    '''
    parser.add_argument('--filters', '-f', metavar="'<field>=<match>'", action='append', nargs='+', help="""List of field/matchvalue filters. 
    Alarm related fields can be : id, summary, assignee, severity, triggeredDate, acknowledgedDate, acknowledgedUsername, alarmName, events.  
    Event related fields can be : ruleName, srcIp, destIp, protocol, lastTime, subtype, destPort, destMac, srcMac, srcPort, deviceName, sigId, normId, srcUser, destUser, normMessage, normDesc, host, domain, ipsId.""", default=[[]])
    '''
    parser.add_argument('--page_size', '-p', metavar='page_size', help='Size of alarms list', default=500, type=int)
    parser.add_argument('--pages', '-n', metavar='pages', help='Number of alarm pages to load', default=1, type=int)
    parser.add_argument('--response_codes', '-r', metavar='response codes', help='List of response codes to acknowledge. Commas separated values. Example : "403,404". Use "error" to include network errored requests.', default='404')
    parser.add_argument('--resources', '-s', metavar='resources', help='List of string matches url resources to acknowledge. Acknowledge any resources if not specified. Commas separated values. Example : "setup.cgi,login.cgi,user.php"', default='')
    parser.add_argument('--force', help="Will not prompt for confirmation before ackniwledging alarms", action="store_true")

    return (parser.parse_args())

def concatenate_url(https,host,ressource):
    url=str()
    if len(ressource)>1:
        while ressource[0] == '/' or ressource[0] == ' ' :
            if len(ressource)>1:
                ressource=ressource[1:]
            else: break
    if https: site='https://'+host.strip( '/' )
    else: site='http://'+host.strip( '/' )
    url=str(urljoin(site,ressource))
    return(url)

if __name__ == "__main__":
    HTTPS=False
    
    args=parse_args()

    alarms=msiempy.alarm.AlarmManager(
        time_range=args.time_range,
        start_time=args.start_time,
        end_time=args.end_time,
        status_filter='unacknowledged',
        filters=[("alarmName", "IPS - High Severity Event")],
        page_size=args.page_size,
    )
    alarms.load_data(pages=args.pages, use_query=True, extra_fields= ['Description', 'Device_URL', 'Alert.DstIP', 'Rule.msg'])

    alarms_to_ack=msiempy.alarm.AlarmManager()

    for alarm in alarms:
        events = alarm.get('events')
        
        if len(events) == 1:
            description = str()
            device_url = str()
            try : #Retreive RAW ressource URL and description
                device_url=events[0]['Device_URL']
                description=events[0]['Description']
            except KeyError : pass #Ignoring KeyErrors because it variblaes are initiated with empty strings

            #If the device url is not empty, then there's something to check !
            if device_url: 

                #Stripping arguments from resource uri. Will return onyl ressource path. 
                resource_path= urlparse(device_url).path

                #If the resource_path matches the ressources gave as cli arguments or no matches have been given, continue and check the file.
                if ( (len(args.resources)>0 
                    and any( [match.strip() in resource_path 
                        for match in args.resources.split(',') if len(match)>0] ))
                    or len(args.resources)==0 ):
                    
                    #Parsing HTTP host field from event description if possible else use IP address
                    host_desc_match = re.findall('(?<=HTTP Host ==  ).+?(?=;;;)', description)
                    host = host_desc_match[0] if len(host_desc_match)>0 else events[0].get('Alert.DstIP')
                    
                    #Merging host and resource_path to get full url
                    url = concatenate_url(HTTPS, host, resource_path)

                    #Getting the url
                    try:
                        response = requests.get(url, 
                            verify=False, 
                            headers = {'User-Agent': 'Mozilla/5.0'}, 
                            timeout=60)
                    except Exception as err :
                        response = err

                    #If the status code matches the cli arguments (typically 403 or 404)
                    #Or if the request is errored and 'error' is mentionned in response_codes
                    #Then add the alarm to the list to acknowledge
                    if ( (isinstance(response, Exception) and 'error' in args.response_codes) 
                        or (isinstance(response, requests.Response) and str(response.status_code) in [code.strip().lower() 
                            for code in args.response_codes.split(',')]) ):

                        #Print alarm info
                        print("IPS - High Severity Event : {} \n\ttriggered at {} \n\tregarding URL {} \n\treturned {}".format(
                            alarm.get('events')[0].get('Rule.msg'),
                            alarm.get('triggeredDate'),
                            url, response.status_code if isinstance(response, requests.Response) else str(response)))

                        alarms_to_ack.append(alarm)
    
    if len(alarms_to_ack)>0:
        if args.force or ('y' in input('Are you sure you want to acknowledge those {} alarms ? [y/n]'.format(len(alarms_to_ack)))):
            alarms_to_ack.perform(msiempy.alarm.Alarm.acknowledge, progress=True,
                message='Acknowledging {} alarms...'.format(len(alarms_to_ack)))
            print('{} Alarms have been acknowledged.'.format(len(alarms_to_ack)))
    else :
        print('No alarms to acknowledge.')
