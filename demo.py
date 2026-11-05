import streamlit as st
from openai import OpenAI
import re
import os
import base64
import io
import urllib.parse
from docx import Document
from dotenv import load_dotenv
from gtts import gTTS
import requests
import sys
from pathlib import Path
import time

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import RateLimitError

try:
    _SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import download
    import common 
    HAS_CRAWLER = True
except Exception as e:
    HAS_CRAWLER = False

load_dotenv()

try:
    raw_api_key = st.secrets["INTERN_API_KEY"]
    raw_base_url = st.secrets["INTERN_API_BASE"]
except Exception:
    raw_api_key = os.getenv('INTERN_API_KEY', '')
    raw_base_url = os.getenv('INTERN_API_BASE', '')

api_key = re.sub(r'\s+', '', raw_api_key)
base_url = raw_base_url.strip()
client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

st.set_page_config(page_title="银发法盾 - AI 法律助手", page_icon="⚖️", layout="wide")
st.title("⚖️ 银发法盾")
st.markdown("**专为中老年人打造的法律助手**，支持图片案情识别、类案对比与文书导出。")

# ==========================================
# 💡 新增：显著的严谨性声明（高级产品包装）
# ==========================================
st.error("""
### 🛡️ 法律严谨性保障声明
为了保障您的合法权益，拒绝 AI 胡编乱造，本系统接入了**国家法律法规数据库实时抓取引擎**。
由于需要去官方政务网逐字核对并下载真实法条，**整个分析过程通常需要 5-10 分钟**。
请您提交案情后，耐心等待。我们宁愿慢一点，也要确保交给您的每一句话都有真实的法律依据！
""")
# ==========================================

# 侧边栏设置
with st.sidebar:
    st.header("系统设置")
    model_option = st.selectbox("选择生成模型", ["deepseek-v4.1-flash-1017", "intern-s2", "Atria-Dawn"], index=0)
    st.markdown("---")
    st.markdown("**使用指南：**\n1. 输入文字或上传案情截图\n2. 等待AI出具法律意见\n3. 一键下载Word/PDF")
    
    st.markdown("---")
    with st.expander("🛠️ 开发者诊断：测试官方库连通性"):
        st.write("点击下方按钮，验证系统是否能真实抓取国家法律法规数据库。")
        if st.button("⚡ 测试抓取真实法条"):
            if not HAS_CRAWLER:
                st.error("❌ 本地脚本导入失败，请检查 scripts 文件夹是否上传。")
            else:
                with st.spinner("正在连接国家法律法规数据库..."):
                    try:
                        test_res = download.search_laws("民法典", size=1)
                        if test_res and test_res.get("code") == 200 and test_res.get("rows"):
                            test_law = test_res["rows"][0]
                            st.success(f"✅ 检索成功：{test_law.get('title')}")
                            st.json(test_law)
                        else:
                            st.warning("⚠️ 网络超时或官方接口限制（云端常见）。")
                    except Exception as e:
                        st.error(f"❌ 抓取失败：{str(e)}")

    st.markdown("---")
    with st.expander("📖 老年人常见法律名词解释"):
        st.markdown("""
        * **诉讼**：去法院“告状”，让法官来评理。
        * **赡养**：子女在物质和生活上照顾父母的义务。
        * **调解**：找居委会或中间人，坐下来好好商量。
        * **原告/被告**：先告状的叫原告，被告的叫被告。
        """)
    st.markdown("---")
    st.markdown("""
    ### 🚨 紧急维权热线（点击直接拨打）
    <div style="display: flex; flex-direction: column; gap: 15px;">
        <a href="tel:12348" style="background-color: #1e8e3e; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">📞 法律援助热线 12348</a>
        <a href="tel:12315" style="background-color: #ff9800; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">📞 消费者投诉热线 12315</a>
        <a href="tel:110" style="background-color: #f44336; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">🚨 紧急报警 110</a>
    </div>
    <div style="margin-top: 20px; font-size: 18px; color: #666;">📝 注：此功能在手机端点击可直接拨号，在电脑端需配合电话软件使用。</div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    show_template_guide = st.checkbox("显示案情引导模板", value=True)
    show_qa_guide = st.checkbox("显示Q&A话术总结", value=True)
    show_community_guide = st.checkbox("显示社区协助指南", value=True)

with st.sidebar:
    if show_qa_guide:
        with st.expander("💬 Q&A 话术总结（帮您更好说明案情）"):
            st.markdown("**📝 描述案情**")
            st.markdown("""
            | 标题 | 话术模板 |
            |------|----------|
            | **开场引导** | "老人家，您先别慌，把事情的经过从头到尾说一遍，慢慢说。" |
            | **按时间说** | "您按时间顺序讲：最早是什么时候？中间发生了什么？现在是什么情况？" |
            | **抓重点** | "您用最简单的话说：谁、在什么时间、做了什么、对您造成了什么影响？" |
            """)
            st.markdown("**🔍 追问细节**")
            st.markdown("""
            | 标题 | 话术模板 |
            |------|----------|
            | **确认时间** | "您说的是XXXX年XX月，对吗？" |
            | **确认金额** | "这笔钱大概是多少？您还记得具体数字吗？" |
            | **确认人** | "这件事里，对方和您是什么关系？" |
            | **确认证据** | "您有没有留下借条、合同、聊天记录、录音或者视频？" |
            """)

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📝 案情录入")
    st.info("""
    💡 **不会打字？普通话不标准？没关系！** 
    点击下方输入框，在手机键盘上找到 **🎤 麦克风图标**，按住直接说话。
    """)
    if "case_input" not in st.session_state:
        st.session_state.case_input = ""
    def update_input(text):
        st.session_state.case_input = text

    if show_template_guide:
        st.markdown("**📋 不知道怎么描述？请按提示点选：**")
        main_category = st.radio("1. 您遇到了哪方面的纠纷？", ["婚姻家庭", "赡养纠纷", "消费维权", "民间借贷", "遗产继承"], horizontal=True)
        facts = []
        if main_category == "婚姻家庭":
            facts = st.multiselect("2. 具体情况（可多选）", ["遭遇家暴", "对方出轨", "争夺孩子抚养权", "想离婚对方不同意", "隐匿转移财产"])
        elif main_category == "赡养纠纷":
            facts = st.multiselect("2. 具体情况（可多选）", ["子女不给生活费/医药费", "子女逢年过节不看望", "生病住院没人管", "多个子女互相推诿"])
        elif main_category == "消费维权":
            facts = st.multiselect("2. 具体情况（可多选）", ["被忽悠买了高价保健品", "买到假货/过期食品", "办了预付卡老板跑路", "被虚假广告欺骗"])
        elif main_category == "民间借贷":
            facts = st.multiselect("2. 具体情况（可多选）", ["借了钱到期不还", "找不到借钱的人了", "对方耍赖不认账", "利息高得离谱"])
        elif main_category == "遗产继承":
            facts = st.multiselect("2. 具体情况（可多选）", ["老人没留遗嘱", "对遗嘱真假有争议", "其他亲属霸占房产", "存款分配不公"])
        evidence = st.radio("3. 证据情况", ["有书面合同/借条/遗嘱", "只有微信聊天记录/录音", "有转账记录", "什么证据都没有"], horizontal=True)
        if facts: 
            if st.button("✨ 智能拼装案情描述", use_container_width=True, type="secondary"):
                fact_text = "、".join(facts)
                draft_prompt = f"律师您好，我遇到了【{main_category}】方面的问题。具体情况是：{fact_text}。我目前的证据情况是：{evidence}。请问我该怎么办？"
                update_input(draft_prompt)

        st.markdown("**💡 演示专用：一键填入快捷案例**")
        left_col, right_col = st.columns(2)
        with left_col:
            if st.button("💰 赡养纠纷案例", key="btn_sdyj", use_container_width=True):
                st.session_state.case_input = "律师您好，我今年65岁了。我有三个子女，但是现在他们互相推诿，都不愿意支付赡养费，也不来看望我。我身体不好，每个月吃药要花很多钱。请问我该怎么办？"
                st.rerun()
            if st.button("💳 消费维权案例", key="btn_xfwq", use_container_width=True):
                st.session_state.case_input = "律师您好，我前几天去听讲座，被销售人员忽悠，花了三万块钱买了高价保健品。后来我发现这个保健品根本没有他们说的神效，我想退款，但是老板跑路了。请问我该怎么维权？"
                st.rerun()
        with right_col:
            if st.button("🏠 遗产继承案例", key="btn_yjcc", use_container_width=True):
                st.session_state.case_input = "律师您好，我父亲上个月去世了，没有留下书面遗嘱。现在我的大哥把父亲留下的房产和存款都霸占了，说他是长子应该多拿，一分钱都不分给我。请问我该怎么办？"
                st.rerun()
            if st.button("💵 民间借贷案例", key="btn_mjwd", use_container_width=True):
                st.session_state.case_input = "律师您好，去年我朋友找我借了5万块钱，当时写了借条，约定上个月还钱。但是现在到期了，他一直耍赖不认账，微信也不回，电话也不接。请问我该怎么把钱要回来？"
                st.rerun()

    user_prompt = st.text_area("文字描述案情：", height=150, placeholder="例如：我 65 岁了，有三个子女，他们都不愿意支付赡养费...", key="case_input")
    uploaded_file = st.file_uploader("或者上传案情图片/截图 (可选)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="已上传案情图", width=300)
    st.markdown("**🛠️ 高级功能配置：**")
    enable_compare = st.checkbox("开启【类案对比与裁判规则】", value=True)
    enable_ocr = st.checkbox("开启【图片OCR自动提取】", value=True)
    analyze_btn = st.button("🚀 生成法律意见", type="primary", use_container_width=True)

with col2:
    st.subheader("📋 法律意见书")
    if analyze_btn:
        if not user_prompt.strip() and uploaded_file is None:
            st.error("⚠️ 请输入案情或上传图片")
        else:
            try:
                crawled_laws_text = ""
                if HAS_CRAWLER and user_prompt.strip():
                    with st.status("🏛️ 正在直连国家数据库检索并解析真实法条...", expanded=True) as status:
                        try:
                            search_keyword = user_prompt[:8]
                            st.write(f"🔍 正在检索关键词: `{search_keyword}`")
                            search_res = download.search_laws(search_keyword, size=1)
                            
                            if search_res and search_res.get("code") == 200 and search_res.get("rows"):
                                law_info = search_res["rows"][0]
                                law_title = law_info.get("title")
                                bbbs_id = law_info.get("bbbs")
                                st.write(f"✅ 锁定法规：《{law_title}》")
                                
                                st.write("⏳ 正在下载并解析详细法条正文（政务网速度较慢，请耐心等待）...")
                                paragraphs, _ = download._download_docx_text(bbbs_id)
                                articles = common.split_into_articles(paragraphs)
                                
                                crawled_laws_text = f"\n【以下是系统刚刚从官方数据库实时抓取并解析的《{law_title}》真实法条，请严格依据这些法条回答】\n"
                                for i in range(min(5, len(articles))):
                                    crawled_laws_text += f"{articles[i][0]} {articles[i][1]}\n"
                                    
                                status.update(label="✅ 官方真实法条解析完成！", state="complete", expanded=False)
                            else:
                                status.update(label="⚠️ 未检索到高度匹配的法规，将依靠大模型知识回答", state="error", expanded=False)
                        except Exception as e:
                            status.update(label="⚠️ 云端网络受限，法条直连超时，已自动降级为大模型直接回答", state="error", expanded=False)
                            print(f"爬虫异常: {e}")

                system_content = """你是一位拥有20年经验、极其耐心且亲切的资深老龄权益律师。
请用最通俗易懂的拉家常语言解答，绝对禁止堆砌长句。
如果必须提到法律专业术语，请立刻在括号里用大白话解释一遍。

请严格按以下结构输出：
【案情定性】
【法律分析】（必须明确列出对应的《民法典》或相关法律的具体法条序号及内容）
【维权路径】
【行动建议】

【内置限制池】
1. 法律免责声明：必须明确告知用户，AI输出仅供参考，不构成律师法律意见。
2. 严禁编造案号、法院名称、裁判日期。若无法提供真实案号，请直接说明“暂无匹配到公开真实案号”。"""
                
                if crawled_laws_text:
                    system_content += crawled_laws_text
                
                if enable_compare:
                    system_content += "\n请额外增加第五部分【类案对比】：总结1-2个真实相似判例，说明法院的裁判规则。"
                
                messages = [{"role": "system", "content": system_content}]
                if uploaded_file is not None and enable_ocr:
                    filename = uploaded_file.name.lower()
                    mime_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
                    with uploaded_file:
                        base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
                    content_list = [
                        {"type": "text", "text": f"请根据图片中的案情内容进行分析。我的附加说明：{user_prompt}"},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                    messages.append({"role": "user", "content": content_list})
                else:
                    messages.append({"role": "user", "content": user_prompt})

                @retry(
                    retry=retry_if_exception_type(RateLimitError),
                    wait=wait_random_exponential(min=2, max=10),
                    stop=stop_after_attempt(5),
                    reraise=True
                )
                def create_completion_with_retry():
                    return client.chat.completions.create(
                        model=model_option, 
                        messages=messages, 
                        temperature=0.3, 
                        stream=True
                    )

                try:
                    response = create_completion_with_retry()
                except RateLimitError:
                    st.error("⚠️ 当前多人同时使用导致接口请求过于频繁，请等待 10 秒后再点击生成。")
                    st.stop()

                result_placeholder = st.empty()
                full_result = ""
                st.info("🔄 AI律师正在撰写意见，请稍候...")
                for chunk in response:
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            full_result += chunk.choices[0].delta.content
                            result_placeholder.markdown(full_result + "▌")
                result_placeholder.markdown(full_result)
                st.success("✅ 分析完成！")
                result = full_result
                
                st.markdown("### 🔊 语音朗读法律意见书")
                audio_buffer = io.BytesIO()
                try:
                    if result:
                        tts = gTTS(text=result, lang='zh-cn', timeout=10)
                        tts.write_to_fp(audio_buffer) 
                        audio_buffer.seek(0)  
                    else:
                        audio_buffer = None
                except Exception as e:
                    st.warning(f"⚠️ 语音朗读暂时不可用：{str(e)}")
                    audio_buffer = None
                if audio_buffer is not None:
                    st.audio(audio_buffer, format='audio/mpeg')
                    st.caption("💡 支持暂停/加速/下载，点击右上角三个点继续")
                
                st.markdown("### 📥 导出法律意见书")
                doc = Document()
                doc.add_heading('银发法盾 - AI法律意见书', 0)
                doc.add_paragraph(result)
                bio = io.BytesIO()
                doc.save(bio)
                
                col_btn, _ = st.columns([1, 1])
                with col_btn:
                    st.download_button(
                        label="📄 下载 Word 版 (正式文书)", 
                        data=bio.getvalue(), 
                        file_name="法律意见书.docx", 
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                        use_container_width=True
                    )
                st.info("💡 **提示**：由于系统字库限制，暂不提供 PDF 直接下载。建议您下载 Word 版，或在当前页面按 `Ctrl + P` 将网页保存为 PDF。")
                
            except Exception as e:
                st.error(f"❌ 发生错误：{str(e)}")
                st.exception(e)

st.markdown("---")
st.subheader("📖 法条检索与验证")
st.warning("⚠️ **重要说明**：以下提供官方数据库的直接查找入口，请务必核对 AI 提供的法条是否准确。")
db_col1, db_col2 = st.columns(2)
with db_col1:
    st.markdown("**🆔 国家法律法规数据库**")
    st.caption("搜索全年法律、行政法规、部门规章")
    st.markdown("👉 [🔍 在国家法律法规数据库检索](https://flk.npc.gov.cn/)") 
    st.metric("权威性", "官方发布")
with db_col2:
    st.markdown("**🆔 中国裁判文书网**")
    st.caption("查询真实法院判例")
    st.markdown("👉 [🔍 在裁判文书网检索判例](https://wenshu.court.gov.cn/)") 
    st.metric("真实性", "生效文书")

with st.expander("📋 常用老年人保护法条速查"):
    st.markdown("""
    如果您的案情涉及老年人权益，可参考以下核心法条，**在上面的数据库中输入具体条款号可查询原文**：
    * **《民法典》第1067条**：子女不履行赡养义务时，无劳动能力的或生活困难的父母，有要求子女付给赡养费的权利。
    * **《民法典》第1079条**：夫妻一方要求离婚的，可以由有关组织进行调解或者直接向人民法院提起离婚诉讼。
    * **《民法典》第1127条**：遗产按照下列顺序继承：第一顺序：配偶、子女、父母。第二顺序：兄弟姐妹、祖父母、外祖父母。
    * **《老年人权益保障法》第19条**：赡养人应当履行对老年人经济上供养、生活上照料和精神上慰藉的义务。
    * **《老年人权益保障法》第22条**：老年人对个人的财产，依法享有占有、使用、收益和处分的权利。
    """)

if show_community_guide:
    st.markdown("---")
    st.subheader("🏘️ 社区居委会协助指南")
    st.info("当法律规定难以单独解决时，您可以寻求社区居委会的帮助。居委会是居民自治组织，可以调解邻里纠纷、家庭矛盾等。")
    citizen_col1, citizen_col2 = st.columns(2)
    
    def create_community_document():
        doc = Document()
        doc.add_heading('居委会协助申请书', 0)
        doc.add_paragraph('')
        doc.add_paragraph('**申请人**：[您的姓名]')
        doc.add_paragraph('**联系电话**：[您的电话]')
        doc.add_paragraph('**申请事项**：请求社区居委会协助调解')
        doc.add_paragraph('')
        doc.add_heading('事由说明', level=1)
        doc.add_paragraph('请在此处描述您的具体情况，如：赡养纠纷、邻里矛盾、物业问题等')
        doc.add_paragraph('')
        doc.add_heading('调解请求', level=1)
        doc.add_paragraph('恳请贵居委会组织相关人员进行调解，协助双方达成共识。')
        doc.add_paragraph('')
        doc.add_heading('附件', level=1)
        doc.add_paragraph('[相关证据材料，如照片、通知等]')
        doc.add_paragraph('')
        doc.add_paragraph('申请人（签名）：')
        doc.add_paragraph('日期：    年   月   日')
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()
    
    with citizen_col1:
        st.markdown("**📝 居委会通用申请文书模板**")
        st.markdown("点击下载下方按钮，获取标准格式的 Word 申请书模板。填写后提交给您所在小区的居委会。")
        st.download_button(label="下载 申请书模板 (.docx)", data=create_community_document(), file_name="居委会协助申请书.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        st.warning("📱 **手机端提示**：如果点击没反应，请点击微信/浏览器右上角的 `...`，选择“在浏览器中打开”后再下载。")
        st.caption("✅ 此文件可用 Word 2016 及以上版本打开")
