# -*- coding: utf-8 -*-
"""SPT DeskPet - 星露谷物语小游戏

This is a desktop/PyQt adaptation of the supplied SeaDice farming plugin.
The original plugin's group/multi-user-only concepts (mentions, stealing other
players and GM-only cheats) are intentionally not exposed in the single-player
SPT UI. Core farming, shop, warehouse, fishing, weather, events and voyage
mechanics are retained.
"""
import json
import os
import random
import sys
import time
from datetime import date

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget
)

MAX_LEVEL = 20
MAX_FIELDS = 30
BASE_STEAL_COOLDOWN = 60000
WEATHER_TYPES = ["晴天", "雨天", "多云", "大风"]
WEATHER_GROWTH_FACTOR = {"晴天": 1.0, "雨天": 1.1, "多云": 0.95, "大风": 1.2}
PLANT_EVENTS = ["小精灵催熟", "女巫药水致死", "狗熊压坏作物"]

STORE = {
    "防风草种子": {"price": 50, "level": 1, "type": "seed"},
    "胡萝卜种子": {"price": 60, "level": 1, "type": "seed"},
    "白萝卜种子": {"price": 70, "level": 2, "type": "seed"},
    "花椰菜种子": {"price": 70, "level": 2, "type": "seed"},
    "小白菜种子": {"price": 70, "level": 2, "type": "seed"},
    "青豆种子": {"price": 70, "level": 2, "type": "seed"},
    "肥料": {"price": 100, "level": 2, "type": "tool"},
    "土豆种子": {"price": 75, "level": 3, "type": "seed"},
    "大黄种子": {"price": 80, "level": 3, "type": "seed"},
    "甘蓝菜种子": {"price": 80, "level": 3, "type": "seed"},
    "葡萄种子": {"price": 80, "level": 3, "type": "seed"},
    "向日葵种子": {"price": 90, "level": 3, "type": "seed"},
    "玫瑰花种子": {"price": 90, "level": 3, "type": "seed"},
    "扩容田地": {"price": 500, "level": 3, "type": "expand"},
    "土狗": {"price": 1000, "level": 3, "type": "dog"},
    "草莓种子": {"price": 100, "level": 4, "type": "seed"},
    "辣椒种子": {"price": 100, "level": 4, "type": "seed"},
    "甜瓜种子": {"price": 105, "level": 4, "type": "seed"},
    "红叶卷心菜种子": {"price": 105, "level": 4, "type": "seed"},
    "杨桃种子": {"price": 110, "level": 4, "type": "seed"},
    "郁金香种子": {"price": 105, "level": 4, "type": "seed"},
    "玫瑰仙子种子": {"price": 110, "level": 4, "type": "seed"},
    "鱼饵": {"price": 20, "level": 4, "type": "tool"},
    "茄子种子": {"price": 110, "level": 5, "type": "seed"},
    "苋菜种子": {"price": 110, "level": 5, "type": "seed"},
    "山药种子": {"price": 110, "level": 5, "type": "seed"},
    "夏季亮片种子": {"price": 120, "level": 5, "type": "seed"},
    "虞美人种子": {"price": 150, "level": 5, "type": "seed"},
    "桃树种子": {"price": 120, "level": 5, "type": "seed"},
    "苹果树种子": {"price": 120, "level": 5, "type": "seed"},
    "香蕉树种子": {"price": 150, "level": 5, "type": "seed"},
    "宝石甜莓种子": {"price": 200, "level": 5, "type": "seed"},
    "扩容田地ii": {"price": 1000, "level": 5, "type": "expand"},
}

FISH_PRICES = {
    "鲤鱼": 20, "鲱鱼": 30, "小嘴鲈鱼": 30, "太阳鱼": 45, "鳀鱼": 45,
    "沙丁鱼": 45, "河鲈": 50, "鲢鱼": 50, "鲷鱼": 50, "红鲷鱼": 55,
    "海参": 55, "虹鳟鱼": 55, "大眼鱼": 60, "西鲱": 60, "大头鱼": 60,
    "大嘴鲈鱼": 60, "鲑鱼": 60, "鬼鱼": 65, "罗非鱼": 65, "木跃鱼": 65,
    "狮子鱼": 65, "比目鱼": 70, "大比目鱼": 70, "午夜鲤鱼": 70,
    "史莱姆鱼": 70, "虾虎鱼": 70, "红鲻鱼": 75, "青花鱼": 75, "狗鱼": 75,
    "虎纹鳟鱼": 75, "蓝铁饼鱼": 75, "沙鱼": 75,
}
FISH_POOL_LV4 = ["鲤鱼", "鲱鱼", "小嘴鲈鱼", "太阳鱼", "鳀鱼"]
FISH_POOL_LV5 = FISH_POOL_LV4 + ["沙丁鱼", "河鲈", "鲢鱼", "鲷鱼", "红鲷鱼", "海参", "虹鳟鱼"]
FISH_POOL_LV6 = FISH_POOL_LV5 + ["大眼鱼", "西鲱", "大头鱼", "大嘴鲈鱼", "鲑鱼", "鬼鱼"]
FISH_POOL_LV7 = FISH_POOL_LV6 + ["罗非鱼", "木跃鱼", "狮子鱼", "比目鱼", "大比目鱼", "午夜鲤鱼"]
FISH_LEVEL_REQUIREMENTS = {x: 8 for x in FISH_PRICES}
for x in FISH_POOL_LV7: FISH_LEVEL_REQUIREMENTS[x] = 7
for x in FISH_POOL_LV6: FISH_LEVEL_REQUIREMENTS[x] = 6
for x in FISH_POOL_LV5: FISH_LEVEL_REQUIREMENTS[x] = 5
for x in FISH_POOL_LV4: FISH_LEVEL_REQUIREMENTS[x] = 4

VOYAGE_TYPES = {
    "近海远航": {"duration": 30 * 60 * 1000, "moneyMin": 80, "moneyMax": 160, "expMin": 20, "expMax": 40, "baitMin": 0, "baitMax": 2},
    "深海远航": {"duration": 60 * 60 * 1000, "moneyMin": 180, "moneyMax": 320, "expMin": 35, "expMax": 80, "baitMin": 1, "baitMax": 3},
    "远洋远航": {"duration": 120 * 60 * 1000, "moneyMin": 320, "moneyMax": 560, "expMin": 60, "expMax": 120, "baitMin": 2, "baitMax": 5},
}
SHIPWRECK_CHANCE = {"近海远航": 0.2, "深海远航": 0.25, "远洋远航": 0.3}


def app_path(name):
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


def now_ms():
    return int(time.time() * 1000)


def today_str():
    return date.today().isoformat()


def fmt_duration(ms):
    total = max(0, int((float(ms) + 59999) // 60000))
    h, m = divmod(total, 60)
    if h <= 0:
        return f"{m}分钟"
    if m <= 0:
        return f"{h}小时"
    return f"{h}小时{m}分钟"


def default_user():
    return {
        "id": "desktop",
        "name": "农夫",
        "fields": 6,
        "money": 200,
        "level": 1,
        "experience": 0,
        "crops": {},
        "warehouse": {"防风草种子": 6},
        "lastSignInDate": "",
        "purchasedFields": {},
        "fishPond": 0,
        "lastFishPondRefresh": "",
        "wormCatchCount": 0,
        "lastWormCatchDate": "",
        "hasDog": False,
        "explorationType": None,
        "explorationStartTime": None,
        "explorationShipwreck": False,
    }


class FarmGame:
    """Single-player desktop version of the supplied farming game."""
    def __init__(self):
        self.user = self._load()
        self.weather = self._load_weather()
        self.last_message = ""
        self.refresh_daily()

    def _load(self):
        p = app_path("spt_farmland.json")
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            u = default_user()
            if isinstance(raw, dict): u.update(raw)
            u["crops"] = u.get("crops") if isinstance(u.get("crops"), dict) else {}
            u["warehouse"] = u.get("warehouse") if isinstance(u.get("warehouse"), dict) else {}
            u["fields"] = max(1, min(MAX_FIELDS, int(u.get("fields", 6))))
            u["level"] = max(1, min(MAX_LEVEL, int(u.get("level", 1))))
            u["money"] = max(0, int(u.get("money", 200)))
            u["experience"] = max(0, int(u.get("experience", 0)))
            return u
        except Exception:
            return default_user()

    def save(self):
        p = app_path("spt_farmland.json")
        tmp = p + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.user, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)
        except Exception as e:
            self.last_message = f"存档失败：{e}"

    def _load_weather(self):
        p = app_path("spt_farmland_weather.json")
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("date") == today_str() and d.get("weather") in WEATHER_TYPES:
                return d["weather"]
        except Exception:
            pass
        w = random.choice(WEATHER_TYPES)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"date": today_str(), "weather": w}, f, ensure_ascii=False)
        except Exception:
            pass
        return w

    def refresh_daily(self):
        u = self.user
        if u.get("lastFishPondRefresh") != today_str():
            u["lastFishPondRefresh"] = today_str()
            u["fishPond"] = random.randint(15, 25)
        if u.get("lastWormCatchDate") != today_str():
            u["lastWormCatchDate"] = today_str()
            u["wormCatchCount"] = 0
        self._process_voyage()
        self.save()

    def _exp_need(self, level):
        return max(1, int(level)) * 100

    def _total_exp(self, level):
        return sum(self._exp_need(i) for i in range(1, max(1, int(level))))

    def _sync_level(self):
        ups = 0
        while self.user["level"] < MAX_LEVEL and self.user["experience"] >= self._total_exp(self.user["level"] + 1):
            self.user["level"] += 1
            ups += 1
        return ups

    def _add(self, item, amount):
        amount = int(amount)
        if amount <= 0: return
        self.user["warehouse"][item] = int(self.user["warehouse"].get(item, 0)) + amount

    def _remove(self, item, amount):
        amount = int(amount)
        have = int(self.user["warehouse"].get(item, 0))
        if amount <= 0 or have < amount: return False
        left = have - amount
        if left <= 0: self.user["warehouse"].pop(item, None)
        else: self.user["warehouse"][item] = left
        return True

    def _empty_fields(self):
        return [i for i in range(1, self.user["fields"] + 1) if f"田地{i}" not in self.user["crops"]]

    def _crop_output(self, seed):
        return seed[:-2] if seed.endswith("种子") else seed

    def _growth_ms(self, seed):
        lv = STORE.get(seed, {}).get("level", 1)
        return (30 + lv * 30) * 60 * 1000

    def _fish_pool(self):
        lv = max(4, int(self.user["level"]))
        return [x for x in FISH_PRICES if FISH_LEVEL_REQUIREMENTS.get(x, 8) <= lv] or FISH_POOL_LV4

    def status_text(self):
        self.refresh_daily()
        u = self.user
        lines = [
            f"农夫：{u['name']}", f"天气：{self.weather}",
            f"等级：{u['level']}　经验：{u['experience']}",
            f"金币：{u['money']}　田地：{u['fields']}/{MAX_FIELDS}",
            f"土狗：{'已拥有' if u.get('hasDog') else '未拥有'}",
        ]
        if u["level"] < MAX_LEVEL:
            lines.append(f"距离下一级还需：{max(0, self._total_exp(u['level'] + 1) - u['experience'])} 经验")
        for i in range(1, u["fields"] + 1):
            slot = u["crops"].get(f"田地{i}")
            if not slot:
                lines.append(f"田地{i}：空")
            else:
                remain = int(slot.get("harvestTime", 0)) - now_ms()
                if remain <= 0:
                    lines.append(f"田地{i}：{slot.get('seed','')}（成熟）")
                else:
                    lines.append(f"田地{i}：{slot.get('seed','')}（剩余{fmt_duration(remain)}）")
        if u.get("explorationType") and u.get("explorationStartTime"):
            cfg = VOYAGE_TYPES.get(u["explorationType"], VOYAGE_TYPES["近海远航"])
            remain = int(u["explorationStartTime"]) + cfg["duration"] - now_ms()
            lines.append(f"远航：{u['explorationType']}（{'剩余'+fmt_duration(remain) if remain > 0 else '已完成，点击刷新领取'}）")
        return "\n".join(lines)

    def plant(self, seed, amount):
        seed = str(seed).strip(); amount = int(amount)
        if STORE.get(seed, {}).get("type") != "seed": return "只能种植商店中的种子。"
        if amount < 1: return "数量必须大于0。"
        if int(self.user["warehouse"].get(seed, 0)) < amount: return f"{seed}不足。"
        empty = self._empty_fields()
        if len(empty) < amount: return f"空田不足，当前空田{len(empty)}块。"
        base_hours = random.random() * 3.5 + 0.5
        factor = WEATHER_GROWTH_FACTOR.get(self.weather, 1)
        # Match the original 20% random planting event.
        if random.random() <= 0.2:
            event = random.choice(PLANT_EVENTS)
            if event == "小精灵催熟" and self.user["level"] >= 3:
                self._remove(seed, amount)
                t = now_ms() + base_hours * 0.8 * 3600000 * factor
                for i in range(amount): self.user["crops"][f"田地{empty[i]}"] = {"seed": seed, "harvestTime": int(t), "stolen": False}
                msg = f"小精灵催熟了作物。成功种植{amount}块{seed}，成熟时间约{fmt_duration(base_hours*0.8*3600000)}。"
                self.save(); return msg
            if event == "女巫药水致死":
                self._remove(seed, amount); self.user["crops"] = {}
                comp = random.randint(50, 100); fert = random.randint(3, 6)
                self.user["money"] += comp; self._add("肥料", fert)
                self.save(); return f"实习女巫把药水洒到了田里，作物全没了。获得补偿：{comp}金币、肥料x{fert}。"
            if event == "狗熊压坏作物" and amount > 2:
                self._remove(seed, amount); t = now_ms() + base_hours * 3600000 * factor
                planted = list(empty[:amount])
                for idx in planted: self.user["crops"][f"田地{idx}"] = {"seed": seed, "harvestTime": int(t), "stolen": False}
                destroyed = min(random.randint(3, 5), amount)
                random.shuffle(planted)
                for idx in planted[:destroyed]: self.user["crops"].pop(f"田地{idx}", None)
                self.save(); return f"一只狗熊压坏了{destroyed}块作物。"
        self._remove(seed, amount)
        t = now_ms() + base_hours * 3600000 * factor
        for i in range(amount): self.user["crops"][f"田地{empty[i]}"] = {"seed": seed, "harvestTime": int(t), "stolen": False}
        self.save(); return f"已种植{amount}块{seed}，成熟时间约{fmt_duration(base_hours*3600000*factor)}。"

    def harvest(self):
        self._process_voyage()
        # Original 5% adventurer event when harvesting.
        if random.random() < 0.05:
            mature = [k for k,v in self.user["crops"].items() if int(v.get("harvestTime",0)) <= now_ms() and not v.get("stolen")]
            if mature:
                take = random.sample(mature, min(random.randint(1,2), len(mature)))
                for k in take: self.user["crops"].pop(k, None)
                comp = random.randint(50,100); seed = random.choice([x for x in STORE if x.endswith("种子")]); n=random.randint(3,5)
                self.user["money"] += comp; self._add(seed,n); self.save()
                return f"冒险者采走了部分成熟作物。获得补偿：{comp}金币、{seed}x{n}。"
        products = {}
        count = 0
        for k in list(self.user["crops"]):
            v = self.user["crops"][k]
            if int(v.get("harvestTime",0)) <= now_ms():
                product = self._crop_output(v.get("seed", "")); products[product] = products.get(product,0)+1; count += 1; del self.user["crops"][k]
        if not count: return "当前没有成熟作物。"
        for k,v in products.items(): self._add(k,v)
        gain=random.randint(100,200); self.user["experience"] += gain; ups=self._sync_level(); self.save()
        detail="、".join(f"{k}x{v}" for k,v in products.items())
        return f"收获完成：{detail}。经验+{gain}" + (f"，升级至{self.user['level']}级" if ups else "")

    def buy(self, item, amount=1):
        if item not in STORE: return "商店没有这个商品。"
        info=STORE[item]; amount=max(1,int(amount))
        if self.user["level"] < info["level"]: return f"等级不足，需要{info['level']}级。"
        if info["type"] == "expand":
            if self.user["fields"] >= MAX_FIELDS: return f"已达到田地上限({MAX_FIELDS})。"
            if self.user["purchasedFields"].get(item): return "该扩容商品已购买过。"
            amount=1
        if info["type"] == "dog":
            if self.user.get("hasDog"): return "你已经拥有土狗。"
            amount=1
        cost=info["price"]*amount
        if self.user["money"] < cost: return f"金币不足，需要{cost}，当前{self.user['money']}。"
        self.user["money"]-=cost
        if info["type"] == "expand":
            self.user["fields"] += 1; self.user["purchasedFields"][item]=True
        elif info["type"] == "dog": self.user["hasDog"]=True
        else: self._add(item,amount)
        self.save(); return f"购买成功：{item} x{amount}。"

    def sell(self,item,amount=1):
        amount=max(1,int(amount)); have=int(self.user["warehouse"].get(item,0))
        if have<amount:return "仓库数量不足。"
        if item=="肥料":return "肥料不可出售。"
        if item in STORE and STORE[item]["type"]=="seed": price=int(STORE[item]["price"]*0.8)
        elif item=="鱼饵":price=int(STORE["鱼饵"]["price"]*0.5)
        elif item in FISH_PRICES:price=FISH_PRICES[item]
        else:
            seed=STORE.get(item+"种子")
            if not seed:return "该物品无可出售价格定义。"
            price=int(seed["price"]*1.25)
        self._remove(item,amount); income=price*amount; self.user["money"]+=income; self.save()
        return f"出售成功：{item} x{amount}，获得{income}金币。"

    def clear_field(self, index):
        key=f"田地{int(index)}"
        if int(index)<1 or int(index)>self.user["fields"]: return "田地序号无效。"
        if key not in self.user["crops"]: return "该田地为空。"
        del self.user["crops"][key]; self.save(); return f"{key}已铲除。"

    def fertilize(self,index):
        if not self._remove("肥料",1):return "肥料不足。"
        key=f"田地{int(index)}"
        if int(index)<1 or int(index)>self.user["fields"] or key not in self.user["crops"]:
            self._add("肥料",1); return "该田地为空。"
        now=now_ms(); remain=max(0,int(self.user["crops"][key]["harvestTime"])-now); self.user["crops"][key]["harvestTime"]=now+(remain+1)//2
        self.save(); return f"{key}已施肥，剩余时间减半。"

    def signin(self):
        if self.user.get("lastSignInDate")==today_str(): return f"今天已经签到过了。今日天气：{self.weather}"
        reward=random.randint(60,140); self.user["money"]+=reward; self.user["lastSignInDate"]=today_str(); self.save(); return f"签到成功，获得{reward}金币。今日天气：{self.weather}"

    def fish(self):
        self.refresh_daily()
        if int(self.user["warehouse"].get("鱼饵",0))<1:return "鱼饵不足，无法钓鱼。"
        if self.user["fishPond"]<=0:return "鱼塘资源不足，明天再来。"
        self._remove("鱼饵",1)
        if random.random()>=0.55:
            self.user["fishPond"]=max(0,self.user["fishPond"]-0.5);self.save();return f"这次没钓到鱼。鱼塘剩余：{self.user['fishPond']}"
        self.user["fishPond"]=max(0,self.user["fishPond"]-1);fish=random.choice(self._fish_pool());self._add(fish,1);self.save();return f"钓鱼成功，获得{fish}。鱼塘剩余：{self.user['fishPond']}"

    def worm(self):
        if self.user["level"]<4:return "等级不足，需达到4级。"
        if self.weather!="雨天":return "只有雨天才能抓蚯蚓。"
        if self.user.get("wormCatchCount",0)>=7:return "今天抓蚯蚓次数已达上限（7次）。"
        self.user["wormCatchCount"]+=1
        if random.random()<0.7:self._add("鱼饵",1);self.save();return f"抓蚯蚓成功，获得鱼饵x1。今日第{self.user['wormCatchCount']}次。"
        self.save();return f"这次没有抓到。今日第{self.user['wormCatchCount']}次。"

    def drop(self,item,amount=1):
        if not self._remove(item,int(amount)):return "仓库数量不足。"
        self.save();return f"已丢弃：{item} x{int(amount)}"

    def rename(self,name):
        name=str(name).strip()
        if not name:return "请输入农夫名。"
        self.user["name"]=name;self.save();return f"农夫名已修改为：{name}"

    def start_voyage(self,kind):
        self._process_voyage()
        if self.user.get("explorationType") and self.user.get("explorationStartTime"):
            cfg=VOYAGE_TYPES.get(self.user["explorationType"],VOYAGE_TYPES["近海远航"])
            remain=int(self.user["explorationStartTime"])+cfg["duration"]-now_ms()
            if remain>0:return f"你正在{self.user['explorationType']}中，剩余{fmt_duration(remain)}。"
        if kind not in VOYAGE_TYPES:return "探索类型不存在。"
        self.user["explorationType"]=kind;self.user["explorationStartTime"]=now_ms();self.user["explorationShipwreck"]=random.random()<SHIPWRECK_CHANCE[kind];self.save()
        return f"已开启{kind}，预计{VOYAGE_TYPES[kind]['duration']//60000}分钟后完成。"

    def _process_voyage(self):
        kind=self.user.get("explorationType"); start=self.user.get("explorationStartTime")
        if not kind or not start:return None
        cfg=VOYAGE_TYPES.get(kind)
        if not cfg:return None
        remain=int(start)+cfg["duration"]-now_ms()
        if remain>0:return None
        wreck=bool(self.user.get("explorationShipwreck"));self.user["explorationType"]=None;self.user["explorationStartTime"]=None;self.user["explorationShipwreck"]=False
        if wreck:
            self.save();return f"{kind}结束：因沉船事故，本次远航无收益。"
        money=random.randint(cfg["moneyMin"],cfg["moneyMax"]);exp=random.randint(cfg["expMin"],cfg["expMax"]);bait=random.randint(cfg["baitMin"],cfg["baitMax"])
        self.user["money"]+=money;self.user["experience"]+=exp
        if bait:self._add("鱼饵",bait)
        ups=self._sync_level();self.save()
        s=f"你的{kind}已完成，金币+{money}，经验+{exp}"
        if bait:s+=f"，鱼饵+{bait}"
        if ups:s+=f"，升级至{self.user['level']}级"
        return s

    def tick(self):
        msg=self._process_voyage()
        if msg:return msg
        return ""

    def close(self):
        self.save()

    # ---------------- UI ----------------
    def build_ui(self, host, layout):
        self.host=host
        self._widgets=[]
        top=QHBoxLayout();
        self.summary=QLabel(self.status_text());self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color:#333;font-size:13px;background:transparent;")
        top.addWidget(self.summary,1)
        refresh=QPushButton("刷新");refresh.clicked.connect(self._refresh);top.addWidget(refresh)
        layout.addLayout(top)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self._build_farm_tab();self._build_shop_tab();self._build_bag_tab();self._build_fish_tab();self._build_voyage_tab()
        self.msg=QLabel(self.last_message);self.msg.setWordWrap(True);self.msg.setStyleSheet("color:#555;background:transparent;")
        layout.addWidget(self.msg)
        self.timer=QTimer(self.host);self.timer.timeout.connect(self._timer_tick);self.timer.start(1000)

    def _button(self,text,fn):
        b=QPushButton(text);b.clicked.connect(fn);return b

    def _scroll_tab(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollBar:vertical{width:8px;background:transparent;} QScrollBar::handle:vertical{background:#888;border-radius:4px;}")
        scroll.setWidget(widget)
        return scroll

    def _build_farm_tab(self):
        w=QWidget();box=QVBoxLayout(w)
        box.setContentsMargins(10,10,14,10);box.setSpacing(9)
        grid=QGridLayout();grid.setHorizontalSpacing(7);grid.setVerticalSpacing(7);box.addLayout(grid)
        for i in range(1,self.user["fields"]+1):
            b=QPushButton();b.setMinimumHeight(54);b.clicked.connect(lambda _=False,n=i:self._field_action(n));grid.addWidget(b,(i-1)//3,(i-1)%3)
        self.field_grid=grid;self.field_widget=w
        row=QHBoxLayout();box.addLayout(row)
        self.seed_combo=QComboBox();self.seed_combo.setStyleSheet("QComboBox{background:white;color:#222;border:1px solid #bbb;border-radius:6px;padding:5px;} QComboBox QAbstractItemView{background:white;color:#222;selection-background-color:#e8e8e8;selection-color:#111;}");self._fill_seed_combo();row.addWidget(self.seed_combo,1)
        self.seed_count=QSpinBox();self.seed_count.setRange(1,30);self.seed_count.setValue(1);row.addWidget(self.seed_count)
        row.addWidget(self._button("种植",self._plant))
        row2=QHBoxLayout();box.addLayout(row2)
        row2.addWidget(self._button("一键收获",self._harvest));row2.addWidget(self._button("签到",self._signin));row2.addWidget(self._button("修改农夫名",self._rename))
        self.tabs.addTab(self._scroll_tab(w),"农田")
        self._update_fields()

    def _fill_seed_combo(self):
        self.seed_combo.clear()
        for k,v in STORE.items():
            if v["type"]=="seed":self.seed_combo.addItem(k)

    def _build_shop_tab(self):
        w=QWidget();box=QVBoxLayout(w)
        self.shop_list=QListWidget();box.addWidget(self.shop_list,1)
        row=QHBoxLayout();box.addLayout(row)
        self.shop_count=QSpinBox();self.shop_count.setRange(1,99);self.shop_count.setValue(1);row.addWidget(self.shop_count)
        row.addWidget(self._button("购买",self._buy));row.addWidget(self._button("出售选中",self._sell_selected))
        self.tabs.addTab(w,"商店")
        self._update_shop()

    def _build_bag_tab(self):
        w=QWidget();box=QVBoxLayout(w)
        self.bag_list=QListWidget();box.addWidget(self.bag_list,1)
        row=QHBoxLayout();box.addLayout(row)
        self.bag_count=QSpinBox();self.bag_count.setRange(1,999);self.bag_count.setValue(1);row.addWidget(self.bag_count)
        row.addWidget(self._button("丢弃选中",self._drop_selected));row.addWidget(self._button("出售选中",self._sell_selected_bag))
        self.tabs.addTab(self._scroll_tab(w),"仓库")
        self._update_bag()

    def _build_fish_tab(self):
        w=QWidget();box=QVBoxLayout(w)
        self.fish_info=QLabel();self.fish_info.setWordWrap(True);box.addWidget(self.fish_info)
        row=QHBoxLayout();box.addLayout(row)
        row.addWidget(self._button("钓鱼",self._fish));row.addWidget(self._button("抓蚯蚓",self._worm));row.addWidget(self._button("刷新鱼塘",self._refresh))
        self.tabs.addTab(self._scroll_tab(w),"钓鱼")
        self._update_fish()

    def _build_voyage_tab(self):
        w=QWidget();box=QVBoxLayout(w)
        box.setContentsMargins(10,10,14,10);box.setSpacing(9)
        self.voyage_info=QLabel();self.voyage_info.setWordWrap(True);self.voyage_info.setMinimumHeight(80);box.addWidget(self.voyage_info)
        self.voyage_combo=QComboBox();self.voyage_combo.addItems(list(VOYAGE_TYPES))
        self.voyage_combo.setStyleSheet("QComboBox{background:white;color:#222;border:1px solid #bbb;border-radius:6px;padding:5px;} QComboBox QAbstractItemView{background:white;color:#222;selection-background-color:#e8e8e8;selection-color:#111;}")
        box.addWidget(self.voyage_combo)
        box.addWidget(self._button("开始远航 / 领取",self._voyage))
        box.addStretch(1)
        self.tabs.addTab(self._scroll_tab(w),"远航")
        self._update_voyage()

    def _message(self,text):
        self.last_message=str(text);self.msg.setText(self.last_message);self._refresh()

    def _refresh(self):
        self.refresh_daily();self.summary.setText(self.status_text());self._update_fields();self._update_shop();self._update_bag();self._update_fish();self._update_voyage()

    def _timer_tick(self):
        msg=self.tick()
        if msg:self._message(msg)
        else:self.summary.setText(self.status_text());self._update_fields();self._update_voyage()

    def _update_fields(self):
        if not hasattr(self,'field_grid'):return
        while self.field_grid.count():
            item=self.field_grid.takeAt(0);widget=item.widget()
            if widget:widget.deleteLater()
        for i in range(1,self.user["fields"]+1):
            key=f"田地{i}";slot=self.user["crops"].get(key);b=QPushButton();b.setMinimumHeight(54)
            if not slot:text=f"田地{i}\n空"
            else:
                remain=int(slot.get("harvestTime",0))-now_ms();text=f"田地{i}\n{slot.get('seed','')}\n{'成熟' if remain<=0 else fmt_duration(remain)}"
            b.setText(text);b.clicked.connect(lambda _=False,n=i:self._field_action(n));self.field_grid.addWidget(b,(i-1)//3,(i-1)%3)

    def _update_shop(self):
        if not hasattr(self,'shop_list'):return
        self.shop_list.clear();lv=self.user["level"]
        for k,v in STORE.items():
            bought=self.user.get("purchasedFields",{}).get(k)
            if v["type"]=="expand" and bought:continue
            if v["type"]=="dog" and self.user.get("hasDog"):continue
            self.shop_list.addItem(f"{k}  |  {v['price']}金币  |  {v['level']}级" + ("  [不可用]" if lv<v["level"] else ""))

    def _update_bag(self):
        if not hasattr(self,'bag_list'):return
        self.bag_list.clear()
        for k,v in sorted(self.user["warehouse"].items()):self.bag_list.addItem(f"{k} x{int(v)}")

    def _update_fish(self):
        if hasattr(self,'fish_info'):
            self.fish_info.setText(f"天气：{self.weather}\n鱼塘资源：{self.user['fishPond']}\n鱼饵：{int(self.user['warehouse'].get('鱼饵',0))}\n可钓鱼等级：当前{self.user['level']}级")

    def _update_voyage(self):
        if not hasattr(self,'voyage_info'):return
        self._process_voyage();u=self.user;kind=u.get('explorationType')
        if kind and u.get('explorationStartTime'):
            cfg=VOYAGE_TYPES[kind];remain=int(u['explorationStartTime'])+cfg['duration']-now_ms();self.voyage_info.setText(f"当前远航：{kind}\n{'剩余'+fmt_duration(remain) if remain>0 else '已完成，点击领取'}\n沉船结果已在出发时决定。")
        else:self.voyage_info.setText("当前没有进行中的远航。\n近海30分钟 / 深海60分钟 / 远洋120分钟。")

    def _field_action(self,n):
        key=f"田地{n}"
        if key in self.user["crops"] and int(self.user["crops"][key].get('harvestTime',0))>now_ms():
            ans=QMessageBox.question(self.host,"田地操作",f"{key}正在生长。\n是否使用1个肥料减半剩余时间？",QMessageBox.Yes|QMessageBox.No)
            if ans==QMessageBox.Yes:self._message(self.fertilize(n))
        elif key in self.user["crops"]:self._message(self.harvest())
        else:self._message("该田地为空，请先选择种子并种植。")

    def _plant(self):self._message(self.plant(self.seed_combo.currentText(),self.seed_count.value()))
    def _harvest(self):self._message(self.harvest())
    def _signin(self):self._message(self.signin())
    def _rename(self):
        text,ok=QInputDialog.getText(self.host,"修改农夫名","新用户名：",text=self.user['name'])
        if ok:self._message(self.rename(text))
    def _buy(self):
        item=self.shop_list.currentItem()
        if not item:return
        name=item.text().split("  |")[0];self._message(self.buy(name,self.shop_count.value()))
    def _sell_selected(self):
        item=self.shop_list.currentItem()
        if not item:return
        name=item.text().split("  |")[0];self._message(self.sell(name,self.shop_count.value()))
    def _sell_selected_bag(self):
        item=self.bag_list.currentItem()
        if not item:return
        name=item.text().rsplit(" x",1)[0];self._message(self.sell(name,self.bag_count.value()))
    def _drop_selected(self):
        item=self.bag_list.currentItem()
        if not item:return
        name=item.text().rsplit(" x",1)[0];self._message(self.drop(name,self.bag_count.value()))
    def _fish(self):self._message(self.fish())
    def _worm(self):self._message(self.worm())
    def _voyage(self):self._message(self.start_voyage(self.voyage_combo.currentText()))
