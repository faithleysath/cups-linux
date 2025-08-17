#!/bin/bash

# macOS script to manage and start the CUPS printer service container using Docker.

# --- Configuration ---
IMAGE_NAME="cups-printer-server:latest"
CONTAINER_NAME="cups-printer-server"
VIRTUALHERE_APP_PATH="/Applications/VirtualHereServerUniversal.app"
# --- !! SET A UNIQUE PART OF YOUR PRINTER'S NAME HERE !! ---
# This name will be used to automatically find and connect the printer.
PRINTER_NAME="M1005"

# --- Helper Functions ---
function print_info() {
    echo "INFO: $1"
}

function print_success() {
    echo "✅ SUCCESS: $1"
}

function print_error() {
    echo "❌ ERROR: $1" >&2
    exit 1
}

# --- Main Logic ---

# 1. Check if VirtualHere Server is running
print_info "Checking if VirtualHere Server is running..."
if ! pgrep -f "VirtualHereServerUniversal" > /dev/null; then
    print_error "VirtualHere Server is not running. Please start it from ${VIRTUALHERE_APP_PATH} before running this script."
fi
print_success "VirtualHere Server is running."

# 2. Check if the Docker image exists
print_info "Checking for Docker image: ${IMAGE_NAME}..."
if ! docker images --quiet "${IMAGE_NAME}" | grep -q "."; then
    print_info "Image not found. Building it now from Dockerfile..."
    docker build --tag "${IMAGE_NAME}" .
    if [ $? -ne 0 ]; then
        print_error "Failed to build the Docker image."
    fi
    print_success "Image built successfully."
else
    print_success "Image already exists."
fi

# 3. Check the state of the container
print_info "Checking for container: ${CONTAINER_NAME}..."
if docker ps -a --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    if docker ps --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_success "Container is already running."
    else
        print_info "Container exists but is stopped. Starting it..."
        docker start "${CONTAINER_NAME}"
        print_success "Container started."
    fi
else
    print_info "Container does not exist. Creating and starting a new one..."
    docker run \
        --name "${CONTAINER_NAME}" \
        --detach \
        --publish 631:631 \
        --privileged \
        -e VIRTUALHERE_PRINTER_NAME="${PRINTER_NAME}" \
        "${IMAGE_NAME}"
    if [ $? -ne 0 ]; then
        print_error "Failed to create and start the container."
    fi
    print_success "Container created and started."
fi

# --- Final Instructions ---
echo -e "\n🎉 Fully automated printer service is up and running!"
echo "   - The container will automatically connect to the printer: '${PRINTER_NAME}'"
echo "   - ipp-usb will then make it available as a network printer."
echo "   - CUPS Web UI: http://localhost:631"
echo "   - You can view the service logs with: docker exec -it ${CONTAINER_NAME} journalctl -f"
