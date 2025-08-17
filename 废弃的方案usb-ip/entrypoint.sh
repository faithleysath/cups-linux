#!/bin/bash
# This script runs as PID 1 in the container.
# It injects the Docker environment variables into a file that systemd can read,
# then replaces itself with the systemd process.

# Write the environment variable to a file that our service will read
echo "VIRTUALHERE_PRINTER_NAME=${VIRTUALHERE_PRINTER_NAME}" > /etc/environment

# Execute systemd, which will now become PID 1
exec /lib/systemd/systemd
