# FreeTodo 本机部署与迁移说明

最后更新：2026-11-10

## 当前推荐布局

- 源码仓库：`/Users/ctl/Local_Documents/1_personal_projs/FreeTodo/`
- 稳定应用：`/Applications/FreeTodo.app`
- 个人数据：`~/Library/Application Support/FreeTodo/lifetrace-data/`
- 开发启动器：仓库根目录的 `Start-FreeTodo-Dev.command`
- 一键更新器：仓库根目录的 `Build-and-Install-FreeTodo.command`

`.venv/`、`free-todo-frontend/node_modules/` 和构建目录都可以重建，不属于必须备份的个人数据。

## 从旧 localhost 布局迁移

旧布局把个人数据放在仓库内的 `local-user-data/`。第一次构建稳定版或启动 Dev 模式时，脚本仅在新数据目录为空时复制旧数据：

```text
仓库/local-user-data/
        ↓
~/Library/Application Support/FreeTodo/lifetrace-data/
```

如果新目录已有内容，脚本不会覆盖。迁移前后都不会删除旧目录。

## 日常启动与停止

- 稳定版：从 `/Applications`、Launchpad 或 Dock 打开 `FreeTodo`。
- 开发版：双击 `Start-FreeTodo-Dev.command`，保持 Terminal 开启，按 `Control+C` 停止。
- 不要同时运行稳定版和开发版。
- 原有的 `Start-FreeTodo.command` 只用于旧 localhost 布局，不再作为推荐日常入口。

## 迁移到另一台 Apple Silicon Mac

1. 退出稳定版并停止 Dev 模式。
2. 在新 Mac 上克隆同一 fork 和所需分支。
3. 安装 Node/pnpm、Python/uv，并重建 `.venv` 与 `node_modules`。
4. 安全复制整个个人数据目录：

   ```text
   ~/Library/Application Support/FreeTodo/lifetrace-data/
   ```

5. 在新 Mac 的仓库根目录运行 `Build-and-Install-FreeTodo.command`。
6. 在 macOS 中重新授予通知、麦克风、屏幕录制等系统权限。

也可以保留生成的 arm64 DMG，但源码、构建工具和个人数据仍应分别备份。

## 安全说明

`lifetrace-data/config/config.yaml` 包含 Qwen、Tavily 等 API Key。迁移介质和备份文件必须妥善保管，不能提交到 GitHub 或公开分享。

