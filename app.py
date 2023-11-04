import os
from lida import Manager, llm ,TextGenerationConfig
import openai
import streamlit as st
from dotenv import load_dotenv
from viz import get_data, handle_query

load_dotenv()


st.set_option("deprecation.showPyplotGlobalUse", False)
st.markdown("<h1 style='text-align: center; color:#FCF3CF '>Viz GPT</h1>", unsafe_allow_html=True)
# st.title("VizGPT",anchor=)

openai.api_key = os.getenv('OPENAI_API_KEY')

df = get_data()
if df is not None:
    st.write(df.head(100))
    column_names = ",".join(df.columns)
    text_gen = llm("openai")
    textgen_config = TextGenerationConfig(n=1, temperature=0.5, model="gpt-3.5-turbo-0301", use_cache=True)
    lida = Manager(text_gen = text_gen)
    df_summary = lida.summarize("filename.csv", summary_method="default", textgen_config=textgen_config)
    #df_summary ="Hi"
    print(df_summary)
    handle_query(df, df_summary, column_names)
    
