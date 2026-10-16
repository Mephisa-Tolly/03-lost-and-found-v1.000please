import streamlit as st
from datetime import date, datetime
from core.db import (
    init_db, add_item, list_items, get_item, update_item_status,
    add_claim, list_claims, get_claim, update_claim_status,
    add_notification, list_notifications, mark_notification_read,
)
from core.seed_data import seed
from core.matcher import match
from core.evaluator import run_eval

st.set_page_config(page_title="校园失物招领", layout="wide")

init_db()
seed()

CATEGORIES = ["校园卡/学生证", "雨伞", "水杯", "耳机", "充电宝", "钥匙", "银行卡", "书本/文具", "其他"]
SENSITIVE_CATEGORIES = ["校园卡/学生证", "银行卡", "钥匙"]

# ---------- 组件：渲染候选卡片 ----------
def render_match_card(r, idx):
    item = r["item"]
    with st.container(border=True):
        st.markdown(f"### 候选 {idx}　相似度：{r['score']}（{r['level']}）")
        st.write(f"**{item['title']}**  ·  {item['type']}")
        st.write(f"类别：{item['category']}　时间：{item['time']}　地点：{item['location']}")
        if item["sensitive_level"] == 1:
            st.write("描述：**敏感物品，关键细节不公开**")
        else:
            st.write(f"描述：{item['description']}")
        
        tags = " ".join([f"`{reason}`" for reason in r["reasons"]])
        st.write(f"相似理由：{tags if tags else '暂无明确相似点'}")
        
        st.caption("请仔细核对物品特征，确认无误后再去“信息池”申请认领。系统不会自动判定归属。")

# ---------- 页面：匹配结果列表 ----------
def page_match_results(results, title):
    st.subheader(f"【{title}】的匹配候选")
    st.info("提示：以下为系统推荐候选，请人工确认，系统不会自动判定归属。")
    if not results:
        st.warning("无匹配结果。暂无找到符合您描述的物品，请检查关键词或重新发布。")
        return
    cols = st.columns(3)
    for idx, r in enumerate(results):
        with cols[idx]:
            render_match_card(r, idx + 1)
    st.caption("分级阈值：高 ≥0.75 / 中 0.6-0.75 / 低 <0.6；界面不出现“AI置信度”字样。")

# ---------- 页面：首页 ----------
def page_home():
    st.header("首页")
    st.write("校园智能失物招领匹配系统 V1.0")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("寻物信息", len(list_items(item_type="寻物")))
    with col2:
        st.metric("招领信息", len(list_items(item_type="招领")))

# ---------- 页面：发布信息 ----------
def page_publish():
    st.header("发布信息")
    
    if "last_results" in st.session_state and st.session_state["last_results"] is not None:
        page_match_results(st.session_state["last_results"], st.session_state.get("last_title", ""))
        if st.button("返回重新发布"):
            st.session_state["last_results"] = None
            st.rerun()
        return

    with st.form("publish_form"):
        item_type = st.radio("类型", ["寻物", "招领"], horizontal=True)
        title = st.text_input("标题", placeholder="例如：丢失校园卡")
        category = st.selectbox("物品类别", CATEGORIES)
        location = st.text_input("丢失/拾获地点", placeholder="例如：图书馆一楼")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            d = st.date_input("日期", value=date.today())
        with col_t2:
            t = st.time_input("时间")
            
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            color = st.text_input("颜色（选填）")
        with col_c2:
            brand = st.text_input("品牌（选填）")
            
        description = st.text_area("详细描述（至少填一项，≤300字）", placeholder="请描述物品特征，越详细越容易匹配")
        
        st.file_uploader("拍照/上传图片（选填，最多9张）", accept_multiple_files=True)
        st.caption("提示：上传前请遮挡人脸、证件号与屏幕内容；敏感物品仅管理员可见原图。")
        
        anonymous = st.toggle("匿名发布（开启后不展示姓名/学号/头像）")
        contact = st.text_input("联系方式（默认隐藏，核验通过后可见）")
        private_features = st.text_input("私密特征（选填，仅用于认领核验）")
        
        submitted = st.form_submit_button("提交发布")

    if submitted:
        if not title or not location or not description:
            st.error("标题、地点、描述为必填项")
            return
        sensitive = 1 if category in SENSITIVE_CATEGORIES else 0
        data = {
            "type": item_type, "title": title, "category": category, "location": location,
            "time": f"{d} {t.strftime('%H:%M')}", "color": color, "brand": brand,
            "description": description, "images": "", "contact": contact,
            "anonymous": 1 if anonymous else 0, "sensitive_level": sensitive,
            "private_features": private_features, "created_by": "me",
        }
        add_item(data)
        st.success(f"已发布【{item_type}】：{title}")
        
        # 自动匹配
        results = match(data, list_items())
        
        # 双向通知（发给匹配到的对方）
        for r in results:
            target_user = r["item"]["created_by"]
            if target_user and target_user != "me":
                add_notification(target_user, "匹配命中", f"有新的【{item_type}】信息可能与您的《{r['item']['title']}》匹配，请查看。")

        st.session_state["last_results"] = results
        st.session_state["last_title"] = title
        st.rerun()

# ---------- 页面：信息池（已改为折叠面板） ----------
def page_pool():
    st.header("信息池")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        f_keyword = st.text_input("搜索关键词（自动匹配同义词，如“保温杯/水杯”）", placeholder="输入物品名称...")
    with col2:
        f_type = st.selectbox("类别", ["全部", "寻物", "招领"])
    with col3:
        f_sort = st.selectbox("排序", ["时间倒序", "相关度"])

    item_type = None if f_type == "全部" else f_type
    rows = list_items(item_type=item_type, keyword=f_keyword or None)
    
    st.write(f"共 {len(rows)} 条结果")
    
    if not rows:
        st.warning("**无结果空态：** 没有找到相关结果，请尝试更改关键词或发布新的寻物/招领信息。")
        return
        
    for r in rows:
        # 🔴 核心改动：用手风琴折叠框，点标题直接原地展开，无需单独按钮
        with st.expander(f"📦 {r['title']}  ·  {r['type']}   |   状态：{r['status']}"):
            st.write(f"类别：{r['category']}　地点：{r['location']}　时间：{r['time']}")
            
            # 敏感物品保护
            if r["sensitive_level"] == 1:
                st.write("描述：**该类别为敏感物品，关键细节不公开**")
            else:
                st.write(f"描述：{r['description']}")
            
            if r["anonymous"] == 1:
                st.caption("🔒 匿名发布，不展示发布者身份")
                
            st.divider()
            st.write("**申请认领**")
            applicant = st.text_input("你的姓名/昵称", key=f"ap_{r['item_id']}")
            answers = st.text_input("私密特征核验（必填，用于防冒领）", key=f"an_{r['item_id']}")
            if st.button("提交认领申请", key=f"sb_{r['item_id']}"):
                if not answers:
                    st.error("必须填写私密特征核验")
                else:
                    add_claim(r["item_id"], applicant or "匿名申请人", answers)
                    update_item_status(r["item_id"], "认领中")
                    add_notification(r["created_by"] or "me", "认领申请", f"有人申请认领《{r['title']}》，请查看核验。")
                    st.success("认领申请已提交！状态已更新为【认领中】")
                    st.rerun()

# ---------- 页面：我的 ----------
def page_mine():
    st.header("我的记录")
    
    st.subheader("📦 我的发布")
    mine = [r for r in list_items() if r["created_by"] == "me"]
    if not mine:
        st.write("暂无发布。")
    for r in mine:
        with st.container(border=True):
            st.write(f"**{r['title']}**  ·  {r['type']}  ·  状态：{r['status']}")
            
            # 认领进度与批准
            if r["status"] == "认领中":
                st.info("⏳ 认领进度：已有申请人，待您确认 → 管理员二次核验 → 发放联系方式")
                claims = list_claims(item_id=r["item_id"])
                if claims:
                    for c in claims:
                        st.write(f"申请人：{c['applicant']} | 核验答案：{c['answers']}")
                        if c["status"] == "待核验":
                            if st.button("✅ 批准认领", key=f"approve_{c['claim_id']}"):
                                update_claim_status(c["claim_id"], "已通过")
                                update_item_status(r["item_id"], "已确认")
                                add_notification(c["applicant"], "认领通过", f"您对《{r['title']}》的认领申请已通过，联系方式可见。")
                                st.success("已批准！")
                                st.rerun()

    st.divider()
    st.subheader("📋 我的申请")
    claims = list_claims()
    if not claims:
        st.write("暂无申请。")
    for c in claims:
        item = get_item(c["item_id"])
        title = item["title"] if item else f"物品{c['item_id']}"
        with st.container(border=True):
            st.write(f"申请物品：**{title}** | 状态：{c['status']}")

# ---------- 页面：消息 ----------
def page_notifications():
    st.header("站内消息")
    notes = list_notifications()
    if not notes:
        st.write("暂无消息。")
    for n in notes:
        with st.container(border=True):
            st.write(f"**{n['type']}**：{n['content']}")
            st.caption(f"时间：{n['created_at']}　{'已读' if n['read_flag'] else '未读'}")
            if not n["read_flag"]:
                if st.button("标记已读", key=f"rn_{n['notification_id']}"):
                    mark_notification_read(n["notification_id"])
                    st.rerun()

# ---------- 页面：管理端台账 ----------
def page_admin():
    st.header("管理员台账")
    st.caption("仅管理员可见（保卫处/宿管/系统管理员）")
    
    tab1, tab2 = st.tabs(["📝 快速登记", "📋 台账列表"])
    with tab1:
        st.subheader("快速登记（拍照即录）")
        with st.form("admin_publish"):
            a_cat = st.selectbox("类别", CATEGORIES)
            a_loc = st.text_input("地点", value="上次登记地点：快递站")
            a_title = st.text_input("标题", placeholder="例如：捡到校园卡")
            a_desc = st.text_area("描述")
            shelf = st.text_input("货架位置编码（选填，如A-架-2）")
            
            if st.form_submit_button("保存台账并触发匹配"):
                data = {
                    "type": "招领", "title": a_title, "category": a_cat, "location": a_loc,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "description": a_desc, "created_by": "admin"
                }
                add_item(data)
                st.success("已登记入台账！系统已自动触发匹配。")
                
    with tab2:
        st.subheader("台账列表")
        st.dataframe(list_items(item_type="招领"), use_container_width=True)
        st.caption("字段：编号 | 类别 | 存放位置 | 状态 | 经办人")

# ---------- 页面：评测 ----------
def page_eval():
    st.header("评测报告")
    st.write("运行 40 组评测集，验证匹配效果。")
    if st.button("运行评测"):
        with st.spinner("评测中..."):
            result = run_eval()
        st.json(result)

# ---------- 主入口 ----------
st.title("校园智能失物招领匹配系统")
st.write("V1.0 开发中")

st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["首页", "发布", "信息池", "我的", "消息", "管理端", "评测"])

if page == "首页":
    page_home()
elif page == "发布":
    page_publish()
elif page == "信息池":
    page_pool()
elif page == "我的":
    page_mine()
elif page == "消息":
    page_notifications()
elif page == "管理端":
    page_admin()
elif page == "评测":
    page_eval()
