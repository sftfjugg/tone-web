# flake8: noqa

SSH_PUB_KEY = """
#!/bin/bash

if [ ! -f "/root/.ssh/id_rsa.pub" ]; then
	ssh-keygen -b 2048 -t rsa -f /root/.ssh/id_rsa -q -N ""
fi

cat /root/.ssh/id_rsa.pub

"""
