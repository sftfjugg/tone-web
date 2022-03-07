# flake8: noqa

DEPLOY_AGENT = """
#!/bin/bash

toneagent_dir=/usr/local/toneagent/rpm
config_file=/usr/local/toneagent/conf/toneagent.config.yaml
rpm_url={rpm_url}

echo "[log]uninstall the old version toneagent..."
rpm -e toneagent
if [ $? -ne 0 ]; then
    echo "[log]toneagent wasn't installed before..."
fi

rm -Rf $toneagent_dir
mkdir -p $toneagent_dir
cd $toneagent_dir

echo "[log]downloading the rpm package..."
curl $rpm_url --connect-timeout 10 -o toneagent.rpm
if [ $? -ne 0 ]; then
    echo "[log]rpm download failed..."
    exit 1
fi

echo "[log]install toneagent..."
yum -y install toneagent.rpm
if [ $? -ne 0 ]; then
    echo "[log]rpm install failed..."
    exit 1
fi

echo "[log]modify toneagent configuration..."
echo -e "tsn: {tsn}\nmode: {mode}\nproxy: {proxy}" > $config_file
if [ $? -ne 0 ]; then
    echo "[log]modify toneagent configuration failed..."
    exit 1
fi

systemctl restart toneagent
echo "[log]toneagent deploy success!"
"""