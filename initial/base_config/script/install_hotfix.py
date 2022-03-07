# flake8: noqa

INSTALL_HOTFIX = """

#!/bin/sh


script_path=$(readlink -f `dirname $0`)
# not support yet
tone_url=

# record command and output in logfile
log_cmd()
{{
local cmd="$@"  

[ -z "$logfile" ] && logfile="/tmp/$(basename $0 | cut -d. -f1).log"
[ -f "$logfile" ] || touch $logfile
{{
    echo "[$(date '+%F %T')] $cmd"
    $cmd
}} >> $logfile 2>&1
}}


is_kernel_install()
{{
local ret=1
for pkg in $@; do
    pkg=$(basename $pkg)
    echo $pkg | egrep -v "hotfix|devel|headers|tools|debuginfo" | grep -qE "^kernel|^kernel-debug" && ret=0 && break
    done
    return $ret
}}


parse_alikver()
{{
    alikernel_version=$1
    [ -z "$alikernel_version" ] && return
    local alikver_major=""
    local alikver_minor=""
    local alikver_extra=""

    alikernel_tag=""

    alikver_major=`echo $alikernel_version | cut -d'.' -f4`
    if ! echo $alikver_major | grep -qE '^ali[0-9]{{4}}'; then
        echo "Non-alikernel release: $alikver_major"
        return
    fi
    alikernel_tag=$alikver_major
    if [[ "$alikernel_version" =~ '3.10' ]]; then
    alikver_minor=`echo $alikernel_version | cut -d'.' -f5`
    if echo $alikver_minor | grep -qE '^rc[0-9]'; then
        alikernel_tag=${{alikernel_tag}}.${{alikver_minor}}
        alikver_extra=`echo $alikernel_version | cut -d'.' -f6`
        else
        alikver_extra=$alikver_minor
        alikver_minor=""
    fi  
    elif [[ "$alikernel_version" =~ '4.9' ]]; then
    alikver_minor=`echo $alikernel_version | cut -d'.' -f3 | cut -d'-' -f2`
    alikver_extra=`echo $alikernel_version | cut -d'.' -f5`
    if echo $alikver_minor | grep -qE '^[0-9]{{3}}'; then
        alikernel_tag=${{alikver_minor}}.${{alikernel_tag}}
    else
        alikernel_tag=$alikver_major
        alikver_minor=""
        fi
    else
    echo "Non-alikernel version: $alikernel_version"
    return
    fi
    if [ -n "$alikver_extra" ] && ! [[ "$alikver_extra" =~ "alios" ]]; then
        alikernel_tag="${{alikernel_tag}}.${{alikver_extra}}"
    fi
}}


khotfix_cleanup()
{{
    local pkg
    for pkg in `rpm -qa | egrep "^khotfix-|^kernel-hotfix-" | grep "$alikernel_tag"`; do
    log_cmd rpm -e --nodeps $pkg
    done
}}


get_registered_khotfix()
{{
    local kver=$1
    local tmp_script=$(mktemp)

    cat <<-EOF > $tmp_script
    curl -H 'Content-Type: application/json' -X GET -d '{{ "kernel": "$kver"}}' $tone_url/api/hotfix_id_list/ 2>/dev/null 
    | sed -n '/"data": \[/,/\],/p' | egrep -v "\[|\]" | sed -e 's/"//g' -e 's/,//g' | xargs
EOF
    khotfix_registered=$(sh $tmp_script)
    rm -rf $tmp_script
}}


khotfix_install()
{{
    local khotfix_list=""
    local karch=`uname -m`
    local khotfix_blacklist="D744095 D646263 D741581 ticket_lock 			D844356 bounce_io bounce_alloc"

    [ -n "$new_kver" ] && get_registered_khotfix "$new_kver"
    if [ -n "$khotfix_registered" ]; then
    echo "Install registered kernel hotfixes:"
    echo "$khotfix_registered"
    for x in $khotfix_registered; do
    pkg=$(yum search -b test $x 2>/dev/null | 				grep "${{alikernel_tag}}.${{karch}}" | 				
    egrep "khotfix|kernel-hotfix" | 				awk '{{print $1}}')
    [ -n "$pkg" ] && khotfix_list+=" $pkg"
    done
    else
    echo "Install kernel hotfixes in current branch"
    khotfix_list=$(yum search -b current khotfix | 			grep "${{alikernel_tag}}" | 			
    awk '{{print $1}}' | 			sed "s/\.${{karch}}$//g" | 			xargs)

    [ -n "$alikernel_tag" ] && 			khotfix_list+=" $(yum search -b current kernel-hotfix | 				
    grep "${{alikernel_tag}}.${{karch}}" | 				awk '{{print $1}}' | 				sed "s/\.${{karch}}$//g" | xargs)"
    fi

    # install kernel hotfix or skip
    for kfix in $khotfix_list; do
        skip=0
        for x in $khotfix_blacklist; do
        if (echo $kfix | grep -q $x); then
        skip=1
        if (rpm -qa | grep -q $kfix); then
        log_cmd "rpm -e $kfix"
        break
    fi
    fi
        done
    if [ -z "$khotfix_registered" ] && 			[[ "$kfix" =~ "kernel-hotfix" ]] && 		
    [[ ! "$kfix" =~ "kernel-hotfix-D" ]]; then
        skip=1
        fi
        [ "$skip" -eq 1 ] && echo "SKIP: $kfix" && continue
    log_cmd "yum install -y -q -b current $kfix"
    done
    echo "Success to install hotfix."
}}


# install kernel hotfixes
if is_kernel_install "$@"; then
    parse_alikver "$new_kver"
    if [ -n "$alikernel_tag" ]; then
    khotfix_cleanup
    [ x"$KHOTFIX_INSTALL" = xy ] && khotfix_install
    fi
fi

"""
