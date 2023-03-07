# flake8: noqa

UPLOAD_FILE = """
#!/bin/bash

SOURCE_FILE=$1
SOURCE_FILE_NAME=$2
NEW_FILE_NAME=$3

TONE_STORAGE_HOST={tone_storage_host}
TONE_STORAGE_SFTP_PORT={tone_storage_sftp_port}
TONE_STORAGE_PROXY_PORT={tone_storage_proxy_port}
TONE_STORAGE_USER={tone_storage_user}
TONE_STORAGE_PASSWORD={tone_storage_password}
TONE_STORAGE_BUCKET=${{7:-results}}

install_utils()
{{
 yum install -y lftp
}}


function upload_file(){{
    lftp -u ${{TONE_STORAGE_USER}},${{TONE_STORAGE_PASSWORD}} -e "set ftp:ssl-allow no" sftp://${{TONE_STORAGE_HOST}}:${{TONE_STORAGE_SFTP_PORT}} <<EOF
    cd ${{TONE_STORAGE_BUCKET}}
    mkdir -p $TONE_JOB_ID
    cd $TONE_JOB_ID
    mput $SOURCE_FILE
    mv $SOURCE_FILE_NAME $NEW_FILE_NAME
    by
EOF
}}


install_utils
upload_file

"""
