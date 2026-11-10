"""Advertise the running ResQ API on the local network using DNS-SD."""
import socket
import time

from zeroconf import ServiceInfo, Zeroconf


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
    finally:
        sock.close()
    info = ServiceInfo("_resq._tcp.local.", "ResQ Backend._resq._tcp.local.", addresses=[socket.inet_aton(address)], port=8000, properties={"service": "resq-mobile-network"})
    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print(f"Advertising ResQ Backend at http://{address}:8000/")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()


if __name__ == "__main__":
    main()
