import os
import time
import sys
import subprocess
import requests
import ntplib
from datetime import datetime

def get_ntp_time():
    """Get time from NTP servers"""
    ntp_servers = [
        'pool.ntp.org',
        'time.google.com', 
        'time.windows.com',
        'time.nist.gov'
    ]
    
    for server in ntp_servers:
        try:
            client = ntplib.NTPClient()
            response = client.request(server, timeout=2)
            if response:
                return response.tx_time
        except Exception as e:
            print(f"Error with NTP server {server}: {str(e)}")
            continue
    
    # Fall back to HTTP time services
    return get_http_time()

def get_http_time():
    """Get time from HTTP time services"""
    time_servers = [
        'http://worldtimeapi.org/api/ip',
        'http://worldclockapi.com/api/json/utc/now',
        'http://date.jsontest.com'
    ]
    
    for server in time_servers:
        try:
            response = requests.get(server, timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # Different APIs return time in different formats
                if 'unixtime' in data:  # worldtimeapi.org
                    return data.get('unixtime')
                elif 'currentFileTime' in data:  # worldclockapi.com
                    # Convert Windows file time to Unix time (seconds since 1970)
                    file_time = int(data.get('currentFileTime')) / 10000000 - 11644473600
                    return file_time
                elif 'milliseconds_since_epoch' in data:  # date.jsontest.com
                    return data.get('milliseconds_since_epoch') / 1000
        except Exception as e:
            print(f"Error with HTTP time server {server}: {str(e)}")
            continue
    
    return None

def main():
    # Get current system time
    system_time = time.time()
    print(f"Current system time: {datetime.fromtimestamp(system_time)}")
    
    # Get accurate time
    ntp_time = get_ntp_time()
    
    if ntp_time is None:
        print("Could not get time from any server. No changes made.")
        return
    
    print(f"Accurate time from servers: {datetime.fromtimestamp(ntp_time)}")
    
    # Calculate time difference
    time_diff = abs(system_time - ntp_time)
    print(f"Time difference: {time_diff:.1f} seconds ({time_diff/3600:.1f} hours)")
    
    # If time difference is significant (more than 1 minute), update system time
    if time_diff > 60:
        if os.name == 'nt':  # Windows
            # Format time string for Windows date command (Month/Day/Year Hour:Minute:Second)
            time_str = datetime.fromtimestamp(ntp_time).strftime("%m/%d/%Y %H:%M:%S")
            
            print(f"\nYour system time is significantly off. To fix this run:")
            print(f"\nRunning as administrator: date {time_str}")
            print(f"Running as administrator: time {time_str.split()[1]}")
            
            # Ask for confirmation
            response = input("\nDo you want to try updating system time now? (y/n): ")
            if response.lower() == 'y':
                try:
                    # Try to set the date
                    date_cmd = subprocess.run(['cmd', '/c', 'date', time_str.split()[0]], 
                                             shell=True, capture_output=True, text=True)
                    print(date_cmd.stdout)
                    
                    # Try to set the time
                    time_cmd = subprocess.run(['cmd', '/c', 'time', time_str.split()[1]], 
                                             shell=True, capture_output=True, text=True)
                    print(time_cmd.stdout)
                    
                    print("\nSystem time update attempted. Please check if it worked.")
                    print("If it didn't work, run Command Prompt as Administrator and execute the commands above manually.")
                except Exception as e:
                    print(f"Error updating system time: {str(e)}")
                    print("Please run Command Prompt as Administrator and execute the commands above manually.")
        else:  # Linux/Mac
            # Format time string for date command
            time_str = datetime.fromtimestamp(ntp_time).strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\nYour system time is significantly off. To fix this run:")
            print(f"\nsudo date -s \"{time_str}\"")
            
            # Ask for confirmation
            response = input("\nDo you want to try updating system time now? (y/n): ")
            if response.lower() == 'y':
                try:
                    # Try to set the date and time
                    date_cmd = subprocess.run(['sudo', 'date', '-s', time_str], 
                                             shell=True, capture_output=True, text=True)
                    print(date_cmd.stdout)
                    
                    print("\nSystem time update attempted. Please check if it worked.")
                except Exception as e:
                    print(f"Error updating system time: {str(e)}")
                    print("Please run the command above manually with sudo privileges.")
    else:
        print("System time is within acceptable range. No changes needed.")

if __name__ == "__main__":
    main() 