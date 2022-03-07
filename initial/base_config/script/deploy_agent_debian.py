# flake8: noqa

DEPLOY_AGENT_DEBIAN = """
#!/bin/bash

toneagent_dir=/usr/local/toneagent/rpm
config_file=/usr/local/toneagent/conf/toneagent.config.yaml
deb_url={rpm_url}

echo "[log]uninstall the old version toneagent..."
dpkg -r toneagent
if [ $? -ne 0 ]; then
    echo "[log]toneagent wasn't installed before..."
fi

rm -Rf $toneagent_dir
mkdir -p $toneagent_dir
cd $toneagent_dir

echo "[log]downloading the deb package..."
curl $deb_url --connect-timeout 10 -o toneagent.deb
if [ $? -ne 0 ]; then
    echo "[log]deb download failed..."
    exit 1
fi

echo "[log]install toneagent..."
dpkg -i toneagent.deb
if [ $? -ne 0 ]; then
    echo "[log]dpkg install failed..."
    exit 1
fi

echo "[log]modify toneagent configuration..."
echo -e "tsn: {tsn}
mode: {mode}
proxy: {proxy}" > $config_file
if [ $? -ne 0 ]; then
    echo "[log]modify toneagent configuration failed..."
    exit 1
fi

systemctl restart toneagent
echo "[log]toneagent deploy success!"

"""