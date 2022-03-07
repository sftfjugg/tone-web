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
  for ((i=0; i<$clone_retries; ++i)); do
    rm -Rf $tone_install
    git clone --single-branch --branch $tone_branch https://gitee.com/anolis/tone-cli $1 > $log 2>&1
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

suite_list=(${tone_list_output// / }) 
for(( i=0;i<${#suite_list[@]};i++))
do
    if [ $(($i%2)) == 0 ] ; then
       echo suite:${suite_list[$i]}
       case_info=`tone list ${suite_list[$i]}`
    else
       echo type:${suite_list[$i]}
       echo "$case_info"
       echo "-------------------------------"  
    fi
done

"""