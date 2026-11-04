import streamlit as st
from openai import OpenAI
import re
import os
import base64
import io
import urllib.parse
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv
from gtts import gTTS
import requests
import sys
from pathlib import Path

# === 新增：导入你的爬虫模块，实现网页端直连 ===
try:
    _SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import download 
    HAS_CRAWLER = True
except Exception as e:
    HAS_CRAWLER = False
# ==========================================

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

# 侧边栏设置
with st.sidebar:
    st.header("系统设置")
    model_option = st.selectbox("选择生成模型", ["deepseek-v4.1-flash-1017", "intern-s2", "Atria-Dawn"], index=0)
    
    # === 新增：网页端法条直连开关 ===
    use_real_law = st.checkbox("🌟 开启【官方数据库法条直连】", value=HAS_CRAWLER, help="开启后，系统会在生成前先去人大网检索真实法规")
    # ================================

    st.markdown("---")
    st.markdown("**使用指南：**\n1. 输入文字或上传案情截图\n2. 等待AI出具法律意见\n3. 一键下载Word/PDF")
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
    *（如果长辈习惯说方言，可在手机输入法设置中开启"方言识别"，如粤语、四川话等，AI 一样能听懂哦！）*
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
        st.markdown("**💡 快捷分类按钮：**")
        left_col, right_col = st.columns(2)
        with left_col:
            st.button("💰 赡养纠纷", key="btn_sdyj")
            st.button("💳 消费维权", key="btn_xfwq")
        with right_col:
            st.button("🏠 遗产继承", key="btn_yjcc")
            st.button("💵 民间借贷", key="btn_mjwd")

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
                # === 新增：后台偷偷调用爬虫，获取真实法条 ===
                crawled_context = ""
                if use_real_law and HAS_CRAWLER and user_prompt.strip():
                    with st.spinner("正在直连国家法律法规数据库检索相关法条..."):
                        try:
                            # 简单提取前几个字作为搜索关键词（比如“赡养纠纷”）
                            search_keyword = user_prompt[:8]
                            search_res = download.search_laws(search_keyword, size=3)
                            if search_res and search_res.get("code") == 200:
                                rows = search_res.get("rows", [])
                                crawled_context = "\n【以下是从官方数据库实时抓取的相关法律法规名称】\n"
                                for row in rows[:3]:
                                    crawled_context += f"- {row.get('title')}\n"
                                crawled_context += "请务必结合以上真实存在的法规名称进行解答。\n"
                        except Exception as e:
                            print(f"爬虫检索超时: {e}")
                # ==========================================

                system_content = """你是一位拥有20年经验、极其耐心且亲切的资深老龄权益律师。
请用最通俗易懂的拉家常语言解答，绝对禁止堆砌长句。
如果必须提到法律专业术语，请立刻在括号里用大白话解释一遍。

请严格按以下结构输出：
【案情定性】
【法律分析】（必须明确列出对应的《民法典》或相关法律的具体法条序号及内容）
【维权路径】
【行动建议】

【核心任务：法条深度解读】
当您需要引用具体法条时，请：
1. 写出该法条的具体内容
2. 用大白话解释该法条的含义
3. 说明该法条适用于当前案情的原因
4. 列出其他可能适用的相关法条

【絮叨应对预案】
1. 始终保持耐心、尊重，不打断、不催促
2. 用一句话复述确认，让老人感到被倾听
3. 把长段话拆成小块，逐点确认
4. 当话题偏离时，用温和问句拉回案情
5. 不评判、不争论，避免使用命令式语气

【内置限制池】
1. 法律免责声明：必须明确告知用户，AI输出仅供参考，不构成律师法律意见。
2. 隐私保护：不主动索要、不保存用户敏感个人信息。
3. 紧急情况：发现紧急情况，优先建议拨打110、120。
4. 禁止承诺：不得承诺具体胜诉率、赔偿金额。
5. 证据边界：可提示常见证据类型，但不代替用户判断。
6. 地域差异：建议用户以当地法院、法援中心口径为准。
7. 多轮冗余：当用户反复陈述同一内容时，应复述确认后进入下一问题。
8. 绝对禁令：严禁编造案号、法院名称、裁判日期。若无法提供真实案号，请直接说明“暂无匹配到公开真实案号”，并仅描述裁判规则，不得虚构。"""
                
                # === 新增：把抓取到的法条塞进大模型的脑子里 ===
                if crawled_context:
                    system_content += crawled_context
                # =========================================
                
                if enable_compare:
                    system_content += "\n请额外增加第五部分【类案对比】：总结1-2个最高人民法院或地方法院的真实相似判例，说明法院的裁判规则。若无法提供真实案号，请直接说明“暂无匹配到公开真实案号”，不得虚构。"
                
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
                
                response = client.chat.completions.create(model=model_option, messages=messages, temperature=0.3, stream=True)
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
                
                # 语音朗读（增加超时与异常处理）
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
                
                # 导出
                st.markdown("### 📥 导出法律意见书")
                export_col1, export_col2 = st.columns(2)
                doc = Document()
                doc.add_heading('银发法盾 - AI法律意见书', 0)
                doc.add_paragraph(result)
                bio = io.BytesIO()
                doc.save(bio)
                export_col1.download_button(label="下载 Word 版 (推荐)", data=bio.getvalue(), file_name="法律意见书.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                
                # PDF导出（使用fpdf2加载中文字体）
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.add_font("yahei", "", "msyh.ttc", uni=True) 
                    pdf.set_font("yahei", size=12)
                    pdf.multi_cell(0, 10, result)
                    pdf_output = bytes(pdf.output(dest="S")) 
                    export_col2.download_button(label="下载 PDF 版 (预览用)", data=pdf_output, file_name="法律意见书.pdf", mime="application/pdf", use_container_width=True)
                    st.caption("💡 提示：PDF预览版仅供快速查阅，正式文书请优先下载 Word 版。")
                except Exception as e:
                    st.error(f"PDF生成失败：{e}")
                
            except Exception as e:
                st.error(f"❌ 发生错误：{str(e)}")
                st.exception(e)

# ============================================
# 法条检索与验证
# ============================================
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
        st.caption("✅ 此文件可用 Word 2016 及以上版本打开")
    
    with citizen_col2:
        st.markdown("**📞 社区走访建议**")
        st.markdown("""
        **去哪里找居委会**：
        - 您所在的小区居委会办公室
        - 街道办事处（乡镇政府下辖）
        - 社区服务中心
        
        **带什么材料**：
        1. 身份证复印件
        2. 问题相关证据（照片、合同、聊天记录）
        3. 写好的情况说明（可用上方模板）
        
        **调解后的好处**：
        - 免费、高效的纠纷解决方式
        - 不伤和气，保留邻里关系
        - 若调解不成，仍可向法院起诉
        
        **注意事项**：
        - 居委会调解基于双方自愿原则
        - 调解协议具有法律约束力
        """)
