# 黄果短剧热更新

独立于 APK 发布仓库。客户端从本仓库 latest release 的 hot-update.json 下载签名清单与资源包。私钥保存在本机签名目录，仓库只包含公钥。

## 修改和发布

- site.json：域名、请求头、路径模板、页面选择器、JSON 字段别名、封面域名与已有解密参数。
- theme.json：启用开关、带时区的起止时间、明暗主题颜色、背景、底栏尺寸和图标。
- theme/：主题图片、SVG 图标与可选 CSS。
- release.json：独立递增的 revision、显示版本、最低 APK versionCode 与 bridgeVersion。

Python 需要 cryptography；GitHub 发布使用已登录的 gh CLI。

```powershell
python publish.py
python publish.py --web
python publish.py --web --publish
```

普通规则或主题包不必包含界面。完整界面包从相邻 Android Version/app/src/main/assets 构建，也可以用 --assets 指定路径。资源包启用时整套替换；缺省界面使用 APK 内置版本。只发主题或规则包会保留客户端最后验证成功的界面，无需重复下载整套界面。release.json 的 resetUi=true 可明确恢复 APK 内置界面。

每次发布先递增 release.json 中的 revision。已有 revision 不可覆盖。回退内容也必须用更大的 revision 重新发布，避免客户端重复启用已失败的包。正式 APK 可以独立升级；bridgeVersion=1 的兼容包可继续使用。

## 主题格式

light/dark 接受 --bg、--panel、--text、--muted、--accent、--dock、--line 颜色。background 使用 asset（theme/ 下的相对路径）与 opacity（0..1），只出现在首页。dock 支持 radiusDp、buttonRadiusDp、heightDp，以及 icons.home/adult/ai/library。css 可指向 theme/ 下的额外 CSS。startsAt/endsAt 使用包含时区的 ISO 8601，例如 2026-10-01T00:00:00+08:00；到期自动恢复普通样式。

## 客户端契约

完整界面必须保留 app.html/app.js/app.css，app.html 加载 runtime.js、hot-runtime.js 再加载 app.js。runtime 与主题/健康引导由 APK 固定提供。app.js 初始化成功后调用 window.hgBootReady()；未确认成功的试用包会回退至上一可用版本。

资源下载和校验在后台，启动不依赖 GitHub 连通。首次打开新包标记为试用，成功后确认；坏签名、不兼容包、损坏文件和路径越界会被拒绝。账号、收藏和观看历史存储在原生应用中，不属于资源包。

## 封面与路径

cover.mode 支持 aes-cbc、plain、auto；AES/CBC/NoPadding 和 AES/CBC/PKCS5Padding，密钥编码支持 text/hex/base64。hostRewrites 可将历史封面域名映射到新的 allowedHosts。headerRepair=legacy-xor 保留旧修复规则，none 关闭；bytePatches 可以按 offset/from/to 条件替换字节。全新解密算法或新的原生功能仍需要 APK。

routes 定义路径模板，patterns 定义链接匹配规则。fields.content/hero 的值为字段别名数组，支持点分隔嵌套字段（例如 stream.url）。规则改变后仅清理目录缓存，收藏和观看进度保留。

## 首页庆祝 Banner

theme.json 中的 campaigns 数组可添加本地宣传页，独立于全局主题 enabled 开关。每项包含 id、title、description、artwork（theme/ 下的英文资源路径）、startsAt/endsAt（带时区）、dateLabel、button、message。活动在有效期内加入首页轮播首位，点击打开庆祝页，系统返回或页面返回恢复首页。活动到期后自动退出轮播。修改或移除活动配置后发布更大的 revision 即可，无需修改 APK。

首次支持此入口的前端资源版本为 2026.10.01.2。后续只改活动配置可以单独发布规则/主题包，客户端继续沿用已有前端。
