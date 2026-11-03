import streamlit as st
from openai import OpenAI
import re
import os
import base64
import io
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv

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
    model_option = st.selectbox("选择生成模型", 
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
    st.markdown("### 🚨 紧急维权热线")
    st.markdown("📞 [法律援助热线 12348](tel:12348)")
    st.markdown("📞 [消费者投诉热线 12315](tel:12315)")
    st.markdown("🚨 [紧急报警 110](tel:110)")
    st.caption("注：手机端点击可直接拨号，电脑端需配合电话软件。")
    
    st.markdown("---")
    st.markdown("**🛠️ 功能开关：**")
    show_template_guide = st.checkbox("显示案情引导模板", value=True)
    show_qa_guide = st.checkbox("显示Q&A话术总结", value=True)

with st.sidebar:
    if show_qa_guide:
        with st.expander("💬 Q&A 话术总结"):
            st.markdown("""
            * **开场引导**："老人家，您先别慌，把事情的经过从头到尾说一遍。"
            * **按时间说**："您按时间顺序讲：最早是什么时候？中间发生了什么？"
            * **确认证据**："您有没有留下借条、合同、聊天记录、录音？"
            * **风险提示**："AI只能给您参考，建议您去咨询专业律师。"
            """)

# 分栏：左侧输入，右侧输出
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📝 案情录入")
    st.info("💡 **不会打字？没关系！** 点击下方输入框，在手机键盘上找到 **🎤 麦克风图标**，按住直接说话。")
    
    if "case_input" not in st.session_state:
        st.session_state.case_input = ""

    if show_template_guide:
        st.markdown("**📋 试试这些模板（点击自动填入）：**")
        t_col1, t_col2 = st.columns(2)
        
        def update_input(text):
            st.session_state.case_input = text

        with t_col1:
            if st.button("💰 赡养纠纷", use_container_width=True, key="t1"):
                update_input("我65岁了，有三个子女。大儿子说没钱，二女儿说不想管，小儿子说别的哥哥姐姐先出。我退休金1500元，看病吃药要800元。我该怎么办？")
            if st.button("💳 消费维权", use_container_width=True, key="t2"):
                update_input("我在药店买了2万元的保健品，推销员说能治好我的高血压。现在吃了没用，想退钱，怎么办？")
        with t_col2:
            if st.button("🏠 遗产继承", use_container_width=True, key="t3"):
                update_input("我老伴去世了，留下一套房和10万存款。三个子女吵个不停，生前没立遗嘱，该怎么办？")
            if st.button("💵 民间借贷", use_container_width=True, key="t4"):
                update_input("3年前我借给老李5万块钱，有借条，现在要他还钱他说没钱，怎么办？")
    
    user_prompt = st.text_area("文字描述案情：", height=150, placeholder="例如：我 65 岁了，有三个子女，他们都不愿意支付赡养费...", key="case_input")
    
    uploaded_file = st.file_uploader("或上传案情图片/截图 (可选)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="已上传案情图", width=300)
        
    st.markdown("**🛠️ 高级功能配置：**")
    enable_compare = st.checkbox("开启【类案对比】", value=True)
    enable_ocr = st.checkbox("开启【图片OCR提取】", value=True)
    analyze_btn = st.button("🚀 生成法律意见", type="primary", use_container_width=True)

with col2:
    st.subheader("📋 法律意见书")
    if analyze_btn:
        if not user_prompt.strip() and uploaded_file is None:
            st.error("⚠️ 请输入案情或上传图片")
        else:
            try:
                system_content = """你是一位拥有20年经验的资深老龄权益律师。
请用最通俗易懂的拉家常语言解答。
如果必须提到法律专业术语，请立刻在括号里用大白话解释一遍。
请严格按【案情定性】【法律分析】【维权路径】【行动建议】四部分输出。"""
                
                if enable_compare:
                    system_content += "\n请额外增加第五部分【类案对比】：总结1-2个真实相似判例。"
                
                messages = [{"role": "system", "content": system_content}]
                
                if uploaded_file is not None and enable_ocr:
                    filename = uploaded_file.name.lower()
                    mime_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
                    with uploaded_file:
                        base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')
                    content_list = [
                        {"type": "text", "text": f"请根据图片分析。补充：{user_prompt}"},
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
                
                for chunk in response:
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            full_result += chunk.choices[0].delta.content
                            result_placeholder.markdown(full_result + "▌")
                
                result_placeholder.markdown(full_result)
                st.success("✅ 分析完成！")
                result = full_result
                
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
                st.warning("💡 **重要提示**：PDF中文可能显示不全，正式文书请下载 Word 版。")
            except Exception as e:
                st.error(f"❌ 发生错误：{str(e)}")
