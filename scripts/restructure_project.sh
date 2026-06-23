#!/bin/bash
# 项目目录结构重组脚本
# 将散落在根目录的文件按功能模块重新组织

set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

echo "===== 开始项目目录重组 ====="
echo "工作目录: $BASE_DIR"
echo ""

# ===== 创建目录结构 =====
echo "===== 创建目录结构 ====="
mkdir -p src/core src/api/middleware src/web src/asr src/db/migrations src/services src/logger src/utils
mkdir -p tests
mkdir -p doc/guides doc/reports doc/plans doc/fixes doc/progress doc/design
mkdir -p scripts

# ===== 移动源代码文件 =====
echo "===== 移动源代码文件 ====="

# --- src/core: 核心配置 ---
mv config.py src/core/
mv config.py.bak src/core/
mv dynamic_config.py src/core/
mv compat_layer.py src/core/
echo "  src/core/ 完成"

# --- src/api: 后端API服务 ---
mv api.py src/api/
mv task_detail_api.py src/api/
mv middleware/idempotency.py src/api/middleware/
rmdir middleware 2>/dev/null || true
echo "  src/api/ 完成"

# --- src/web: 前端Web界面 ---
mv app.py src/web/
mv login.py src/web/
mv task_detail_page.py src/web/
mv api_client.py src/web/
echo "  src/web/ 完成"

# --- src/asr: 语音识别引擎 ---
mv asr_engine.py src/asr/
mv asr_engine.py.backup src/asr/
mv model_loader.py src/asr/
mv hardware_detector.py src/asr/
echo "  src/asr/ 完成"

# --- src/db: 数据库 ---
mv database.py src/db/
mv init_db.sql src/db/
mv migration_add_origin_data.sql src/db/
mv migrations/add_user_id_column.py src/db/migrations/
mv migrations/rename_customer_code_to_customer_no.py src/db/migrations/
mv migrations/update_user_is_active_default.py src/db/migrations/
rmdir migrations 2>/dev/null || true
echo "  src/db/ 完成"

# --- src/services: 业务服务层 ---
mv batch_processor.py src/services/
mv csv_parser.py src/services/
mv checkpoint.py src/services/
mv report_generator.py src/services/
mv auth.py src/services/
echo "  src/services/ 完成"

# --- src/logger: 日志模块 ---
mv logger.py src/logger/
mv logger_config.py src/logger/
mv logger_monitor.py src/logger/
echo "  src/logger/ 完成"

# --- src/utils: 工具与调试 ---
mv exception_handler.py src/utils/
mv debug_tool.py src/utils/
mv debug_session_state.py src/utils/
mv fix_admin_password.py src/utils/
mv execute_migration.py src/utils/
echo "  src/utils/ 完成"

# ===== 移动测试文件 =====
echo "===== 移动测试文件 ====="
mv test_simple.py tests/
mv test_single_audio.py tests/
mv test_unit.py tests/
mv pytest.ini tests/
echo "  tests/ 完成"

# ===== 移动文档文件 =====
echo "===== 移动文档文件 ====="

# --- doc/guides: 使用指南 ---
mv QUICK_START.md doc/guides/
mv INSTALL.md doc/guides/
mv README.md doc/guides/
mv LOGGER_GUIDE.md doc/guides/
mv EXCEPTION_HANDLER_GUIDE.md doc/guides/
mv TASK_DETAIL_HTML_GUIDE.md doc/guides/
mv CONSOLE_LOG_FORMAT.md doc/guides/
echo "  doc/guides/ 完成"

# --- doc/reports: 完成报告 ---
mv 100_PERCENT_COMPLETION_REPORT.md doc/reports/
mv FINAL_COMPLETION_REPORT.md doc/reports/
mv FINAL_SUMMARY.md doc/reports/
mv PHASE6_7_SUMMARY.md doc/reports/
mv PHASE8_SUMMARY.md doc/reports/
echo "  doc/reports/ 完成"

# --- doc/plans: 计划文档 ---
mv ARCHITECTURE_REFACTORING_PLAN.md doc/plans/
mv IMPLEMENTATION_PLAN.md doc/plans/
mv IMPLEMENTATION_CHECKLIST.md doc/plans/
mv OPTIMIZATION_PLAN.md doc/plans/
mv OPTIMIZATION_RECOMMENDATIONS.md doc/plans/
echo "  doc/plans/ 完成"

# --- doc/fixes: 修复记录 ---
mv ADMIN_PASSWORD_FIX.md doc/fixes/
mv ASR_CONFIG_DEVICE_FIX.md doc/fixes/
mv AUTH_REFRESH_FIX.md doc/fixes/
mv IMPORT_FIX_SUMMARY.md doc/fixes/
mv LOGIN_REFRESH_ANALYSIS.md doc/fixes/
mv LOGIN_REFRESH_FINAL_FIX.md doc/fixes/
mv LOGIN_SESSION_PERSISTENCE_FIX.md doc/fixes/
mv PAGE_RENDER_FIX.md doc/fixes/
mv SYNTAX_ERROR_FIX.md doc/fixes/
mv TAB_REFRESH_AND_OVERFLOW_FIX.md doc/fixes/
mv TASK_DETAIL_AND_AUTH_OPTIMIZATION.md doc/fixes/
mv TASK_DETAIL_BUTTON_FIX.md doc/fixes/
mv TASK_LIST_OVERFLOW_FIX.md doc/fixes/
mv URL_COPY_FEATURE.md doc/fixes/
echo "  doc/fixes/ 完成"

# --- doc/progress: 进度文档 ---
mv PROGRESS.md doc/progress/
mv IMPLEMENTATION_SUMMARY.md doc/progress/
mv OPTIMIZATION_SUMMARY.md doc/progress/
mv FRONTEND_BACKEND_SEPARATION_PROGRESS.md doc/progress/
mv ORIGIN_DATA_OPTIMIZATION.md doc/progress/
mv LOG_FORMAT_UPDATE.md doc/progress/
echo "  doc/progress/ 完成"

# --- doc/design: 设计文档 ---
mv APP_ERROR_LOGGING_ENHANCEMENT.md doc/design/
mv SINGLETON_OPTIMIZATION.md doc/design/
mv UI_ADJUSTMENT_FINAL.md doc/design/
mv UI_OPTIMIZATION.md doc/design/
echo "  doc/design/ 完成"

# ===== 移动脚本文件 =====
echo "===== 移动脚本文件 ====="
mv QUICK_START.sh scripts/
mv start_task_detail_service.sh scripts/
mv run_tests.sh scripts/
mv crontab.example scripts/
mv cleanup_logs.py scripts/
echo "  scripts/ 完成"

# ===== 清理异常文件 =====
echo "===== 清理异常文件 ====="
rm -f "="
echo "  清理完成"

echo ""
echo "===== 项目目录重组完成 ====="
echo ""
echo "新目录结构:"
echo "  src/core/      - 核心配置 (config, dynamic_config, compat_layer)"
echo "  src/api/       - 后端API服务 (api, task_detail_api, middleware)"
echo "  src/web/       - 前端Web界面 (app, login, task_detail_page, api_client)"
echo "  src/asr/       - 语音识别引擎 (asr_engine, model_loader, hardware_detector)"
echo "  src/db/        - 数据库 (database, migrations, init_db.sql)"
echo "  src/services/  - 业务服务层 (batch_processor, csv_parser, auth, ...)"
echo "  src/logger/    - 日志模块 (logger, logger_config, logger_monitor)"
echo "  src/utils/     - 工具与调试 (exception_handler, debug_tool, ...)"
echo "  tests/         - 测试文件"
echo "  doc/           - 文档 (guides, reports, plans, fixes, progress, design)"
echo "  scripts/       - 脚本文件"
