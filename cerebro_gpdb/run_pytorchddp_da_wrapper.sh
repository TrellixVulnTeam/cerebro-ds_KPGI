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
SUB_LOG_DIR=${1}
WORKING_DIR=${2}
EPOCHS=${3:-10}
OPTIONS=${4:-""}
echo "In wrapper"
export NCCL_SOCKET_IFNAME='enp94s0f0'
# kill any leftover
while $(killall -9 python3.7 2>/dev/null); do 
    sleep 1
done
sleep 3
cd $WORKING_DIR
export PYTHONPATH=''
export PYTHONPATH="${PYTHONPATH}:/local:/local/cerebro-greenplum"
python3.7 -u run_pytorchddp_da.py --logs_root ${SUB_LOG_DIR} --worker --num_epochs $EPOCHS ${OPTIONS} 2>&1 | tee -a ${SUB_LOG_DIR}/${WORKER_NAME}.log