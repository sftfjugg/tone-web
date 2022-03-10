# flake8: noqa

PREPARE_DEBIAN = """
#!/bin/bash

if [ $# -lt 1 ];then
  echo "usage:$0 INSTALL_PATH"
  exit 1
fi

tone_install=$1
provider=$2
logfile=/tmp/prepare_tone.log
tone_branch=${TONE_DEBUG_BRANCH:-master}
tone_git_url=https://gitee.com/anolis/tone-cli

rm -rf $logfile && date > $logfile


# record the command and result to logfile
run_cmd()
{
    cmd="$@"
    {
        echo -e "
##CMD: $cmd"
        $cmd
    } >> $logfile 2>&1
}

clone_tone()
{
  ret=1
  # try 5 times
  for i in $(seq 1 5); do
    rm -Rf $tone_install
    run_cmd git clone --single-branch --branch $tone_branch $tone_git_url $tone_install
    if [ $? -ne 0 ]; then
      echo git clone fail >> $logfile
      sleep 5
      continue
    else
      ret=0
      break
    fi
  done

  return $ret
}


prepare()
{
  #clone tone
  run_cmd apt-get update
  run_cmd apt-get install -y git
  run_cmd apt-get install -y make  
  clone_tone $tone_install
  if [ $? -ne 0 ]; then
    echo "clone tone from $tone_git_url failed."
    exit 1
  fi

  # tone make install
  run_cmd cd $tone_install
  run_cmd rm -f /usr/local/bin/tone
  run_cmd "make install"
  if [ $? -ne 0 ];then
    echo "tone make install error"
    exit 1
  fi
  
  sudo ln -fs /bin/bash /bin/sh
}


#pre_cleanup()
#{
  # remove authconfig which conflicts with lkp installation
  # yum -y erase authconfig &> /dev/null
  # install vmcore-collect
  # run_cmd "yum -y install -b current vmcore-collect"
#}

#pre_cleanup
prepare
echo 'prepare done'

"""
