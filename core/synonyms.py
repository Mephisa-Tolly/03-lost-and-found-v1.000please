SYNONYM_GROUPS = {
    "校园卡": ["一卡通", "学生证", "饭卡", "校园卡"],
    "耳机": ["蓝牙耳机", "airpods", "AirPods", "无线耳机", "耳机"],
    "充电宝": ["移动电源", "电宝", "充电宝"],
    "雨伞": ["折叠伞", "长柄伞", "伞", "雨伞"],
    "水杯": ["保温杯", "马克杯", "杯子", "水杯"],
    "钥匙": ["钥匙串", "门钥匙", "宿舍钥匙", "车钥匙", "钥匙"],
    "银行卡": ["储蓄卡", "信用卡", "银行卡"],
    "书本": ["教材", "课本", "笔记本", "书本"],
    "身份证": ["身份证件", "身份证"],
    "书包": ["背包", "双肩包", "书包"],
    "充电器": ["充电头", "充电器"],  # 注意：不合并到充电宝
}

CATEGORY_GROUPS = {
    "证件类": ["校园卡/学生证", "银行卡"],
    "随身物品": ["雨伞", "水杯"],
    "电子设备": ["耳机", "充电宝"],
    "钥匙类": ["钥匙"],
    "其他": ["书本/文具", "其他"],
}

LOCATION_GROUPS = {
    "食堂": ["一食堂", "二食堂", "三食堂", "食堂", "餐厅", "清真餐厅"],
    "教学楼": ["教学楼", "教一", "教二", "教三", "A楼", "B楼", "C楼"],
    "图书馆": ["图书馆", "图书馆一楼", "图书馆二楼", "自阅室", "自习室"],
    "操场": ["操场", "体育场", "体育馆", "篮球场", "羽毛球场", "足球场"],
    "快递站": ["快递站", "菜鸟驿站", "快递点", "快递中心"],
    "宿舍区": ["宿舍", "男生宿舍", "女生宿舍", "公寓", "宿舍楼"],
    "校门口": ["校门", "东门", "西门", "南门", "北门"],
}

STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "那", "请问", "麻烦", "谢谢",
    "同学", "老师", "今天", "昨天", "刚刚", "好像", "大概", "可能",
    "应该", "希望", "有没有", "谁", "帮", "帮忙", "捡到", "丢失", "丢",
    "找到", "拾到", "失物", "招领",
])


def expand_text(text):
    if not text:
        return ""
    text = str(text)
    for standard, words in SYNONYM_GROUPS.items():
        for w in words:
            if w != standard:
                text = text.replace(w, standard)
    return text


def same_category(cat1, cat2):
    if cat1 == cat2:
        return True
    for group, cats in CATEGORY_GROUPS.items():
        if cat1 in cats and cat2 in cats:
            return True
    return False


def same_location(loc1, loc2):
    if not loc1 or not loc2:
        return True
    if loc1 == loc2:
        return True
    for group, locs in LOCATION_GROUPS.items():
        if any(l in loc1 for l in locs) and any(l in loc2 for l in locs):
            return True
    return False