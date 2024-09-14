#!/bin/bash

# 檢查.env文件是否存在
if [ ! -f .env ]; then
  echo ".env 文件不存在"
  exit 1
fi

# 讀取.env文件中的每一行
while IFS= read -r line || [[ -n "$line" ]]; do
  # 忽略空行和註釋行
  if [[ "$line" =~ ^[[:space:]]*# ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
    continue
  fi

  # 將行分割成變數名和值
  var_name=$(echo "$line" | cut -d= -f1)
  var_value=$(echo "$line" | cut -d= -f2-)

  # 匯出變數到環境中
  export "$var_name"="$var_value"
done < .env

echo "已將.env中的變數匯出到環境中"