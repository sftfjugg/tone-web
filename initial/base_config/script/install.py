# flake8: noqa

INSTALL_KERNEL = """

#!/bin/sh

logfile='/tmp/tone_run.log'


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

# check and rebuild rpm db in case it was corrupted
check_rpmdb()
{
	if rpm -qa 2>&1 | grep -q "error: rpmdb"; then
		echo "Try to rebuild corrupted rpmdb"
		rebuild_rpmdb
	fi
}

rebuild_rpmdb()
{
	# back up /var/lib/rpm dir
	mkdir -p /backups/rpm/
	(cd /var/lib && tar zcf /backups/rpm/rpmdb-$(date +%F).tar.gz rpm)

	# try to fix the broken rpmdb
	log_cmd 'pushd /var/lib/rpm'
	log_cmd '/usr/lib/rpm/rpmdb_stat -CA'
	log_cmd 'rm -f /var/lib/rpm/__db*'
	if ! /usr/lib/rpm/rpmdb_verify -q Packages; then
		log_cmd 'mv Packages Packages.orig'
		{
		echo '/usr/lib/rpm/rpmdb_dump Packages.orig | '		'/usr/lib/rpm/rpmdb_load Packages'
		/usr/lib/rpm/rpmdb_dump Packages.orig | 		/usr/lib/rpm/rpmdb_load Packages
		} >> $logfile 2>&1
	fi
	log_cmd '/usr/lib/rpm/rpmdb_verify Packages'
	log_cmd 'rpm -qa 1> /dev/null'
	log_cmd 'rpm -v --rebuilddb'
	log_cmd 'yum clean all'
	log_cmd 'popd'
}

install_rpm()
{
	local ret=1
	local pkg=$1

	# try 10 times
	for ((i=0; i<3; ++i)); do
		log_cmd rpm -ivh --force $pkg
		if [[ $? != 0 ]]; then
			sleep 1
			continue
		else
			ret=0
			break
		fi
	done
	return $ret
}


# check and fix broken rpmdb at beginning
check_rpmdb

for pkg in $@;do
    wget --spider --connect-timeout=5 --timeout=10 --tries=10 --retry-connrefused $pkg >/dev/null 2>&1
    if [[ $? != 0 ]];then
        echo "wget --spider $pkg failed"
        exit 1
    fi
done

# remove existing kernel-headers to avoid dependency error
if echo $@ | grep -qE "kernel-headers|kernel-alinux-headers"; then
	for x in `rpm -qa | grep -E "kernel-headers|kernel-alinux-headers"`; do
		log_cmd rpm -e --nodeps $x
	done
fi

for pkg in $@;do
    install_rpm $pkg
    if [[ $? != 0 ]]; then
      echo "Failed to install kernel rpm: $pkg"
    exit 1
fi
done

# print installed kernel package for better tone output
if [ -n "$new_kver" ]; then
	echo "Kernel: $new_kver"
else
	rpm -qa | grep "$(basename $1 .rpm)"
fi

echo "install kernel done."
exit 0

"""