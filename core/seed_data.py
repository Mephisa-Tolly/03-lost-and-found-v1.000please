from core.db import init_db, add_item, get_conn


def seed():
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    conn.close()

    if count > 0:
        return

    samples = [
        {"type": "寻物", "title": "丢失校园卡", "category": "校园卡/学生证",
         "location": "图书馆一楼", "time": "2026-10-10 12:00",
         "color": "蓝色", "brand": "", "description": "蓝色卡套，学号尾号1234",
         "anonymous": 0, "sensitive_level": 1,
         "private_features": "卡套上贴了一张小熊贴纸", "created_by": "student_a"},
        {"type": "招领", "title": "捡到一张校园卡", "category": "校园卡/学生证",
         "location": "图书馆", "time": "2026-10-10 13:00",
         "color": "蓝色", "brand": "", "description": "在图书馆一楼自习区捡到一张校园卡，蓝色卡套",
         "anonymous": 1, "sensitive_level": 1,
         "private_features": "卡套上有卡通贴纸", "created_by": "student_b"},
        {"type": "寻物", "title": "丢失蓝牙耳机", "category": "耳机",
         "location": "教学楼A201", "time": "2026-10-11 09:00",
         "color": "白色", "brand": "AirPods", "description": "白色 AirPods，左耳丢了一只",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_a"},
        {"type": "招领", "title": "捡到一只耳机", "category": "耳机",
         "location": "教学楼", "time": "2026-10-11 10:00",
         "color": "白色", "brand": "AirPods", "description": "在A201捡到一只白色无线耳机",
         "anonymous": 1, "sensitive_level": 0, "created_by": "student_c"},
        {"type": "寻物", "title": "丢失保温杯", "category": "水杯",
         "location": "食堂二楼", "time": "2026-10-11 12:30",
         "color": "黑色", "brand": "膳魔师", "description": "黑色保温杯，杯身有划痕",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_a"},
        {"type": "招领", "title": "捡到一个水杯", "category": "水杯",
         "location": "食堂", "time": "2026-10-11 13:00",
         "color": "黑色", "brand": "膳魔师", "description": "食堂二楼捡到黑色保温杯",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_d"},
        {"type": "寻物", "title": "丢失充电宝", "category": "充电宝",
         "location": "快递站", "time": "2026-10-12 17:00",
         "color": "白色", "brand": "小米", "description": "白色小米充电宝，10000毫安",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_a"},
        {"type": "招领", "title": "捡到充电宝", "category": "充电宝",
         "location": "快递站门口", "time": "2026-10-12 18:00",
         "color": "白色", "brand": "小米", "description": "快递站捡到白色移动电源",
         "anonymous": 1, "sensitive_level": 0, "created_by": "student_e"},
        {"type": "寻物", "title": "丢失雨伞", "category": "雨伞",
         "location": "教学楼B103", "time": "2026-10-12 08:00",
         "color": "黑色", "brand": "", "description": "黑色折叠伞，伞柄有磨损",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_a"},
        {"type": "招领", "title": "捡到一把伞", "category": "雨伞",
         "location": "教学楼", "time": "2026-10-12 09:00",
         "color": "黑色", "brand": "", "description": "B103教室捡到黑色长柄伞",
         "anonymous": 0, "sensitive_level": 0, "created_by": "student_f"},
    ]

    for s in samples:
        add_item(s)

    print(f"已插入 {len(samples)} 条种子数据")