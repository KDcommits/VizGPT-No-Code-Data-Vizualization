import os
import openai
import streamlit as st
from dotenv import load_dotenv
from viz import get_data, GPTQuery, Tables
from lida import Manager, llm ,TextGenerationConfig

load_dotenv()

st.set_option("deprecation.showPyplotGlobalUse", False)
st.markdown("<h1 style='text-align: center; color:#E8FEBD  '>Viz GPT</h1>", unsafe_allow_html=True)
# st.title("VizGPT",anchor=)

openai.api_key = os.getenv('OPENAI_API_KEY')

menu = st.sidebar.selectbox("**Choose an Option**", ["Upload your data", "Query existing data"])
if menu=="Upload your data":
    df,data_filename = get_data()
    if df is not None:
        st.write(df.head(100))
        column_names = ",".join(df.columns)
        text_gen = llm("openai")
        textgen_config = TextGenerationConfig(n=1, temperature=0.5, model="gpt-3.5-turbo-0301", use_cache=True)
        lida = Manager(text_gen = text_gen)
        df_summary = lida.summarize(data=data_filename, summary_method="default", 
                                    textgen_config=textgen_config,n_samples=3)
        #df_summary ="Hi"
        GPTQuery().handle_csv_query(df, df_summary, column_names)
        
elif menu=="Query existing data":
    table_obj = Tables()
    df , table_name =  table_obj.preview_table()
    query_obj = GPTQuery()
    table_obj.show_table_summary(table_name)
    query_obj.handle_sql_query()


    
