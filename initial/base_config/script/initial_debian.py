# flake8: noqa

INITIAL_DEBIAN = """
#!/bin/bash

# we do a complete cleanup in tone machine pool.
if [ "$1" = "inpool" ]; then
    # some tests may generate large httpd logs.
    rm -rf /var/log/httpd/*

    # cleanup existing kernel rpms to save space for new kernel installation.
    cur_kern=$(uname -r)
    debs=$(dpkg -l| grep ^kernel- | grep -v $cur_kern)
    #rpms=$(rpm -qa | grep ^kernel- | grep -v $cur_kern)
    for deb in $debs; do
      dpkg -r $deb
    done

    sleep 5
    # cleanup files under /boot to save space.
    irfs=`ls /boot/initramfs-* | egrep -v "$cur_kern|rescue"`
    rm -rf $irfs
    symvers=`ls /boot/symvers-* | egrep -v "$cur_kern|rescue"`
    rm -rf $symvers
    vls=`ls /boot/vmlinuz-* | egrep -v "$cur_kern|rescue"`
    rm -rf $vls
    sms=`ls /boot/System.map-* | egrep -v "$cur_kern|rescue"`
    rm -rf $sms
    cfgs=`ls /boot/config-* | egrep -v "$cur_kern|rescue"`
    rm -rf $cfgs
    mds=`ls /lib/modules/ | grep -v $cur_kern`
    cd /lib/modules/
    rm -rf $mds
fi

# driver for 4.9 and 3.10
if [ -f "/etc/alios-release" ]; then
	sed 's/^#add_drivers+=""/add_drivers+=" mpt3sas mpt2sas "/' /etc/dracut.docker > /tmp/dracut.docker
	mv -f /tmp/dracut.docker /etc/dracut.docker
fi
echo "initial done."

"""