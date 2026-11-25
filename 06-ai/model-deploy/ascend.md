---
title: 昇腾 NPU 部署环境
description: CANN 安装、NPU 验证与 MindIE 服务启动的命令速查（占位待补）
tags:
  - ai
  - model-deploy
  - ascend
aliases:
  - 06-AI/model_deploy/Ascend-昇腾
---

# 昇腾 NPU 部署环境

## CANN 安装

<https://ascend.github.io/docs/sources/ascend/quick_install.html>

```shell
python3 -c "import acl;print(acl.get_soc_name())"
# 若返回芯片型号，则安装成功。
```

```sh
source /usr/local/Ascend/cann/set_env.sh
```

## MindIE

配置说明：<https://mindie-llm-doc.readthedocs.io/zh-cn/latest/user_guide/user_manual/service_parameter_configuration>

`cd $MINDIE_LLM_HOME_PATH`

vi conf/config.json

```sh
export MINDIE_LOG_TO_STDOUT="true"
```

nohup ./bin/mindieservice_daemon > output.log 2>&1 &

pip3 install -r requirements_qwen3vl.txt --no-index --find-links /data/wheelhouse/
