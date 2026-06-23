#!/bin/bash
set -e

ROO_RULES_DIR="/Users/ylm/Documents/Roo/Rules"
ROO_RULE_FILE="$ROO_RULES_DIR/spec-coding-process.md"
PROJECT_RULE_FILE=".roo/rules/spec-coding-process.md"

mkdir -p "$ROO_RULES_DIR"

cat > "$ROO_RULE_FILE" <<'EOF'
# Spec Coding 全局规则

## 全局生效范围

本规则对 Roo 插件维度全局生效，适用于所有项目、所有工作区中的 coding、debug、refactor、test、script、docs 相关实现任务。

除非用户明确提出新的覆盖性规则，否则本文件优先作为后续任务的默认执行约束。

## 默认前置流程

任何 coding 执行之前，必须先完成以下步骤：

1. 需求理解
2. 现状分析
3. 功能分析
4. 设计方案
5. 执行 TODO
6. 用户确认
7. 切换到 Code 模式实现
8. 实现后验证并输出结果

## 需求理解要求

执行前需要明确：

- 用户原始诉求
