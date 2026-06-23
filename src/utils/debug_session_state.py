#!/usr/bin/env python3
"""
启用调试日志 - 分析session_state刷新问题

在app.py开头添加以下代码，帮助诊断问题
"""

import streamlit as st

# 在app.py最开始添加（第6行之后）
# 添加session_state变更追踪
original_setitem = st.session_state.__class__.__setitem__

def traced_setitem(self, key, value):
    print(f"[SESSION_STATE] 设置: {key} = {value}")
    return original_setitem(self, key, value)

st.session_state.__class__.__setitem__ = traced_setitem

# 添加session_state删除追踪
original_delitem = st.session_state.__class__.__delitem__

def traced_delitem(self, key):
    print(f"[SESSION_STATE] 删除: {key}")
    return original_delitem(self, key)

st.session_state.__class__.__delitem__ = traced_delitem

print("=" * 60)
print(" Session State 调试追踪已启用")
print("=" * 60)

