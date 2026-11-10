# FreeTodo macOS 稳定版与开发版指南

最后更新：2026-11-10

## 两种运行模式

### 稳定版 FreeTodo.app

- 日常使用时双击 `/Applications/FreeTodo.app`。
- App 自动启动内置的 Next.js 前端和 Python 后端，不需要手动打开 localhost。
- 稳定版使用构建时的源码快照；修改仓库源码后，需要重新构建和安装。
- 个人数据不在 App 安装包中，更新或替换 App 不会覆盖个人数据。

### FreeTodo Dev

- 开发调试时双击仓库根目录的 `Start-FreeTodo-Dev.command`。
- 后端直接运行仓库中的 Python 源码，前端运行 Next.js 开发服务器。
- 前端代码支持 hot reload；修改后端代码后需要重启 Dev 启动器。
- Dev 模式会保持一个 Terminal 窗口；按 `Control+C` 即可停止。

两种模式共享同一个个人数据目录，因此不可同时运行。Dev 启动器会先请求稳定版退出；如果开发端口已被其他程序占用，它会停止并报告问题，不会杀死未知进程。

## 个人数据目录

稳定版和 Dev 版统一使用：

```text
~/Library/Application Support/FreeTodo/lifetrace-data/
```

其中包括：

- `config/config.yaml`：API Key 和本地设置。
- `data/lifetrace.db`：主要 Todo、聊天等 SQLite 数据。
- `data/scheduler.db`：调度任务数据。
- `data/vector_db/`：本地向量检索数据。
- `data/audio/`：音频数据。
- `logs/`：运行日志。

这个目录包含私密数据和 API Key，不得提交到 Git，也不应放入公开网盘。

## 第一次迁移

第一次运行 `Build-and-Install-FreeTodo.command` 或 `Start-FreeTodo-Dev.command` 时：

1. 如果目标数据目录为空，脚本把仓库中的旧 `local-user-data/` 完整复制过去。
2. 如果目标目录已经包含任何数据，迁移会跳过，不覆盖已有数据库或配置。
3. 旧 `local-user-data/` 不会被删除，可暂时作为迁移前备份。

确认 App 中的待办和设置完整后，再单独决定是否归档旧目录。

## 修改源码后更新稳定版

双击仓库根目录的：

```text
Build-and-Install-FreeTodo.command
```

脚本依次执行：

1. 检查 macOS 与 Apple Silicon 架构。
2. 检查至少 3 GiB 可用磁盘空间。
3. 安全执行一次性数据迁移。
4. 运行后端测试、Biome 和 TypeScript 检查。
5. 构建 Next.js、PyInstaller 后端和 arm64 Electron App。
6. 验证产物确实为 arm64 `FreeTodo.app`。
7. 关闭旧版 App，临时备份旧 App，再安装新版。
8. 启动失败时恢复旧 App；成功后删除临时 App 备份。

整个更新过程不会删除或替换 `lifetrace-data`。

## 手动备份与恢复

备份前先退出稳定版并停止 Dev 模式，然后复制：

```bash
ditto "$HOME/Library/Application Support/FreeTodo/lifetrace-data" \
  "$HOME/Desktop/FreeTodo-data-backup"
```

恢复时也必须先退出所有 FreeTodo 进程。建议把当前目录另存一份，再用 `ditto` 恢复备份；不要让两个 FreeTodo 实例同时写同一个 SQLite 数据库。

## 当前限制

- 当前构建只面向这台 Apple Silicon MacBook Air。
- 当前是本机自用构建，没有 Apple Developer ID notarization，也没有 GitHub 自动更新。
- 更新源码不会实时改变已安装 App；必须重新运行一键构建安装器。
- 手机端、Google Calendar 双向同步和 Habitica 联动仍属于后续项目。

