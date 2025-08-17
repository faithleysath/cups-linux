#!/bin/bash

# Simplified, robust script to connect to a USB printer via VirtualHere.
# ipp-usb will handle the rest.

# --- Configuration ---
if [ -z "$VIRTUALHERE_PRINTER_NAME" ]; then
    echo "ERROR: VIRTUALHERE_PRINTER_NAME environment variable is not set. Exiting."
    exit 1
fi
echo "--> Target printer name: $VIRTUALHERE_PRINTER_NAME"

# --- Main Logic ---

echo "--> Starting VirtualHere client in the background..."
nohup /usr/sbin/vhclientarm64 > /dev/null 2>&1 &
sleep 5

echo "--> Connecting to Mac host (host.docker.internal)..."
/usr/sbin/vhclientarm64 -t "MANUAL HUB ADD,host.docker.internal"
sleep 2

echo "--> Searching for available USB devices..."
DEVICE_LIST=$(/usr/sbin/vhclientarm64 -t "LIST")
PRINTER_LINE=$(echo "$DEVICE_LIST" | grep "$VIRTUALHERE_PRINTER_NAME")

if [ -z "$PRINTER_LINE" ]; then
    echo "ERROR: Could not find a printer with the name '$VIRTUALHERE_PRINTER_NAME'."
    echo "Available devices:"
    echo "$DEVICE_LIST"
    exit 1
fi

PRINTER_ADDRESS=$(echo "$PRINTER_LINE" | awk -F'[()]' '{print $2}')
echo "--> Found printer address: $PRINTER_ADDRESS"

echo "--> Attempting to connect to device: $PRINTER_ADDRESS..."
MAX_RETRIES=5
RETRY_COUNT=1
SUCCESS=false
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RESPONSE=$(/usr/sbin/vhclientarm64 -t "USE,$PRINTER_ADDRESS")
    if [ "$RESPONSE" == "OK" ]; then
        echo "--> Connection successful."
        SUCCESS=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "--> Connection failed with response: '$RESPONSE'. Retrying ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep 3
done

if [ "$SUCCESS" = "false" ]; then
    echo "ERROR: Failed to connect to printer after $MAX_RETRIES attempts."
    exit 1
fi

echo "--> Printer connected. ipp-usb and CUPS will now take over."
exit 0
