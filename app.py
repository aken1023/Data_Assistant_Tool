import streamlit as st
import main

def title(word, font_size, bold=False, center=False):
    align = "center" if center else "left"
    bold_style = "font-weight: bold;" if bold else ""
    st.markdown(f"""
    <style>
    .title {{
        font-size: {font_size}px;
        text-align: {align};
        {bold_style}
        color: white;  
    }}
    </style>
    """, unsafe_allow_html=True)

    output = st.markdown(f'<div class="title">{word}</div>', unsafe_allow_html=True)
    return output

def sub_title(word, font_size, bold=False, center=True):
    align = "center" if center else "left"
    bold_style = "font-weight: bold;" if bold else ""
    st.markdown(f"""
    <style>
    .sub_title {{
        font-size: {font_size}px !important;
        text-align: {align};
        {bold_style}
        color: white;  
    }}
    </style>
    """, unsafe_allow_html=True)

    output = st.markdown(f'<p class="sub_title"><b>{word}</b></p>', unsafe_allow_html=True)
    return output

def app():
    with st.sidebar:
        st.image('Image\label.png', width=80)
        title('Planty Analyst', font_size=40,  bold=True)
        st.write("")

        with st.form(key='my_form'):
            form_name = st.text_input(label='Name', placeholder='Please enter your name',)
            form_id = st.text_input(label='Employee Number', placeholder='Please enter employee number')
            form_app = st.selectbox('App', ['Forest 2 - 專注森林', 'WaterDo - 水球清單', 'SleepTown - 沉默小鎮'])

            #調整間距
            for _ in range(3):
                st.write("")

            submit_button = st.form_submit_button(label='Submit')

            # 初始化參數
            if "name" not in st.session_state:
                st.session_state["name"] = ""
            if "login" not in st.session_state:
                st.session_state["login"] = ""

        if submit_button:
            if form_name.capitalize() in ["Jimmy"]:
                st.session_state["name"] = form_name.capitalize()
                st.session_state["login"] = 'success'
                st.success('Login successful!', icon="✅")
                
            else:
                st.error('No person found!!', icon="🚨")

    if st.session_state["login"] == "success":
        main.assistant() #驅動 Assistant

    else:
         # 使用 Markdown 顯示大字體的提示信息
        sub_title("Sign in for Access", font_size=50, bold=True, center=True)
        st.image(r"Image\background_new.png", width=700)

if __name__ == "__main__":
    app()