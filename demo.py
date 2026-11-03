import streamlit as st
from openai import OpenAI
import re
import os
import base64
import io
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv
from gtts import gTTS

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
    model_option = st.selectbox("选择生成模型 (建议选多模态模型)", 
        ["deepseek-v4.1-flash-1017", "intern-s2", "Atria-Dawn"], index=0)
    
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
        <a href="tel:12348" style="background-color: #1e8e3e; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">
            📞 法律援助热线 12348
        </a>
        <a href="tel:12315" style="background-color: #ff9800; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">
            📞 消费者投诉热线 12315
        </a>
        <a href="tel:110" style="background-color: #f44336; color: white; padding: 20px 40px; border-radius: 15px; text-align: center; font-size: 24px; text-decoration: none; display: block;">
            🚨 紧急报警 110
        </a>
    </div>
    <div style="margin-top: 20px; font-size: 18px; color: #666;">
    📝 注：此功能在手机端点击可直接拨号，在电脑端需配合电话软件使用。
    </div>
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

# 分栏：左侧输入，右侧输出
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📝 案情录入")
    
    st.info("""
    💡 **不会打字？普通话不标准？没关系！** 
    点击下方输入框，在手机键盘上找到 **🎤 麦克风图标**，按住直接说话。
    *（如果长辈习惯说方言，可在手机输入法设置中开启"方言识别"，如粤语、四川话等，AI 一样能听懂哦！）*
    """)
    
    # 初始化 session_state
    if "case_input" not in st.session_state:
        st.session_state.case_input = ""

    def update_input(text):
        st.session_state.case_input = text

    # 案件类型引导模板（升级版：三步漏斗式引导）
    if show_template_guide:
        st.markdown("**📋 不知道怎么描述？请按提示点选（我们会自动为您生成案情）：**")
        
        # 第一步：定性（大类）
        main_category = st.radio(
            "1. 您遇到了哪方面的纠纷？（单选）",
            ["婚姻家庭", "赡养纠纷", "消费维权", "民间借贷", "遗产继承"],
            horizontal=True
        )
        
        # 第二步：诉求与事实（小类多选）
        facts = []
        if main_category == "婚姻家庭":
            facts = st.multiselect("2. 具体发生了什么？（可多选）", ["遭遇家暴", "对方出轨", "争夺孩子抚养权", "想离婚对方不同意", "隐匿转移财产"])
        elif main_category == "赡养纠纷":
            facts = st.multiselect("2. 具体发生了什么？（可多选）", ["子女不给生活费/医药费", "子女逢年过节不看望", "生病住院没人管", "多个子女互相推诿"])
        elif main_category == "消费维权":
            facts = st.multiselect("2. 具体发生了什么？（可多选）", ["被忽悠买了高价保健品", "买到假货/过期食品", "办了预付卡老板跑路", "被虚假广告欺骗"])
        elif main_category == "民间借贷":
            facts = st.multiselect("2. 具体发生了什么？（可多选）", ["借了钱到期不还", "找不到借钱的人了", "对方耍赖不认账", "利息高得离谱"])
        elif main_category == "遗产继承":
            facts = st.multiselect("2. 具体发生了什么？（可多选）", ["老人没留遗嘱", "对遗嘱真假有争议", "其他亲属霸占房产", "存款分配不公"])

        # 第三步：证据情况
        evidence = st.radio(
            "3. 您手里有什么证据？（单选）",
            ["有书面合同/借条/遗嘱", "只有微信聊天记录/录音", "有转账记录", "什么证据都没有"],
            horizontal=True
        )

        # 第四步：一键生成草稿
        if facts: 
            if st.button("✨ 智能拼装案情描述", use_container_width=True, type="secondary"):
                fact_text = "、".join(facts)
                draft_prompt = f"律师您好，我遇到了【{main_category}】方面的问题。具体情况是：{fact_text}。我目前的证据情况是：{evidence}。请问我该怎么办？"
                update_input(draft_prompt)
    
    user_prompt = st.text_area("文字描述案情：", height=150, placeholder="例如：我 65 岁了，有三个子女，他们都不愿意支付赡养费...", key="case_input")
    
    uploaded_file = st.file_uploader("或者上传案情图片/截图 (可选)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="已上传案情图", width=300)
        
    st.markdown("**🛠️ 高级功能配置：**")
    enable_compare = st.checkbox("开启【类案对比与裁判规则】", value=True)
    enable_ocr = st.checkbox("开启【图片OCR自动提取】", value=True)
    
    analyze_btn = st.button("🚀 生成法律意见", type="primary", use_container_width=True)

# 右侧：法律意见书 + 新增功能
with col2:
    st.subheader("📋 法律意见书")
    
    if analyze_btn:
        if not user_prompt.strip() and uploaded_file is None:
            st.error("⚠️ 请输入案情或上传图片")
        else:
            try:
                system_content = """你是一位拥有20年经验、极其耐心且亲切的资深老龄权益律师。
请用最通俗易懂的拉家常语言解答，绝对禁止堆砌长句。
如果必须提到法律专业术语（如管辖权、诉讼时效），请立刻在括号里用大白话解释一遍。
请严格按【案情定性】【法律分析】【维权路径】【行动建议】四部分输出。

【絮叨应对预案】
1. 始终保持耐心、尊重，不打断、不催促
2. 用一句话复述确认，让老人感到被倾听
3. 把长段话拆成小块，逐点确认
4. 当话题偏离时，用温和问句拉回案情
5. 不评判、不争论，避免使用命令式语气

【内置限制池】
1. 法律免责声明：必须明确告知用户，AI输出仅供参考，不构成律师法律意见，重大案件请咨询执业律师或法律援助机构
2. 隐私保护：不主动索要、不保存用户身份证号、住址、银行卡等敏感个人信息
3. 紧急情况：发现用户人身安全受威胁、家暴、自杀等紧急情况时，优先建议拨打110、120或联系社区/家人
4. 禁止承诺：不得承诺具体胜诉率、赔偿金额、案件结果，仅可提供流程指引和风险提示
5. 证据边界：可提示常见证据类型，但不代替用户判断证据效力，不指导伪造、变造证据
6. 地域差异：法律适用存在地域差异，建议用户以当地律师、法院、法援中心口径为准
7. 多轮冗余：当用户反复陈述同一内容时，应复述确认后进入下一问题，避免无效循环"""
                
                if enable_compare:
                    system_content += "\n此外，请额外增加第五部分【类案对比】：总结1-2个最高人民法院或地方法院的真实相似判例，说明法院的裁判规则。"
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
                
                response = client.chat.completions.create(
                    model=model_option, 
                    messages=messages, 
                    temperature=0.5,
                    stream=True
                )
                result_placeholder = st.empty()
                full_result = ""
                st.info("🔄 AI律师正在撰写意见，请稍候...")
                
                # ================= 核心流式输出 (干净版) =================
                for chunk in response:
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            full_result += chunk.choices[0].delta.content
                            result_placeholder.markdown(full_result + "▌")
                # ============================================================
                
                result_placeholder.markdown(full_result)
                st.success("✅ 分析完成！")
                
                result = full_result
                
                # 语音朗读
                st.markdown("### 🔊 语音朗读法律意见书")
                audio_buffer = io.BytesIO()
                try:
                    tts = gTTS(text=result, lang='zh-cn')
                    tts.write_to_fp(audio_buffer)
                    audio_buffer.seek(0)
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
                export_col1.download_button(
                    label="下载 Word 版 (推荐)",
                    data=bio.getvalue(),
                    file_name="法律意见书.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 10, result.encode('latin-1', 'replace').decode('latin-1'))
                pdf_output = bytes(pdf.output(dest="S")) 
                
                export_col2.download_button(
                    label="下载 PDF 版 (预览用)",
                    data=pdf_output,
                    file_name="法律意见书.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.warning("💡 **重要提示**：由于 PDF 本地字库限制，中文可能显示不全。**正式法律文书请务必下载 Word 版**。")
                
            except Exception as e:
                st.error(f"❌ 发生错误：{str(e)}")
                st.exception(e)

# 社区居委会协助指南
if show_community_guide:
    st.markdown("---")
    st.subheader("🏘️ 社区居委会协助指南")
    st.info("""
    当法律规定难以单独解决时，您可以寻求社区居委会的帮助。居委会是居民自治组织，可以调解邻里纠纷、家庭矛盾等。
    """)
    
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
        st.markdown("""
        点击下载下方按钮，获取标准格式的 Word 申请书模板。  
        填写后提交给您所在小区的居委会。
        """)
        st.download_button(
            label="下载 申请书模板 (.docx)",
            data=create_community_document(),
            file_name="居委会协助申请书.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
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