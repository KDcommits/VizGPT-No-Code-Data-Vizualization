import re
import os
import json
import openai
import pandas as pd
import streamlit as st
from sql import SQLQuery
from dotenv import load_dotenv
import mysql.connector as connection
from lida import Manager, llm ,TextGenerationConfig

load_dotenv()
function_calls = []

def get_data():
    file_types = ['csv']
    data_upload = st.file_uploader("**Upload a file**", type = file_types)
    if data_upload:
        df= pd.read_csv(data_upload)
        return df , data_upload.name
    
    return None, None


class GPTQuery:
    def __init__(self):
        self.query = st.sidebar.text_area("**Enter your question**")
        self.btn = st.sidebar.button("Get Answer")

    def extract_code_from_markdown(self,md_text):
        code_blocks = re.findall(r"```(python)?(.*?)```", md_text, re.DOTALL)
        code = "\n".join([block[1].strip() for block in code_blocks])
        return code

    def execute_openai_code(self,response_text, df):
        code = self.extract_code_from_markdown(response_text)
        if code:
            try:
                exec(code)
                #st.plotly_chart()
            except Exception as e:
                st.error(str(e))

    def handle_csv_query(self,df, df_summary, column_names):
        with st.sidebar.expander("**Display Data Summary**",expanded=False):
            st.sidebar.markdown("**Data Summary**")
            summ = st.sidebar.empty()
            summ.write(df_summary)

        if self.btn:
            if self.query and self.query.strip() !="":
                prompt_content = f"""
                    The dataset is ALREADY loaded into a DataFrame named 'df'. DO NOT load the data again.
                    The DataFrame has the following columns : {column_names}
                    The DataFrame has the following summary : {df_summary}

                    Befor plotting, ensure the data is ready by:
                    1. Checking if the columns of the data represents the correct datatype. If not convert them to the proper datatype.
                    2. Handle NaN values by replacing them with either mean or median or most frequenct categorical value.

                    Use python packages Pandas and Matplotlib ONLY for visualization.
                    Provide SINGLE CODE BLOCK witha solution using Pandas and Matplotlib in a single figure to address the following query: {self.query}.

                    - USE SINGLE CODE BLOCK with a solution.
                    - DO NOT EXPLAIN THE CODE.
                    - DO NOT COMMENT THE CODE
                    - ALWAYS WRAP THE CODE IN A SINGLE CODE BLOCK.
                    - The code block must end with ''' delimiter.
                    - Example code format '''code'''

                    - Colors to use for background and axes of the figure : #F0F0F6
                    """
                
                messages = [
                    {
                        'role':'system', 
                        'content':'You are a helpful data visualization assistant who gives the visualization code without explaining and commenting the code.'},
                    {
                        'role':'user',
                        'content':prompt_content
                    }
                ]


                with st.expander("**Show Python Code**",expanded=False):
                    with st.chat_message("assistant", avatar="🤖"):
                        botmsg = st.empty()
                        response = []
                        response = openai.ChatCompletion.create(
                        model ='gpt-3.5-turbo', 
                        messages = messages,
                        temperature=0,
                        )
                    
                        llm_output = response['choices'][0]['message']['content']
                        botmsg.write(llm_output)
                        
                self.execute_openai_code(llm_output,df)

    def handle_sql_query(self):
        if self.btn:
            if self.query and self.query.strip() !="":
                query = re.sub(r'\s+', ' ', self.query.lower())
                sql_obj =  SQLQuery()
                sql_response ="Hi"
                global function_calls
                sql_response, function_calls =  sql_obj.openai_functions_chain(query=query, 
                                                                               function_calls=function_calls)
                sql_query = eval(function_calls[0]['arguments'])['query']
                result_df = pd.read_csv('filename.csv').infer_objects()
                query_mask = (query.__contains__('plot')|
                              query.__contains__('draw')|
                              query.__contains__('chart')|
                              query.__contains__('graph')|
                              query.__contains__('visualize')|
                              query.__contains__('illustrate'))
                if (result_df.shape[0]>100) | query_mask:
                    text_gen = llm("openai")
                    textgen_config = TextGenerationConfig(n=1, temperature=0.5, model="gpt-3.5-turbo-0301", use_cache=True)
                    lida = Manager(text_gen = text_gen)
                    column_names = ",".join(result_df.columns)
                    df_summary = lida.summarize(data='filename.csv', summary_method="default", 
                                                textgen_config=textgen_config,n_samples=3)
                    self.handle_csv_query(result_df,df_summary,column_names)

                elif (query.__contains__('tabular')|(query.__contains__('table format'))):
                    with st.expander("",expanded=True):
                        st.markdown("<h5 style='text-align: left; font-size: 16px; color:#BDFEFB  '>SQL Response</h5>",unsafe_allow_html=True)
                        answer = st.empty()
                        answer.write(result_df)
                        st.markdown("<h5 style='text-align: left; font-size: 16px; color:#BDFEFB  '>SQL Query</h5>",unsafe_allow_html=True)
                        sql_query_ = st.empty()
                        sql_query_.write(sql_query)

                else:
                    with st.expander("",expanded=True):
                        st.markdown("<h5 style='text-align: left; font-size: 16px; color:#BDFEFB  '>SQL Response</h5>",unsafe_allow_html=True)
                        answer = st.empty()
                        answer.write(sql_response)
                        st.markdown("<h5 style='text-align: left; font-size: 16px; color:#BDFEFB  '>SQL Query</h5>",unsafe_allow_html=True)
                        sql_query_ = st.empty()
                        sql_query_.write(sql_query)

class Tables:
    def __init__(self):
        self.table_dir = os.path.join(os.getcwd(),'table_preview')

    def store_table(self):
        conn = connection.connect(host=os.getenv('DB_HOST'),user=os.getenv('DB_USERNAME'),
                                  password=os.getenv('DB_PASSWORD'),database=os.getenv('DB_NAME'), use_pure=True) 
        query = "show tables;"
        results  = pd.read_sql_query(query, conn)
        table_names = results.values.flatten().tolist()
        for table_name in table_names:
            query = f"select * from {table_name} limit 100"
            table_data  = pd.read_sql_query(query, conn)
            table_data = table_data.infer_objects()
            table_data.to_csv(f"table_preview//{table_name.lower()}.csv", index=False)

    def preview_table(self):
        csv_file_names = os.listdir(self.table_dir)
        table_names  = [csv_file_name.split('.csv')[0].title() for csv_file_name in csv_file_names]
        table_menu = st.sidebar.selectbox("**Choose Table**", table_names)
        for table_name in table_names:
            if table_menu==table_name:
                table_path = os.path.join(self.table_dir,table_name.lower()+'.csv')
                df = pd.read_csv(table_path)
                st.markdown(f"<h5 style='text-align: left; font-size: 16px; color:#FED6BD'>Table : {table_name}</h5>",unsafe_allow_html=True)
                
                st.write(df.head(100))
                return df, table_name
            
    def show_table_summary(self,table_name):
        table_path = os.path.join(self.table_dir,table_name+'.csv')
        text_gen = llm("openai")
        textgen_config = TextGenerationConfig(n=1, temperature=0.5, model="gpt-3.5-turbo-0301", use_cache=True)
        lida = Manager(text_gen = text_gen)
        df_summary = lida.summarize(data=table_path, summary_method="default", 
                                    textgen_config=textgen_config,n_samples=3)
        df_summary['name']= table_name+'.csv'
        df_summary['file_name'] =table_name+'.csv'
        with st.sidebar.expander("**Display Data Summary**",expanded=False):
            st.sidebar.markdown("**Data Summary**")
            summ = st.sidebar.empty()
            summ.write(df_summary)
