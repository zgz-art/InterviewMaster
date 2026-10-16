import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from src.resume_parser import extract_text_from_pdf
from src.llm_client import generate_questions, score_answer, generate_final_report
from src.speech import transcribe_audio, text_to_speech
from src.video_utils import InterviewVideoProcessor

st.set_page_config(page_title="AI 面试官", page_icon="🎯", layout="wide")

# ---------- 状态初始化 ----------
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_q = 0
    st.session_state.scores = []
    st.session_state.answers = []
    st.session_state.interview_done = False
    st.session_state.report = None

st.title("🎯 AI 面试官")
st.caption("金融行业软件外包公司 · 内部面试工具")

# ---------- 侧边栏：简历录入 ----------
with st.sidebar:
    st.header("📄 简历录入")
    uploaded = st.file_uploader("上传简历 PDF", type=["pdf"])
    jd_text = st.text_area("或粘贴职位描述/简历文本", height=150)

    if st.button("🚀 生成面试题", use_container_width=True):
        resume_text = ""
        if uploaded:
            resume_text = extract_text_from_pdf(uploaded.getvalue())
        elif jd_text:
            resume_text = jd_text
        if not resume_text:
            st.error("请先上传简历或粘贴文本")
        else:
            with st.spinner("AI 正在生成针对性面试题..."):
                questions = generate_questions(resume_text)
                st.session_state.questions = questions
                st.session_state.current_q = 0
                st.session_state.scores = []
                st.session_state.answers = []
                st.session_state.interview_done = False
                st.session_state.report = None
            st.success(f"已生成 {len(questions)} 道题")

# ---------- 主界面：双栏布局 ----------
col1, col2 = st.columns([3, 2])

with col1:
    st.header("🎙️ 面试问答")

    if not st.session_state.questions:
        st.info("请在左侧上传简历并生成面试题。")
    elif st.session_state.interview_done:
        st.success("✅ 面试已完成")
        if st.session_state.report:
            rpt = st.session_state.report
            st.subheader("📊 面评报告")
            st.write(rpt.get("overall", ""))
            st.write("**技术亮点：**", "；".join(rpt.get("strengths", [])))
            st.write("**待改进点：**", "；".join(rpt.get("improvements", [])))
    else:
        idx = st.session_state.current_q
        total = len(st.session_state.questions)
        st.progress(idx / total, text=f"第 {idx+1}/{total} 题")

        question = st.session_state.questions[idx]
        st.subheader(f"第 {idx+1} 题")
        st.write(question)

        # TTS 播报当前问题
        if st.button("🔊 语音播报问题", use_container_width=True):
            audio_path = text_to_speech(question)
            st.audio(audio_path, format="audio/mp3", autoplay=True)

        # 录音回答
        audio_bytes = st.audio_input("请回答（点击录制）", key=f"audio_{idx}")

        if audio_bytes and st.button("提交回答", type="primary", use_container_width=True):
            with st.spinner("正在识别语音..."):
                transcript = transcribe_audio(audio_bytes.getvalue())

            if not transcript:
                st.warning("未识别到有效语音，请重新录制")
            else:
                st.write("**识别内容：**", transcript)
                with st.spinner("AI 评分中..."):
                    result = score_answer(question, transcript)

                st.session_state.answers.append(transcript)
                st.session_state.scores.append(result)

                # 展示本题评分
                st.metric("本题得分", f"{result.get('score', 0)}/100")
                st.write("**评语：**", result.get("feedback", ""))

                # 判断是否追问
                if result.get("need_followup") and result.get("followup_question"):
                    st.session_state.questions.insert(idx + 1, result["followup_question"])
                    st.info(f"AI 追问：{result['followup_question']}")

                st.session_state.current_q += 1

                # 检查是否结束
                if st.session_state.current_q >= len(st.session_state.questions):
                    st.session_state.interview_done = True
                    with st.spinner("生成面评报告..."):
                        st.session_state.report = generate_final_report(
                            st.session_state.scores, st.session_state.questions
                        )
                st.rerun()

with col2:
    st.header("📹 视频监控")
    ctx = webrtc_streamer(
        key="interview-video",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=InterviewVideoProcessor,
        media_stream_constraints={"video": True, "audio": False},
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
    )
    if ctx.state.playing:
        st.caption("🔴 面试录制中 · 系统将定期抽帧存证")
    else:
        st.caption("点击 START 开启摄像头")

# ---------- 历史记录展开 ----------
if st.session_state.answers:
    with st.expander("📝 历史回答与评分"):
        for i, (ans, sc) in enumerate(zip(st.session_state.answers, st.session_state.scores)):
            st.write(f"**Q{i+1} 回答：** {ans}")
            st.write(f"得分：{sc.get('score', 'N/A')} · {sc.get('feedback', '')}")
