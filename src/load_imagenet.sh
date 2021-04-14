#!/usr/bin/env bash
# Copyright 2020 Yuhao Zhang and Arun Kumar. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
TIMESTAMP=`date "+%Y_%m_%d_%H_%M_%S"`
LOG_DIR="/mnt/nfs/logs/run_logs/$TIMESTAMP"
SUB_LOG_DIR=$LOG_DIR/load-imagenet
mkdir -p $SUB_LOG_DIR
echo "Loading imagenet ..."
SECONDS=0
echo "Loading imagenet, Start time `date "+%Y-%m-%d %H:%M:%S"`">>$LOG_DIR/global.log
unset PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/local/cerebro-greenplum"
python3.7 -u load_imagenet.py --load --pack 2>&1 | tee -a ${SUB_LOG_DIR}/client.log
echo "Loading imagenet, End time `date "+%Y-%m-%d %H:%M:%S"`">>$LOG_DIR/global.log 
echo "Loading imagenet, TOTAL EXECUTION TIME OVER ALL MST $SECONDS">>$LOG_DIR/global.log