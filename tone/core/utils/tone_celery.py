from subprocess import call

# 启动celery
call(['celery', '-A', 'tone', 'worker', '--pool=solo', '-l', 'info'])
