#!/bin/bash
# 测试运行脚本

echo "=========================================="
echo "  语音识别分析系统 - 测试工具"
echo "=========================================="
echo ""

# 检查 pytest 是否安装
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest 未安装，正在安装..."
    pip3 install pytest pytest-cov --user
fi

case "$1" in
    unit)
        echo "🧪 运行单元测试..."
        python3 -m pytest test_unit.py -v -k "not TestASREngineMock and not TestBatchProcessorMock"
        ;;
    
    all)
        echo "🧪 运行所有测试..."
        python3 -m pytest test_unit.py -v
        ;;
    
    coverage)
        echo "📊 运行测试并生成覆盖率报告..."
        python3 -m pytest test_unit.py --cov=. --cov-report=html --cov-report=term-missing
        echo ""
        echo "✅ 覆盖率报告已生成: htmlcov/index.html"
        ;;
    
    debug)
        echo "🔧 运行诊断工具..."
        python3 debug_tool.py
        ;;
    
    log)
        echo "📝 查看日志..."
        if [ -d "logs" ]; then
            echo "日志文件列表:"
            ls -lh logs/*.log 2>/dev/null || echo "暂无日志文件"
            echo ""
            echo "最新 50 行应用日志:"
            tail -n 50 logs/app.log 2>/dev/null || echo "app.log 不存在"
        else
            echo "❌ logs 目录不存在"
        fi
        ;;
    
    monitor)
        echo "📊 实时监控日志..."
        if [ -f "logs/app.log" ]; then
            tail -f logs/app.log
        else
            echo "❌ app.log 不存在，请先运行应用"
        fi
        ;;
    
    *)
        echo "用法: $0 {unit|all|coverage|debug|log|monitor}"
        echo ""
        echo "命令说明:"
        echo "  unit      - 运行单元测试"
        echo "  all       - 运行所有测试（包括 Mock 测试）"
        echo "  coverage  - 运行测试并生成覆盖率报告"
        echo "  debug     - 运行系统诊断工具"
        echo "  log       - 查看日志文件"
        echo "  monitor   - 实时监控日志输出"
        exit 1
        ;;
esac
