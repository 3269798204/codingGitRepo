# Roo 插件级全局规则安装计划

## 目标

将 Spec Coding 规则从项目维度同步到 Roo 插件维度默认全局规则目录。

目标文件：`/Users/ylm/Documents/Roo/Rules/spec-coding-process.md`

## 执行步骤

1. 创建 Roo 插件级全局规则目录。
2. 写入 Spec Coding 全局规则文件。
3. 删除项目级误放文件 `.roo/rules/spec-coding-process.md`。
4. 读取目标文件验证内容。

## 说明

由于 Architect 模式只能直接编辑 Markdown 文件，插件级目录写入将通过终端命令完成。