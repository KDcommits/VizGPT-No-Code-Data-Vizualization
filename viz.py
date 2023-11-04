import re
import openai
import pandas as pd
import streamlit as st

def handle_query(df, df_summary, column_names):
    query = st.text_area("Enter your question")

    if st.button("Get Answer"):
        if query and query.strip() !="":
            prompt_content = f"""
                The dataset is ALREADY loaded into a DataFrame named 'df'. DO NOT load the data again.
                The DataFrame has the following columns : {column_names}
                The DataFrame has the following summary : {df_summary}

                Befor plotting, ensure the data is ready by:
                1. Checking if the columns of the data represents the correct datatype. If not convert them to the proper datatype.
                2. Handle NaN values by replacing them with either mean or median or most frequenct categorical value.

                Use python packages Pandas and Mathplotlib ONLY for visualization.
                Provide SINGLE CODE BLOCK witha solution using Pandas and Matplotlib in a single figure to address the following query: {query}.

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


            with st.expander("**Display Python Code**🔻"):
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
                    #botmsg.write("Hi")
                    # for chunk in openai.ChatCompletion.create(
                    #     model= 'gpt-3.5-turbo',
                    #     messages=messages,

                    # ):
                    #     text = chunk.choices[0].get("delta",{}).get("content")
                    #     if text:
                    #         response.append(text)
                    #         result = "".join(response).strip()
                    #         botmsg.write(result)
            #st.write("Hi")
            execute_openai_code(llm_output,df, query)


def get_data():
    file_types = ['csv']
    data_upload = st.file_uploader("Upload a file", type = file_types)
    if data_upload:
        df= pd.read_csv(data_upload)
        return df 
    
    return None

def extract_code_from_markdown(md_text):
    code_blocks = re.findall(r"```(python)?(.*?)```", md_text, re.DOTALL)
    code = "\n".join([block[1].strip() for block in code_blocks])
    return code

def execute_openai_code(response_text, df, query):
    code = extract_code_from_markdown(response_text)
    if code:
        try:
            exec(code)
            st.pyplot()
        except Exception as e:
            st.error(str(e))



