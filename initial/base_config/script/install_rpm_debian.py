# flake8: noqa

INSTALL_RPM_DEBIAN = """
#!/bin/bash

script_path=$(readlink -f `dirname $0`)


log_cmd()
{
	local cmd="$@"

	[ -z "$logfile" ] && logfile="/tmp/$(basename $0 | cut -d. -f1).log"
	[ -f "$logfile" ] || touch $logfile
	{
		echo "[$(date '+%F %T')] $cmd"
		$cmd
	} >> $logfile 2>&1
}


install_deb()
{
	local ret=1
	local pkgs=$@

	# try 3 times
	for i in $(seq 1 3); do
		log_cmd dpkg -i --force $pkgs
		if [ $? != 0 ]; then
			sleep 3
			continue
		else
			ret=0
			break
		fi
	done
	return $ret
}


install_deb $@
if [ $? != 0 ]; then
    echo "Failed to install packages: $@"
    exit 1
else
    echo "Success to install packages: $@"
fi

"""