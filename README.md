# Zeekr Daily Checkin (极氪日常权益助手)

专为极氪车主打造的轻量自动化日常任务工具。每日全自动完成签到、阅读任务与权益收集，支持早中晚随机时段波动打卡及 iOS Bark 实时推送。

---

## 一、 功能亮点

- **全自动日常任务**：自动完成 App 每日签到、阅读指定文章（获取免费碎片）、一键收割所有待领权益（碎片、步行碳积分、能量球、极值球）。
- **拟人化防风控调度**：
  - 早（07:30~08:00）、中（12:00~12:30）、晚（19:30~20:00）三时段等概率（各 1/3）随机挑选。
  - 选中时段后在 30 分钟窗口内随机延时（15~1785秒）触发，彻底打破固定打卡痕迹。
  - 当日成功一次后立即锁定，其余时段毫秒级静默退出。
- **免手动配置**：自动从 JWT 动态解析用户 ID、昵称和车标头像，自动生成合法设备指纹。
- **iOS Bark 实时推送**：打卡完成即时推送卡片消息，直观汇报获得的碎片与当前碳积分总额。
- **零依赖与多环境支持**：纯 Python 3 标准库打造，完美支持 **GitHub Actions（免费云端、零服务器）**、**OpenWrt 软路由** 及 **Linux/本地** 运行。

---

## 二、 凭证获取指引 (3分钟快速完成)

### 1. 抓取极氪 Token (Authorization)
> [!TIP]
> **避开干扰请求的核心技巧**：极氪 App 启动时会产生大量图片与监控请求。在抓包工具中**直接全局搜索关键词 `Bearer`**，能秒级定位到核心凭证！

1. 手机连接 Wi-Fi，打开抓包软件（iOS 推荐使用 **Stream**，Android 推荐使用 **Reqable**）。
2. 在抓包工具中开启抓包并信任 HTTPS 证书。
3. 打开手机上的 **极氪 App**，进入【我的】或【社区】页面下拉刷新。
4. 回到抓包软件停止抓包，在历史请求列表中点击搜索，输入关键词：`Bearer`。
5. 点开搜索到的任意一个请求，查看 **请求头 (Request Headers)**。
6. 找到 `Authorization` 字段，完整复制其内容（格式为 `Bearer eyJhbGciOi...` 这一长串）。

### 2. 获取 iOS Bark Key
1. 在 iPhone 上的 App Store 下载安装 **Bark**（免费无广告）。
2. 打开 Bark App，首页中间会显示一条专属链接（例如 `https://api.day.app/YOUR_KEY/`）。
3. 复制其中的 `YOUR_KEY` 字符串即可。

---

## 三、 快速部署方式

### 方式 A：GitHub Actions 云端全自动 (推荐：零成本、免服务器)

车友无需任何软路由或云服务器，直接借助 GitHub 免费云端每日定时执行：

1. **Fork 本仓库** 到你个人的 GitHub 账号。
2. 进入你 Fork 后的仓库页面，点击 **Settings -> Secrets and variables -> Actions**。
3. 点击 **New repository secret**，添加以下两项配置：
   - `ZEEKR_TOKEN`：填入抓包获取的完整 Token（包含 `Bearer ` 前缀）。
   - `BARK_KEY`：填入你的 Bark 专属 Key（可选，不填则不推 Bark）。
4. 点击仓库上方的 **Actions** 标签，点击 `I understand my workflows, go ahead and enable them` 启用工作流。
5. （可选测试）在 Actions 列表中选择 `极氪每日日常任务`，点击右侧的 `Run workflow` 手动测试一次，手机即可收到推送。

---

### 方式 B：OpenWrt 软路由一键安装

适合家中拥有 24 小时在线软路由或 Linux 掌柜：

1. 通过 SSH 登录你的 OpenWrt 软路由后台。
2. 执行以下一键部署脚本：
   ```sh
   curl -sSL https://raw.githubusercontent.com/Zer0xPoint/zeekr-daily-checkin/main/install_openwrt.sh | sh
   ```
3. 按照终端屏幕提示粘贴你的 Token 与 BarkKey。脚本将自动完成环境检测、文件部署（权限 600 安全加锁）以及 Crontab 早中晚三时段调度注入。

---

### 方式 C：本地或服务器直接运行

1. 克隆本仓库：
   ```sh
   git clone https://github.com/Zer0xPoint/zeekr-daily-checkin.git
   cd zeekr-daily-checkin
   ```
2. 复制配置模板并填入信息：
   ```sh
   cp config.example.json config.json
   ```
3. 执行打卡：
   ```sh
   python3 src/checkin.py
   ```

---

## 四、 常见问题 (FAQ)

- **Q: Token 有效期有多久？**
  - A: 极氪 App 的 JWT Token 具有较长的生命周期。只要你不在手机 App 内部主动点击“退出登录”，通常可稳定运行数月至一年。如果 Token 自然过期，Bark 将推送失效预警，重新抓包替换即可。
- **Q: 为什么每天收到推送的时间都不一样？**
  - A: 这是内置的防风控算法。脚本会在早、中、晚三个合理的生活作息时段中随机选择，并在对应时段内随机等待 0~30 分钟再发包，模拟真实人工打卡操作。

---

## 免责声明

1. 本项目仅供 Python 编程技术交流、接口自动化研究与车主自用，严禁用于商业牟利或违规非法用途。
2. 使用本项目造成的任何权益变动、接口限制或相关风险，由使用者自行承担。
