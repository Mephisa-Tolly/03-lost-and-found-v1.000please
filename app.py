import streamlit as st
from datetime import date
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


def render_matches(results):
    if not results:
        st.info("暂无匹配候选。")
        return
    for r in results:
        item = r["item"]
        with st.container(border=True):
            st.subheader(f"{item['title']}  ·  {item['type']}")
            st.write(f"类别：{item['category']}　地点：{item['location']}　时间：{item['time']}")
            if item["sensitive_level"] == 1:
                st.write("描述：**敏感物品，关键细节不公开**")
            else:
                st.write(f"描述：{item['description']}")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("相似度", r["score"])
            with c2:
                st.metric("分级", r["level"])
            st.write("相似理由：" + ("；".join(r["reasons"]) if r["reasons"] else "无"))


@st.dialog("匹配候选 Top-3", width="large")
def match_dialog(title, results):
    st.write(f"【{title}】的匹配候选")
    render_matches(results)


@st.dialog("物品详情", width="large")
def detail_dialog(item):
    st.subheader(f"{item['title']}  ·  {item['type']}")
    st.write(f"类别：{item['category']}")
    st.write(f"地点：{item['location']}")
    st.write(f"时间：{item['time']}")
    if item["color"]:
        st.write(f"颜色：{item['color']}")
    if item["brand"]:
        st.write(f"品牌：{item['brand']}")
    if item["sensitive_level"] == 1:
        st.write("描述：**敏感物品，关键细节不公开**")
    else:
        st.write(f"描述：{item['description']}")
    st.write(f"状态：{item['status']}")

    st.divider()
    st.write("**申请认领**")
    applicant = st.text_input("你的姓名/昵称", key=f"ap_{item['item_id']}")
    answers = st.text_input("私密特征核验（必填，用于防冒领）", key=f"an_{item['item_id']}")
    if st.button("提交认领申请", key=f"sb_{item['item_id']}"):
        if not answers:
            st.error("必须填写私密特征核验")
            return
        add_claim(item["item_id"], applicant or "匿名申请人", answers)
        update_item_status(item["item_id"], "认领中")
        add_notification(item["created_by"] or "me", "认领申请",
                         f"有人申请认领《{item['title']}》，请查看核验。")
        st.success("认领申请已提交，状态已更新为【认领中】")


def page_home():
    st.header("首页")
    st.write("校园智能失物招领匹配系统 V1.0")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("寻物信息", len(list_items(item_type="寻物")))
    with col2:
        st.metric("招领信息", len(list_items(item_type="招领")))


def page_publish():
    st.header("发布信息")

    if st.session_state.get("show_match"):
        results = st.session_state.get("match_results", [])
        target_title = st.session_state.get("match_title", "")
        st.session_state["show_match"] = False
        match_dialog(target_title, results)

    with st.form("publish_form"):
        item_type = st.radio("类型", ["寻物", "招领"], horizontal=True)
        title = st.text_input("标题", placeholder="例如：丢失校园卡")
        category = st.selectbox("物品类别", CATEGORIES)
        location = st.text_input("丢失/拾获地点", placeholder="例如：图书馆一楼")
        d = st.date_input("日期", value=date.today())
        t = st.time_input("时间")
        color = st.text_input("颜色（选填）")
        brand = st.text_input("品牌（选填）")
        description = st.text_area("详细描述", placeholder="请描述物品特征")
        st.file_uploader("上传图片（选填）", accept_multiple_files=True)
        anonymous = st.checkbox("匿名发布")
        contact = st.text_input("联系方式（选填，默认隐藏）")
        private_features = st.text_input("私密特征（选填，仅用于认领核验）")
        submitted = st.form_submit_button("提交")

    if submitted:
        if not title or not location or not description:
            st.error("标题、地点、描述为必填项")
            return
        sensitive = 1 if category in SENSITIVE_CATEGORIES else 0
        data = {
            "type": item_type,
            "title": title,
            "category": category,
            "location": location,
            "time": f"{d} {t.strftime('%H:%M')}",
            "color": color,
            "brand": brand,
            "description": description,
            "images": "",
            "contact": contact,
            "anonymous": 1 if anonymous else 0,
            "sensitive_level": sensitive,
            "private_features": private_features,
            "created_by": "me",
        }
        add_item(data)
        st.success(f"已发布【{item_type}】：{title}")

        # 自动匹配
        results = match(data, list_items())
        
        # 🔴 双向匹配通知：给被匹配到的那条信息的发布者发通知
        for r in results:
            target_user = r["item"]["created_by"]
            if target_user and target_user != "me":  # 不给自己发
                add_notification(
                    target_user, 
                    "匹配命中", 
                    f"有新的【{item_type}】信息可能与您的《{r['item']['title']}》匹配，请查看。"
                )

        st.session_state["match_results"] = results
        st.session_state["match_title"] = title
        st.session_state["show_match"] = True
        st.rerun()


def page_pool():
    st.header("信息池")

    col1, col2, col3 = st.columns(3)
    with col1:
        f_type = st.selectbox("类型", ["全部", "寻物", "招领"], key="pool_type")
    with col2:
        f_category = st.selectbox("类别", ["全部"] + CATEGORIES, key="pool_cat")
    with col3:
        f_keyword = st.text_input("关键词", placeholder="搜索标题、描述、地点", key="pool_kw")

    item_type = None if f_type == "全部" else f_type
    rows = list_items(item_type=item_type, keyword=f_keyword or None)
    if f_category != "全部":
        rows = [r for r in rows if r["category"] == f_category]

    st.write(f"共 {len(rows)} 条")

    for r in rows:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.subheader(f"{r['title']}  ·  {r['type']}")
                st.write(f"类别：{r['category']}　地点：{r['location']}　时间：{r['time']}")
                if r["sensitive_level"] == 1:
                    st.write("描述：**该类别为敏感物品，关键细节不公开**")
                else:
                    st.write(f"描述：{r['description']}")
            with c2:
                st.write(f"状态：{r['status']}")
                if r["anonymous"] == 1:
                    st.write("匿名发布")
                
                # 🔴 新增：查看匹配候选按钮
                if st.button("查看匹配候选", key=f"m_{r['item_id']}"):
                    results = match(r, list_items())
                    match_dialog(r["title"], results)
                
                if st.button("查看详情", key=f"d_{r['item_id']}"):
                    detail_dialog(r)


def page_mine():
    st.header("我的")
    st.subheader("我的发布")
    mine = [r for r in list_items() if r["created_by"] == "me"]
    if not mine:
        st.write("暂无发布。")
    for r in mine:
        with st.container(border=True):
            st.write(f"**{r['title']}**  ·  {r['type']}  ·  状态：{r['status']}")
            if st.button("查看详情", key=f"md_{r['item_id']}"):
                detail_dialog(r)
            
            # 🔴 新增：认领批准逻辑
            if r["status"] == "认领中":
                claims = list_claims(item_id=r["item_id"])
                if claims:
                    st.write("---")
                    st.write("**待处理的认领申请：**")
                    for c in claims:
                        st.write(f"申请人：{c['applicant']}，核验答案：{c['answers']}")
                        if c["status"] == "待核验":
                            if st.button("✅ 批准认领", key=f"approve_{c['claim_id']}"):
                                update_claim_status(c["claim_id"], "已通过")
                                update_item_status(r["item_id"], "已确认")
                                add_notification(c["applicant"], "认领通过", f"您对《{r['title']}》的认领申请已通过，联系方式可见。")
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
            st.write(f"申请物品：**{title}**")
            st.write(f"核验答案：{c['answers']}")
            st.write(f"状态：{c['status']}")


def page_notifications():
    st.header("站内消息")
    notes = list_notifications()
    if not notes:
        st.write("暂无消息。")
    for n in notes:
        with st.container(border=True):
            st.write(f"**{n['type']}**：{n['content']}")
            st.write(f"时间：{n['created_at']}　{'已读' if n['read_flag'] else '未读'}")
            if not n["read_flag"]:
                if st.button("标记已读", key=f"rn_{n['notification_id']}"):
                    mark_notification_read(n["notification_id"])
                    st.rerun()


def page_eval():
    st.header("评测报告")
    st.write("运行 40 组评测集，验证匹配效果。")
    if st.button("运行评测"):
        with st.spinner("评测中..."):
            result = run_eval()
        st.json(result)


st.title("校园智能失物招领匹配系统")
st.write("V1.0 开发中")

st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["首页", "发布", "信息池", "我的", "消息", "评测"])

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
elif page == "评测":
    page_eval()
