import streamlit as st
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=st.secrets["INTERN_API_KEY"],
    base_url=st.secrets["INTERN_API_BASE"]
)

st.set_page_config(
    page_title="银发法盾 - AI 法律文书助手",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ 银发法盾")
st.markdown("### AI 法律文书生成与咨询系统")
st.markdown("**专为中老年人打造的法律助手**，简化复杂法律流程，提供清晰指引。")

with st.sidebar:
    st.header("功能说明")
    st.markdown("""
    **当前支持：**
    - 法律文书生成
    - 纠纷咨询分析
    
    **操作指南：**
    1. 在下方输入框描述您的法律问题
    2. 点击"开始分析"按钮
    3. 系统会生成法律建议和文书草案
    """)

st.subheader("📝 请输入您的法律问题")
user_prompt = st.text_area(
    "例如：我 65 岁了，有三个子女，他们都不愿意支付赡养费，我该怎么办？",
    height=150,
    placeholder="请详细描述您的法律问题和需求..."
)

model_option = st.selectbox(
    "选择生成模型",
    [
        "deepseek-v4.1-flash-1017", 
        "intern-s2", 
        "Atria-Dawn", 
        "Agents-A1", 
        "Sage-A1.5", 
        "glm-5.3", 
        "kimi-k2.6"
    ],
    index=0,
    help="调用时必须使用官方模型ID"
)

if st.button("🚀 开始分析", type="primary"):
    if not user_prompt.strip():
        st.error("⚠️ 请输入您的法律问题")
    else:
        st.info("🔄 正在分析，请稍候...")
        
        try:
            response = client.chat.completions.create(
                model=model_option,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的法律顾问和文书助手。请用通俗易懂的语言回答中老年人的法律疑问，并提供实用的法律建议。"
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            st.success("✅ 分析完成！")
            st.markdown("### 📋 法律建议")
            st.markdown(result)
            
            st.info("💡 提示：您可以将生成的内容保存为 Word 或 PDF 文档。如需进一步优化文书格式，请联系我们的技术团队。")
            
        except Exception as e:
            st.error(f"❌ 发生错误：{str(e)}")
            st.info("请检查：1. 网络连接；2. API Key 是否正确；3. 端砚平台是否正常运行")

st.markdown("---")
st.caption("© 2026 银发法盾开发团队 | 中国 - 东盟'AI+ 法律'应用创新大赛参赛作品")


