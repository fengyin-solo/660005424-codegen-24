# 分布式日志聚合与智能异常检测平台

基于Vue 3 + FastAPI的企业级日志分析平台，正则/Grok解析、滑动窗口聚合、3-sigma+IQR双算法异常检测、全文检索。

## 目标用户
SRE工程师、DevOps团队、系统运维人员

## 技术栈
- 前端: Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts
- 后端: Python FastAPI + NumPy + SQLite + WebSocket

## 核心功能
1. 多源日志流接入：支持Apache/NGINX/应用JSON/自定义格式四种日志类型模拟
2. 正则/Grok日志解析引擎：自动提取timestamp/level/source/message字段
3. 滑动时间窗口聚合统计：1分钟/5分钟/15分钟三级聚合粒度
4. 3-sigma + IQR双算法异常检测：分别基于正态分布和四分位距的异常分数计算
5. 倒排索引全文搜索：TF-IDF词频+布尔AND/OR查询
6. 告警规则管理：支持阈值告警+异常分数告警+关键词命中告警三级
7. ECharts日志量趋势+异常分布热力图+告警时间线
8. 大屏数据权限：账号级 source/level 二维授权（allow/deny）、未授权占位、越权拒绝、启用校验与版本化口径

## 大屏数据权限
- 入口：工具栏「🖥 进入大屏」；「🔑 授权管理」配置账号授权清单
- 授权维度：数据来源（14 个 source）× 日志级别（INFO/WARN/ERROR/DEBUG），deny 优先
- 未授权模块在大屏上以 🔒 占位说明呈现，不显示 0 或空值
- 显式请求未授权对象返回 `403 out_of_scope` 并在 `denied` 中逐项写明原因；大屏未启用返回 `403 screen_disabled`
- 授权清单为空、含重复/allow-deny 冲突、未知对象或生效后无任一维度放行时，启用被整单拒绝（`400 invalid_grants`），`errors` 逐条列出不合格项，原状态保持不变
- 每次成功启用生成不可变口径版本（v1、v2…），数据由 `账号+版本` 固定种子派生；多窗口通过 BroadcastChannel + 轮询对齐同一版本，切回普通模式后原有面板标题/图例/布局保持不变
- 预置账号：`admin`（全量）、`viewer-a`（全部来源，仅 INFO/WARN）、`viewer-b`（空清单，未启用，用于演示启用失败）、`viewer-c`（草稿态）

