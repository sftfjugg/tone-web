# flake8: noqa

REBOOT = """
#!/bin/sh

sync
sleep 5
reboot -f
"""