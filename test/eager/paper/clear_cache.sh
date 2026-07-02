#! /bin/bash

# Get the directory of the script
SCRIPT_DIR=$(realpath "$0" | sed 's|\(.*\)/.*|\1|')

# check if the .env file exists
if [ -f "$SCRIPT_DIR/../../../.env" ]; then
    echo "Loading environment variables from .env file"
else
    echo "The .env file does not exist, please create it with SUDO_PASSWORD defined"
    exit 1
fi

# export the environment variable defined in the .env file
export $(grep -v '^#' "$SCRIPT_DIR/../../../.env" | xargs)

# check if the SUDO_PASSWORD environment variable is defined
if [ -z "$SUDO_PASSWORD" ]; then
    echo "The SUDO_PASSWORD environment variable is not defined"
    exit 1
fi

# Sync filesystem
echo $SUDO_PASSWORD | sudo -S sync

# Clear the cache
# This is the same as running `sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches`
echo $SUDO_PASSWORD | sudo -S sysctl -w vm.drop_caches=3

# Wait for 10 seconds
sleep 10

# Sync filesystem again
echo $SUDO_PASSWORD | sudo -S sync

# Check the cache
echo $SUDO_PASSWORD | sudo -S free -h

exit 0
