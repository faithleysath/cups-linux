# Step 1: Base Image
FROM --platform=linux/arm64 debian:stable-slim

# Step 2: Environment Setup
ENV DEBIAN_FRONTEND=noninteractive

# Step 3: Install Dependencies
RUN apt-get update && apt-get install -y \
    cups \
    printer-driver-foo2zjs \
    usbip \
    kmod \
    avahi-daemon \
    systemd \
    acl \
    sane-utils \
    && rm -rf /var/lib/apt/lists/*

# Step 4: Install the pre-downloaded ipp-usb package
COPY ipp-usb_0.9.30.12-1+61.1_arm64.deb /tmp/ipp-usb.deb
RUN dpkg -i /tmp/ipp-usb.deb \
    && rm /tmp/ipp-usb.deb

# Step 4.5: Fix udev rule for scanner permissions
RUN sed -i 's|RUN+="/bin/setfacl -m g:scanner:rw $env{DEVNAME}"|GROUP="scanner", MODE="0660"|' /lib/udev/rules.d/99-libsane1.rules

# Step 4.6: Blacklist usblp kernel module to prevent conflict with ipp-usb
RUN echo "blacklist usblp" > /etc/modprobe.d/blacklist-usblp.conf

# Step 5: Copy Local Files
COPY vhclientarm64 /usr/sbin/vhclientarm64
RUN chmod +x /usr/sbin/vhclientarm64
COPY cupsd.conf /etc/cups/cupsd.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
COPY vh-connect.service /etc/systemd/system/vh-connect.service
RUN chmod 644 /etc/systemd/system/vh-connect.service
COPY ipp-usb.service /etc/systemd/system/ipp-usb.service
COPY connect_printer.sh /usr/local/bin/connect_printer.sh
RUN chmod +x /usr/local/bin/connect_printer.sh

COPY ipp-usb.conf /etc/ipp-usb/ipp-usb.conf

# Step 6: Enable Services
RUN systemctl enable cups.service
RUN systemctl enable avahi-daemon.service
RUN systemctl enable ipp-usb.service
RUN systemctl enable vh-connect.service

# Step 7: Networking and Entrypoint
EXPOSE 631
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
