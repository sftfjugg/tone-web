# flake8: noqa

TONE_SYNC_CASE = """
git_branch=master
work_dir=/tmp/tone_work_dir
tone_file=/usr/local/bin/tone
log=/tmp/sync_case.log
clone_retries=3
tone_branch=${TONE_DEBUG_BRANCH:-master}

clone_code(){
  ret=1
  # try 5 times
  i=0
  while [ "$i" -lt $clone_retries ]; do
    rm -Rf $tone_install
    git clone --single-branch --branch $tone_branch https://gitee.com/anolis/tone-cli $1 > $log 2>&1
    if [ $? -ne 0 ]; then
      echo git clone fail >>$logfile
      sleep 5
      continue
    else
      ret=0
      break
    fi
    i=$((i + 1))
  done

  return $ret
}


rm -Rf $work_dir && rm -Rf $tone_file

clone_code $work_dir/tone

if [ $? -ne 0 ];then
    echo "git clone tone error"
    exit 1
fi

# clone_code "tone-matrix" $work_dir/tone/matrics
#if [ $? -ne 0 ];then
#    echo "git clone tone-matrix error"
#    exit 1
#fi

cd $work_dir/tone && make install > $log 2>&1
if [ $? -ne 0 ];then
    echo "tone make install error"
    exit 1
fi

tone_list_output=$(tone list)

tone_list() {
  i=0
  while [ "$i" -lt $# ]; do
    if [ $((i % 2)) = 0 ]; then
      tmp=$((i + 1))
      eval "echo \"suite:\${${tmp}}\""
      eval "case_info=\`tone list \${${tmp}}\`"
    else
      tmp=$((i + 1))
      eval "echo \"type:\${${tmp}}\""
      echo "$case_info"
      echo "-------------------------------"
    fi
    i=$((i + 1))
  done
}

tone_list ${tone_list_output}

"""