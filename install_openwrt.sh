#!/bin/sh
# ==============================================================================
# 极氪 App 每日日常任务 OpenWrt 软路由一键安装脚本
# 项目地址: https://github.com/Zer0xPoint/zeekr-daily-checkin
# ==============================================================================

set -e

echo "=================================================="
echo "🚗 极氪 App 自动化日常助手 - OpenWrt 部署向导"
echo "=================================================="

# 1. 检查 Python 3 环境
if ! command -v python3 >/dev/null 2>&1; then
    echo "⚠️ 检测到路由器尚未安装 Python3，正在通过 opkg 自动安装..."
    opkg update
    opkg install python3
fi

# 2. 交互式录入凭证
echo ""
echo "👉 请粘贴抓包获取的完整 Authorization (包含 Bearer 前缀):"
read -r USER_TOKEN

if [ -z "$USER_TOKEN" ]; then
    echo "❌ 错误: Token 不能为空！"
    exit 1
fi

echo ""
echo "👉 请输入 iOS Bark Key (可选，直接回车跳过):"
read -r USER_BARK_KEY

# 3. 创建配置目录与加锁配置文件
echo ""
echo "⚙️ 正在配置安全隔离存储 (/etc/zeekr/zeekr.conf)..."
mkdir -p /etc/zeekr

cat <<EOF > /etc/zeekr/zeekr.conf
# 极氪自动化安全配置 (chmod 600 仅 root 可读写)
ZEEKR_TOKEN="$USER_TOKEN"
DEVICE_ID=""
BARK_KEY="$USER_BARK_KEY"
BARK_SERVER="https://api.day.app"
BARK_GROUP="极氪"
LOG_FILE="/var/log/zeekr_checkin.log"
EOF

chmod 600 /etc/zeekr/zeekr.conf

# 4. 下载核心执行引擎
echo "📥 正在下载核心自动化引擎到 /usr/bin/zeekr_checkin.py..."
curl -sSL "https://raw.githubusercontent.com/Zer0xPoint/zeekr-daily-checkin/main/src/checkin.py" -o /usr/bin/zeekr_checkin.py
chmod 755 /usr/bin/zeekr_checkin.py

# 5. 配置固件升级保护
grep -q '/etc/zeekr/zeekr.conf' /etc/sysupgrade.conf 2>/dev/null || echo '/etc/zeekr/zeekr.conf' >> /etc/sysupgrade.conf

# 6. 配置早中晚三时段 Cron 计划任务
echo "⏰ 配置早中晚智能随机调度计划任务 (07:30 / 12:00 / 19:30)..."
sed -i '/zeekr_checkin.py/d' /etc/crontabs/root 2>/dev/null || true

echo '30 7 * * * /usr/bin/python3 /usr/bin/zeekr_checkin.py --cron >> /var/log/zeekr_checkin.log 2>&1' >> /etc/crontabs/root
echo '0 12 * * * /usr/bin/python3 /usr/bin/zeekr_checkin.py --cron >> /var/log/zeekr_checkin.log 2>&1' >> /etc/crontabs/root
echo '30 19 * * * /usr/bin/python3 /usr/bin/zeekr_checkin.py --cron >> /var/log/zeekr_checkin.log 2>&1' >> /etc/crontabs/root

# 7. 配置开机自检防遗漏
if [ -f /etc/rc.local ]; then
    grep -q 'zeekr_checkin.py' /etc/rc.local || sed -i '/exit 0/i (sleep 30 && /usr/bin/python3 /usr/bin/zeekr_checkin.py --check-missed >> /var/log/zeekr_checkin.log 2>&1) &' /etc/rc.local
fi

/etc/init.d/cron restart

# 8. 执行首次联调测试
echo ""
echo "🚀 正在执行首次联调验证测试..."
python3 /usr/bin/zeekr_checkin.py

echo ""
echo "=================================================="
echo "🎉 安装完成！极氪日常任务引擎已在后台全天候守护。"
echo "每天将在早中晚三个时段中智能随机抽取并自动波动打卡。"
echo "查看运行日志命令: cat /var/log/zeekr_checkin.log"
echo "=================================================="
