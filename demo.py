import streamlit as st
from openai import OpenAI
import re
import os
from dotenv import load_dotenv

load_dotenv()

# 读取密钥，并使用正则表达式强制清除所有空格和换行符
try:
    raw_api_key = st.secrets["INTERN_API_KEY"]
    raw_base_url = st.secrets["INTERN_API_BASE"]
except Exception:
    raw_api_key = os.getenv('INTERN_API_KEY', '')
    raw_base_url = os.getenv('INTERN_API_BASE', '')

api_key = re.sub(r'\s+', '', raw_api_key)
base_url = raw_base_url.strip()

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=30.0  # 超时限制：最多等待30秒
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

st.subheader("🤖 选择 AI 模型")
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
                        "content": (
                            "你是一位拥有20年经验的资深老龄权益保护律师，同时也是一位极具耐心的倾听者。"
                            "你的服务对象是中老年人，他们可能不懂法律术语，或者正在遭受巨大的心理压力。\n\n"
                            "在回答时，请严格遵守以下原则：\n"
                            "1. **通俗易懂**：绝对不要堆砌复杂的法律术语，如果必须使用，请用大白话解释。\n"
                            "2. **充满温度**：先安抚当事人的情绪，再提供法律建议。\n"
                            "3. **精准引法**：在解答时，必须精准引用《中华人民共和国民法典》或《老年人权益保障法》的具体条文（如第1067条关于赡养费的规定）。\n"
                            "4. **结构化输出**：请严格按照以下四个模块输出答案：\n"
                            "   【案情定性】：用一句话告诉当事人这属于什么法律纠纷。\n"
                            "   【法律分析】：结合具体法条，解释为什么他是有理的。\n"
                            "   【维权路径】：给出明确的步骤（如：先协商 -> 找居委会调解 -> 去法院起诉）。\n"
                            "   【行动建议】：告诉当事人接下来需要收集哪些关键证据。\n"
                            "5. **安全底线**：明确告知当事人，AI仅提供参考，重大财产纠纷建议申请免费的法律援助。"
                        )
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
            st.exception(e)
            st.info("请检查：1. 网络连接；2. API Key 是否正确；3. 端砚平台是否正常运行")

st.markdown("---")
st.caption("© 2025 银发法盾开发团队 | 中国 - 东盟'AI+ 法律'应用创新大赛参赛作品")
