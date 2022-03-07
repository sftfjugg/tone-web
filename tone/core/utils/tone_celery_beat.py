from subprocess import call

# 启动celery_beat
call(['single-beat', 'celery', 'beat', '-A', 'tone'])
