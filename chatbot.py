import streamlit as st
from tools import AviationstackError
from agent import create_chat_session, create_client, send_prompt


def render_chatbot_app() -> None:
    if not st.runtime.exists():
        print("Use the Streamlit entry file: streamlit run main.py")
        return

    st.title("Airport Investment Agent")

    gemini_key = st.secrets.get("GEMINI_API_KEY")
    aviationstack_key = st.secrets.get("AVIATIONSTACK_KEY")
    if not gemini_key or not aviationstack_key:
        st.error(
            "Developer Error: GEMINI_API_KEY and AVIATIONSTACK_KEY "
            "are required in secrets."
        )
        st.stop()

    if "client" not in st.session_state:
        st.session_state.client = create_client(gemini_key)

    if "chat_session" not in st.session_state:
        st.session_state.chat_session = create_chat_session(
            st.session_state.client,
            aviationstack_key,
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me about an airport, for example LAX or SFO"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            try:
                response = send_prompt(st.session_state.chat_session, prompt)
                st.markdown(response.text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response.text}
                )
            except AviationstackError as e:
                st.error(f"Aviationstack error: {e}")
                st.stop()
            except RuntimeError as e:
                st.warning(str(e))
                st.session_state.messages.append(
                    {"role": "assistant", "content": str(e)}
                )
            except Exception as e:
                st.error(f"An error occurred while generating response: {e}")
                st.stop()
