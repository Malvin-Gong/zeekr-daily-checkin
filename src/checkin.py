#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极氪 App 每日日常任务与权益助手 (Zeekr Daily Checkin)
- 每日自动签到 (成长值 / 极分)
- 自动阅读每日指定文章 (获取免费碎片)
- 自动检索并领取未领取权益 (碎片、步行碳积分/能量球、极值球、7日抽奖)
- 拟人化随机波动与早中晚三时段智能决策
- 支持 iOS Bark 实时推送 (卡片富文本 + 专属车标图标)
- 零外部依赖 (纯标准库 urllib, json, time, hashlib, random, base64)
- 兼容 GitHub Actions (免服务器云端)、OpenWrt 软路由、Linux/NAS 与本地运行
"""
import urllib.request
import urllib.error
import json
import time
import hashlib
import random
import base64
import os
import sys

BASE_URL = "https://api-gw-toc.zeekrlife.com"
APP_SECRET = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCz09z6e9WOcNq+nUMX8Vq1Xe2EmJxuR3XbtureDCS90dfkok"
DEFAULT_AVATAR = "https://zeekrlife-oss.zeekrlife.com/IMAGE/1/client/default_avatar.jpeg"

def parse_jwt_user_info(token):
    """从 JWT 动态提取用户 accountId、昵称与车标头像 (无需用户手动配置)"""
    try:
        raw = token.replace("Bearer ", "").strip()
        parts = raw.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload_json = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
            sub_str = payload_json.get("sub", "{}")
            sub_json = json.loads(sub_str) if isinstance(sub_str, str) else sub_str
            account_dto = sub_json.get("accountInfoDTO", {})
            return {
                "accountId": str(account_dto.get("accountId", "")),
                "nickname": account_dto.get("nickname", "极氪车友"),
                "avatar": account_dto.get("avatar", DEFAULT_AVATAR)
            }
    except Exception:
        pass
    return {"accountId": "", "nickname": "极氪车友", "avatar": DEFAULT_AVATAR}

def load_config():
    """多级配置加载：环境变量 (GitHub Actions/Docker) > config.json > zeekr.conf"""
    conf = {}

    # 1. 尝试从本地配置文件读取
    candidates = [
        "config.json",
        os.path.join(os.path.dirname(__file__), "..", "config.json"),
        "/etc/zeekr/zeekr.conf",
        "zeekr.conf",
        os.path.join(os.path.dirname(__file__), "..", "zeekr.conf"),
    ]

    for p in candidates:
        if os.path.exists(p):
            if p.endswith(".json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        conf.update(json.load(f))
                        break
                except Exception:
                    pass
            elif p.endswith(".conf"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                conf[k.strip()] = v.strip().strip('"').strip("'")
                        break
                except Exception:
                    pass

    # 2. 环境变量具有最高优先级 (覆盖本地配置，适应 GitHub Actions / Docker)
    for env_key in ["ZEEKR_TOKEN", "BARK_KEY", "BARK_SERVER", "BARK_GROUP", "DEVICE_ID", "LOG_FILE"]:
        if os.environ.get(env_key):
            conf[env_key] = os.environ[env_key]

    return conf

def get_state_file_path(conf):
    """状态文件路径 (首选 /etc/zeekr，次选当前运行目录)"""
    if os.path.exists("/etc/zeekr"):
        return "/etc/zeekr/checkin_state.json"
    return os.path.join(os.path.dirname(__file__), "checkin_state.json")

def load_state(conf):
    path = get_state_file_path(conf)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(conf, state):
    path = get_state_file_path(conf)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 保存状态文件失败: {e}")

def get_headers(conf, token, method="POST"):
    device_id = conf.get("DEVICE_ID", "").strip()
    if not device_id:
        # 基于 Token 自动派生固定合法的 64 位十六进制设备指纹
        device_id = hashlib.sha256(token.encode("utf-8")).hexdigest()

    app_version = conf.get("APP_VERSION", "5.0.8")
    phone_version = conf.get("PHONE_VERSION", "27.3")
    phone_model = conf.get("PHONE_MODEL", "iPhone15ProMax")
    user_agent = f"ZeekrLife/{app_version} (iPhone; iOS {phone_version}; Scale/3.00){device_id}"

    ts = str(int(time.time() * 1000))
    nonce = "".join(str(random.randint(0, 9)) for _ in range(8))
    sign = hashlib.sha1("".join(sorted([APP_SECRET, nonce, ts])).encode("utf-8")).hexdigest()

    h = {
        "User-Agent": user_agent,
        "x_ca_sign": sign,
        "app_code": "toc_ios_zeekrapp",
        "app_version": app_version,
        "device_id": device_id,
        "phone_version": phone_version,
        "x_ca_nonce": nonce,
        "x_ca_key": "APP-SIGN-SECRET-KEY",
        "Version": "2",
        "x_ca_timestamp": ts,
        "request-original": "zeekr-app",
        "WorkspaceId": "prod",
        "riskVersion": "1",
        "Authorization": token,
        "Accept-Language": "zh-Hans-CN;q=1",
        "app_type": "IOS",
        "phone_model": phone_model,
        "x_ca_secret": APP_SECRET,
        "Accept": "*/*"
    }
    if method != "GET":
        h["Content-Type"] = "application/json"
    return h

def api_call(conf, token, path, method="POST", payload=None):
    url = BASE_URL + path
    headers = get_headers(conf, token, method)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {"code": "AUTH_ERROR", "msg": f"Token 失效或认证失败 (HTTP {e.code})"}
        return {"code": f"HTTP_{e.code}", "msg": str(e.reason)}
    except Exception as e:
        return {"code": "ERROR", "msg": str(e)}

def send_bark(conf, title, body, avatar_url=""):
    device_key = conf.get("BARK_KEY", "").strip()
    if not device_key:
        return
    url = conf.get("BARK_SERVER", "https://api.day.app").rstrip("/") + "/push"
    payload = {
        "device_key": device_key,
        "title": title,
        "body": body,
        "group": conf.get("BARK_GROUP", "极氪"),
        "icon": avatar_url or conf.get("BARK_ICON", DEFAULT_AVATAR),
        "ttl": 600
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 200:
                print("  📲 已通过 Bark 发送推送通知")
            else:
                print(f"  ⚠️ Bark 推送返回: {res}")
    except Exception as e:
        print(f"  ❌ Bark 推送失败: {e}")

def run_checkin_tasks(conf, slot_desc="即时触发"):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==========================================")
    print(f"极氪 App 每日日常任务启动: {start_time} [{slot_desc}]")
    print(f"==========================================")

    token = conf.get("ZEEKR_TOKEN", "").strip()
    if not token or "..." in token:
        print("[ERROR] 未配置有效 ZEEKR_TOKEN，请检查配置或环境变量！")
        sys.exit(1)

    user_info = parse_jwt_user_info(token)
    account_id = user_info.get("accountId", "")
    nickname = user_info.get("nickname", "极氪车友")
    avatar = user_info.get("avatar", DEFAULT_AVATAR)

    print(f"👤 当前车主: {nickname} (ID: {account_id[:6]}****{account_id[-4:] if len(account_id) > 10 else ''})")
    bark_lines = [f"👤 账号: {nickname}"]

    # 1. 每日签到
    print("[1/4] 执行每日签到...")
    center_res = api_call(conf, token, "/zeekrlife-mp-val/toc/v1/zgreen/center", "POST", {})
    if center_res.get("code") == "000000":
        info = center_res.get("data", {}).get("signInZgreenInfo", [])
        status_txt = "未知"
        streak_txt = ""
        for item in info:
            name = item.get("taskName", "")
            if name == "每日签到":
                status_txt = "今日已签到" if item.get("taskStatus") else "签到成功"
            elif "连续签到" in name:
                streak_txt = f"({name})"
        msg = f"✅ 每日签到: {status_txt} {streak_txt}"
        print(f"  {msg}")
        bark_lines.append(msg)
    else:
        msg = f"❌ 每日签到失败: {center_res.get('msg')}"
        print(f"  {msg}")
        bark_lines.append(msg)
        if center_res.get("code") == "AUTH_ERROR":
            err_msg = "⚠️ Token 已失效，请重新抓包更新!"
            bark_lines.append(err_msg)
            send_bark(conf, "🚨 极氪签到失败: Token 已失效", "\n".join(bark_lines), avatar)
            sys.exit(1)

    time.sleep(random.uniform(2.0, 3.5))

    # 2. 查询并完成阅读文章任务
    print("[2/4] 检查日常任务 (阅读文章)...")
    tasks_res = api_call(conf, token, "/zeekrlife-mp-mkt/open/v1/taskProgress/taskMsg", "POST", {
        "activityRecord": "medal_compose_task_manage",
        "optional": {"fetchTaskTakeAndReachTimesInfo": True}
    })
    read_done = False
    if tasks_res.get("code") == "000000":
        tasks = tasks_res.get("data", {}).get("taskReachMsgList", [])
        for t in tasks:
            if t.get("name") == "阅读文章":
                dto = t.get("taskTakeDTO") or {}
                if dto.get("currentComplete", 0) >= dto.get("maxCompleteLimit", 1):
                    print("  📖 阅读文章: 今日已完成，跳过")
                    bark_lines.append("📖 阅读文章: 今日已完成")
                    read_done = True
                else:
                    path_url = t.get("doc", {}).get("path", "")
                    article_id = "2033731556337631232"
                    if "acticleId=" in path_url:
                        article_id = path_url.split("acticleId=")[1].split("&")[0]
                    print(f"  📖 正在阅读文章 (ID: {article_id})...")
                    device_id = conf.get("DEVICE_ID", "") or hashlib.sha256(token.encode("utf-8")).hexdigest()
                    api_call(conf, token, "/zeekrlife-search-api/search/open/api/new/behaviorTrack", "POST", {
                        "mobileType": "iOS", "deviceId": device_id, "accountId": account_id,
                        "appVersion": conf.get("APP_VERSION", "5.0.8"), "type": 1, "businessId": article_id
                    })
                    time.sleep(1.0)
                    api_call(conf, token, f"/zeekrlife-bbs-theme/v1/invitation/pub/detail?id={article_id}", "GET")
                    time.sleep(1.0)
                    api_call(conf, token, f"/zeekrlife-bbs-theme/v1/comment/pub/list?moduleId={article_id}&moduleType=1&pageNo=1&pageSize=15", "GET")
                    api_call(conf, token, "/zeekrlife-bbs-theme/v1/invitation/pub/recommend", "POST", {"id": article_id})
                    print("  ✅ 阅读文章任务已完成")
                    bark_lines.append("📖 阅读文章: 已完成 (获新碎片)")
                    read_done = True
                break
    if not read_done:
        print("  ℹ️ 未找到待阅读文章任务或已完成")

    time.sleep(random.uniform(2.5, 4.0))

    # 3. 检索并领取未领取权益 (碎片, 能量球, 极值球)
    print("[3/4] 检索并领取未领取权益...")
    uncollected_res = api_call(conf, token, "/zeekrlife-mp-val/v1/carEnergy/getUncollectedBallsPageNew", "POST", {
        "accountId": account_id
    })
    total_val = 0
    integral_val = 0
    if uncollected_res.get("code") == "000000":
        data = uncollected_res.get("data", {})
        total_val = data.get("totalVal", 0)
        integral_val = data.get("integralTotalVal", 0)
        items = data.get("uncollectedVal") or []
        print(f"  当前碳积分总额: {total_val}, 极值积分: {integral_val}, 待领数量: {len(items)}")

        claimed_items = []
        debris_list = []
        other_list = []
        for it in items:
            val_type = it.get("valDefineCode")
            if val_type == "DEBRIS" or it.get("eventCode") == "medal_compose_easy_draw":
                debris_list.append(it)
            elif val_type == "CARBON_VALUE":
                # 该接口对参数校验较严，按候选参数顺序探测，第一个返回 000000 的即为有效组合
                r = None
                tried = []
                variants = [
                    {"accountId": account_id},
                    {"accountId": int(account_id) if str(account_id).isdigit() else account_id},
                    {"accountId": str(account_id), "energyType": "STEP"},
                    {"accountId": str(account_id), "valType": "CARBON_VALUE"},
                    {"accountId": str(account_id), "energyType": "CARBON_VALUE"},
                ]
                for v in variants:
                    r = api_call(conf, token, "/zeekrlife-mp-val/v1/carEnergy/collectedAllEnergy", "POST", v)
                    tried.append(f"{json.dumps(v, ensure_ascii=False)} => {r.get('code')} {r.get('msg')}")
                    if r.get("code") == "000000":
                        break
                if r and r.get("code") == "000000":
                    claimed_items.append("步行碳积分")
                else:
                    print(f"  ⚠️ 步行碳积分领取失败: 候选参数均未通过校验，转交 batchApply 兜底")
                    for t in tried:
                        print(f"    · {t}")
                    other_list.append(it)
            elif val_type == "ZEEKR_VALUE":
                r = api_call(conf, token, "/zeekrlife-mp-val/v1/carEnergy/collectIntegralZeekrBalls", "POST", {"accountId": account_id})
                if r.get("code") == "000000":
                    claimed_items.append("极值能量球")
                else:
                    print(f"  ⚠️ 极值能量球领取失败: {r.get('code')} {r.get('msg')}")
            else:
                # 兜底：未知 valDefineCode 也尝试走 batchApply，并打印结构便于后续排查
                print(f"  ℹ️ 未识别权益 valDefineCode={val_type} eventCode={it.get('eventCode')} id={it.get('id')}")
                print(f"  ℹ️ 原始数据: {json.dumps(it, ensure_ascii=False)[:500]}")
                other_list.append(it)

        apply_targets = debris_list + other_list
        if apply_targets:
            apply_cmds = [{
                "record": d.get("eventCode", "medal_compose_easy_draw"),
                "payContent": {"bubbleAssetsId": str(d.get("id"))},
                "applyExt": {"origin": d.get("sourceId", "阅读文章")}
            } for d in apply_targets]
            r = api_call(conf, token, "/zeekrlife-mp-mkt/toc/v1/apply/batchApply", "POST", {"applyCmdList": apply_cmds})
            if r.get("code") == "000000":
                res_list = r.get("data") or []
                for res_item in res_list:
                    mat_name = res_item.get("invoice", {}).get("materialSnapshot", {}).get("name", "碎片")
                    claimed_items.append(f"碎片 ({mat_name})")
                    print(f"  🎉 成功领取: {mat_name}")
            else:
                print(f"  ⚠️ batchApply 返回: {r.get('code')} {r.get('msg')}")

        if claimed_items:
            claimed_str = ", ".join(claimed_items)
            print(f"  ✅ 领取完成: {claimed_str}")
            bark_lines.append(f"🎁 领取权益: {claimed_str}")
        elif items:
            print(f"  ⚠️ 仍有 {len(items)} 项待领权益未领取成功，见上方诊断")
            print(f"::warning::仍有 {len(items)} 项待领权益未领取成功")
            bark_lines.append(f"🎁 领取权益: {len(items)} 项待领未成功")
        else:
            print("  ℹ️ 暂无待领取的碎片或能量球")
            bark_lines.append("🎁 领取权益: 暂无待领球/碎片")
    else:
        print(f"  ❌ 检索待领权益失败: {uncollected_res.get('msg')}")

    bark_lines.append(f"📊 账户资产: 碳积分 {total_val} | 极值 {integral_val}")
    bark_lines.append(f"⏰ 执行时间: {time.strftime('%H:%M:%S')} ({slot_desc})")

    # 4. 发送 Bark 推送通知
    print("[4/4] 任务总结与推送...")
    send_bark(conf, "🚗 极氪日常任务已完成", "\n".join(bark_lines), avatar)

    # 更新本地状态
    today = time.strftime("%Y-%m-%d")
    state = load_state(conf)
    state["last_completed_date"] = today
    state["last_completed_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["last_slot"] = slot_desc
    save_state(conf, state)

    print(f"极氪日常任务执行结束: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def handle_cron_dispatch(conf):
    """早中晚三时段智能随机调度算法 (30分钟窗口随机波动)"""
    today = time.strftime("%Y-%m-%d")
    state = load_state(conf)

    # 1. 检查今日是否已完成签到
    if state.get("last_completed_date") == today:
        print(f"[Cron] 今日 ({today}) 已在 {state.get('last_completed_time')} [{state.get('last_slot')}] 完成签到，本次调度跳过。")
        sys.exit(0)

    # 2. 判断当前处于哪个时段
    now = time.localtime()
    hour = now.tm_hour

    slot_name = ""
    prob = 1.0

    if hour < 10:
        slot_name = "早间时段 (07:30~08:00)"
        prob = 0.3333
    elif hour < 16:
        slot_name = "午间时段 (12:00~12:30)"
        prob = 0.5000
    else:
        slot_name = "晚间时段 (19:30~20:00，保底执行)"
        prob = 1.0000

    roll = random.random()
    if roll > prob:
        print(f"[Cron] 处于【{slot_name}】(骰子={roll:.2f} > 阈值={prob:.2f})，决策：本次时段跳过，顺延至下一时段。")
        sys.exit(0)

    # 3. 选中当前时段，在 30 分钟 (15 ~ 1785 秒) 范围内随机延迟
    delay_seconds = random.randint(15, 1785)
    target_ts = time.time() + delay_seconds
    target_time_str = time.strftime("%H:%M:%S", time.localtime(target_ts))

    print(f"[Cron] 🎲 命中时段: 【{slot_name}】!")
    print(f"[Cron] ⏳ 随机波动延时: {delay_seconds // 60} 分 {delay_seconds % 60} 秒，将在 {target_time_str} 执行签到...")

    time.sleep(delay_seconds)
    run_checkin_tasks(conf, slot_desc=f"{slot_name} 波动至 {target_time_str}")

def main():
    conf = load_config()

    # 自动维护内存日志大小 (超过 200KB 保留最新 200 行，避免 RAM 溢出)
    log_file = conf.get("LOG_FILE", "/var/log/zeekr_checkin.log")
    if os.path.exists(log_file) and os.path.getsize(log_file) > 200 * 1024:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as lf:
                lines = lf.readlines()[-200:]
            with open(log_file, "w", encoding="utf-8") as lf:
                lf.writelines(lines)
        except Exception:
            pass

    args = sys.argv[1:]
    if "--gha" in args:
        # GitHub Actions 运行模式：轻度随机防并发延迟 (10~180 秒)
        jitter = random.randint(10, 180)
        print(f"[GitHub Actions] 防并发随机延迟 {jitter} 秒...")
        time.sleep(jitter)
        run_checkin_tasks(conf, slot_desc="GitHub Actions 云端执行")
    elif "--cron" in args:
        handle_cron_dispatch(conf)
    elif "--check-missed" in args:
        today = time.strftime("%Y-%m-%d")
        state = load_state(conf)
        if state.get("last_completed_date") != today and time.localtime().tm_hour >= 20:
            print(f"[Check-Missed] 检测到今日尚未签到且已过晚间窗口，立即补签！")
            run_checkin_tasks(conf, slot_desc="开机防遗漏补签")
    else:
        # 手动执行模式（无延迟，即时触发）
        run_checkin_tasks(conf, slot_desc="手动即时触发")

if __name__ == "__main__":
    main()
