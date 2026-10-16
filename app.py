import os
import json
import uuid
from pathlib import Path
from datetime import date, datetime

import streamlit as st
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

CATEGORIES = ["校园卡/学生证", "雨伞", "水杯", "耳机", "充电宝", "钥匙", "银行卡", "书本/文具", "其他"]
SENSITIVE_CATEGORIES = ["校园卡/学生证", "银行卡", "钥匙"]


def save_images(uploaded_files):
    if not uploaded_files:
        return ""
    paths = []
    for f in uploaded_files:
        ext = Path(f.name).suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            continue
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, "wb") as out:
            out.write(f.getbuffer())
        paths.append(fname)
    return json.dumps(paths, ensure_ascii=False)


def show_images(images_json, sensitive=False):
    if not images_json:
        return
    try:
        names = json.loads(images_json)
    except Exception:
        return
    if not names:
        return
    if sensitive:
        st.caption("🔒 敏感物品图片已隐藏，仅管理员审核后可见")
        return
    cols = st.columns(min(len(names), 3))
    for i, name in enumerate(names):
        full = os.path.join(UPLOAD_DIR, name)
        if os.path.exists(full):
            with cols[i % 3]:
                st.image(full, use_container_width=True)


# ---------- 弹窗：物品详情（包含匹配结果和认领） ----------
@st.dialog("物品详情", width="large")
def detail_dialog(item):
    # 🟢 彻底去掉星号，改用纯文本+换行
    st.markdown(f"# {item['title']}　·　{item['type']}")
    st.write("类别：", item['category'])
    st.write("地点：", item['location'])
    st.write("时间：", item['time'])
    
    if item.get("color"):
        st.write("颜色：", item['color'])
    if item.get("brand"):
        st.write("品牌：", item['brand'])

    if item["sensitive_level"] == 1:
        st.write("描述：该类别为敏感物品，关键细节不公开")
    else:
        st.write("描述：", item['description'])
        show_images(item.get("images", ""), sensitive=False)

    if item["anonymous"] == 1:
        st.caption("🔒 匿名发布，不展示发布者身份")

    st.divider()

    # 🟢 不再弹窗嵌套，直接展开匹配结果
    if st.button("🔍 查看匹配候选", key=f"detail_m_{item['item_id']}"):
        results = match(item, list_items())
        if not results:
            st.warning("暂无匹配候选。")
        else:
            st.subheader("匹配候选 Top-3")
            for i, r in enumerate(results):
                m_item = r["item"]
                with st.container(border=True):
                    st.write(f"候选 {i+1}　相似度 {r['score']}（{r['level']}）")
                    st.write(f"{m_item['title']} | {m_item['type']}")
                    st.write(f"相似理由：{'；'.join(r['reasons']) if r['reasons'] else '无'}")

    # 申请认领表单
    st.subheader("申请认领")
    applicant = st.text_input("你的姓名/昵称", key=f"ap_{item['item_id']}")
    answers = st.text_input("私密特征核验（必填，用于防冒领）", key=f"an_{item['item_id']}")
    
    if st.button("提交认领申请", key=f"sb_{item['item_id']}"):
        if not answers:
            st.error("必须填写私密特征核验")
        else:
            add_claim(item["item_id"], applicant or "匿名申请人", answers)
            update_item_status(item["item_id"], "认领中")
            add_notification(item["created_by"] or "me", "认领申请",
                             f"有人申请认领《{item['title']}》，请查看核验。")
            st.success("认领申请已提交，状态更新为【认领中】")
            st.rerun()


# ---------- 弹窗：发布后的匹配提示 ----------
@st.dialog("匹配候选 Top-3", width="large")
def match_dialog(title, results):
    st.subheader(f"【{title}】的匹配候选")
    st.info("以下为系统推荐候选，请人工确认，系统不会自动判定归属。")
    if not results:
        st.warning("暂无匹配候选。")
        return
    for i, r in enumerate(results):
        item = r["item"]
        with st.container(border=True):
            st.write(f"候选 {i+1}　相似度 {r['score']}（{r['level']}）")
            st.write(f"{item['title']}  ·  {item['type']}")
            st.write(f"类别：{item['category']}　地点：{item['location']}　时间：{item['time']}")
            st.write("相似理由：" + ("；".join(r["reasons"]) if r["reasons"] else "无"))


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

    if st.session_state.get("show_match"):
        results = st.session_state.get("match_results", [])
        title = st.session_state.get("match_title", "")
        st.session_state["show_match"] = False
        match_dialog(title, results)

    with st.form("publish_form"):
        item_type = st.radio("类型", ["寻物", "招领"], horizontal=True)
        title = st.text_input("标题", placeholder="例如：丢失校园卡")
        category = st.selectbox("物品类别", CATEGORIES)
        location = st.text_input("丢失/拾获地点", placeholder="例如：图书馆一楼")
        d = st.date_input("日期", value=date.today())
        t = st.time_input("时间")
        color = st.text_input("颜色（选填）")
        brand = st.text_input("品牌（选填）")
        description = st.text_area("详细描述（至少填一项）", placeholder="请描述物品特征")
        uploaded = st.file_uploader(
            "拍照/上传图片（选填，支持 jpg/png）",
            type=["jpg", "jpeg", "png", "gif", "webp"],
            accept_multiple_files=True,
        )
        st.caption("提示：上传前请遮挡人脸、证件号与屏幕内容；敏感物品图片默认不公开展示。")
        anonymous = st.toggle("匿名发布")
        contact = st.text_input("联系方式（默认隐藏，核验通过后可见）")
        private_features = st.text_input("私密特征（选填，仅用于认领核验）")
        submitted = st.form_submit_button("提交发布")

    if submitted:
        if not title or not location or not description:
            st.error("标题、地点、描述为必填项")
            return
        sensitive = 1 if category in SENSITIVE_CATEGORIES else 0
        images_json = save_images(uploaded)
        data = {
            "type": item_type, "title": title, "category": category, "location": location,
            "time": f"{d} {t.strftime('%H:%M')}", "color": color, "brand": brand,
            "description": description, "images": images_json, "contact": contact,
            "anonymous": 1 if anonymous else 0, "sensitive_level": sensitive,
            "private_features": private_features, "created_by": "me",
        }
        add_item(data)
        st.success(f"已发布【{item_type}】：{title}")

        results = match(data, list_items())
        for r in results:
            target_user = r["item"]["created_by"]
            if target_user and target_user != "me":
                add_notification(target_user, "匹配命中",
                                 f"有新的【{item_type}】信息可能与您的《{r['item']['title']}》匹配，请查看。")

        st.session_state["match_results"] = results
        st.session_state["match_title"] = title
        st.session_state["show_match"] = True
        st.rerun()


# ---------- 页面：信息池 ----------
def page_pool():
    st.header("信息池")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        f_keyword = st.text_input("搜索关键词", placeholder="输入物品名称，如“保温杯”“校园卡”")
    with col2:
        f_type = st.selectbox("类型", ["全部", "寻物", "招领"])
    with col3:
        f_sort = st.selectbox("排序", ["时间倒序", "相关度"])

    item_type = None if f_type == "全部" else f_type
    rows = list_items(item_type=item_type, keyword=f_keyword or None)

    st.write(f"共 {len(rows)} 条结果")

    if not rows:
        st.warning("没有找到相关结果，请尝试更改关键词或发布新的寻物/招领信息。")
        return

    if "view_item" in st.session_state and st.session_state["view_item"]:
        detail_dialog(st.session_state["view_item"])

    for r in rows:
        with st.container(border=True):
            st.subheader(f"{r['title']}　·　{r['type']}")
            st.write(f"类别：{r['category']}　|　地点：{r['location']}　|　时间：{r['time']}")
            st.write(f"状态：{r['status']}")
            
            if st.button("🔍 查看详情并认领", key=f"view_{r['item_id']}", use_container_width=True):
                st.session_state["view_item"] = r
                st.rerun()


# ---------- 页面：我的 ----------
def page_mine():
    st.header("我的记录")

    st.subheader("我的发布")
    mine = [r for r in list_items() if r["created_by"] == "me"]
    if not mine:
        st.write("暂无发布。")
    for r in mine:
        with st.container(border=True):
            st.subheader(f"{r['title']}　·　{r['type']}")
            st.write(f"状态：{r['status']}")

            if r["sensitive_level"] == 1:
                st.caption("🔒 敏感物品，图片默认不公开")
            else:
                show_images(r.get("images", ""), sensitive=False)

            if r["status"] == "认领中":
                st.info("认领进度：已有申请人，待您确认 → 管理员二次核验 → 发放联系方式")
                claims = list_claims(item_id=r["item_id"])
                if claims:
                    for c in claims:
                        st.write(f"申请人：{c['applicant']}　|　核验答案：{c['answers']}")
                        if c["status"] == "待核验":
                            if st.button("✅ 批准认领", key=f"approve_{c['claim_id']}"):
                                update_claim_status(c["claim_id"], "已通过")
                                update_item_status(r["item_id"], "已确认")
                                add_notification(c["applicant"], "认领通过",
                                                 f"您对《{r['title']}》的认领申请已通过，联系方式可见。")
                                st.success("已批准！")
                                st.rerun()

    st.divider()
    st.subheader("我的申请")
    claims = list_claims()
    if not claims:
        st.write("暂无申请。")
    for c in claims:
        item = get_item(c["item_id"])
        title = item["title"] if item else f"物品{c['item_id']}"
        with st.container(border=True):
            st.write(f"申请物品：{title}")
            st.write(f"状态：{c['status']}")


# ---------- 页面：消息 ----------
def page_notifications():
    st.header("站内消息")
    notes = list_notifications()
    if not notes:
        st.write("暂无消息。")
    for n in notes:
        with st.container(border=True):
            st.write(f"{n['type']}：{n['content']}")
            st.caption(f"时间：{n['created_at']}　{'已读' if n['read_flag'] else '未读'}")
            if not n["read_flag"]:
                if st.button("标记已读", key=f"rn_{n['notification_id']}"):
                    mark_notification_read(n["notification_id"])
                    st.rerun()


# ---------- 页面：管理端 ----------
def page_admin():
    st.header("管理员台账")
    st.caption("仅管理员可见")

    tab1, tab2 = st.tabs(["快速登记", "台账列表"])
    with tab1:
        with st.form("admin_publish"):
            a_cat = st.selectbox("类别", CATEGORIES)
            a_loc = st.text_input("地点", value="上次登记地点：快递站")
            a_title = st.text_input("标题", placeholder="例如：捡到校园卡")
            a_desc = st.text_area("描述")
            a_uploaded = st.file_uploader(
                "拍照/上传图片（管理员登记可拍照上传）",
                type=["jpg", "jpeg", "png", "gif", "webp"],
                accept_multiple_files=True,
                key="admin_upload",
            )
            shelf = st.text_input("货架位置编码（选填，如 A-架-2）")
            if st.form_submit_button("保存台账并触发匹配"):
                images_json = save_images(a_uploaded)
                sensitive = 1 if a_cat in SENSITIVE_CATEGORIES else 0
                data = {
                    "type": "招领", "title": a_title, "category": a_cat, "location": a_loc,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "description": a_desc, "images": images_json,
                    "sensitive_level": sensitive, "created_by": "admin",
                }
                add_item(data)
                st.success("已登记入台账！系统已自动触发匹配。")

    with tab2:
        st.subheader("台账列表")
        rows = list_items(item_type="招领")
        for r in rows:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(r['title'])
                    st.write(f"类别：{r['category']}　地点：{r['location']}　时间：{r['time']}")
                    st.write(f"描述：{r['description']}")
                with c2:
                    st.write(f"状态：{r['status']}")
                    st.write(f"经办：{r['created_by']}")
                show_images(r.get("images", ""), sensitive=False)


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
