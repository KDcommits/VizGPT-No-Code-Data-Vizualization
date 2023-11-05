import os
import openai
import pandas as pd
from dotenv import load_dotenv
import mysql.connector as connection 

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
openai.api_key = os.getenv('OPENAI_API_KEY')

class SQLQuery:
    def __init__(self):
        self.DB_USERNAME = os.getenv('DB_USERNAME')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD')
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_PORT = os.getenv('DB_PORT')
        self.DB_NAME = os.getenv('DB_NAME')

    @property
    def databaseConnectionString(self):
        db_user = self.DB_USERNAME
        db_Password  = self.DB_PASSWORD
        db_host = self.DB_HOST + self.DB_PORT
        db_name = self.DB_NAME
        connectionString = f"mysql+pymysql://{db_user}:{db_Password}@{db_host}/{db_name}"
        return connectionString
    
    @property
    def databaseSQLSchema(self):
            ''''
                Extracting the schema info from the MySQL database and passing the schema 
                information to the prompt.
            '''
            sql_query = f"""  
            SELECT C.TABLE_NAME, C.COLUMN_NAME, C.DATA_TYPE, T.TABLE_TYPE, T.TABLE_SCHEMA  
            FROM INFORMATION_SCHEMA.COLUMNS C  
            JOIN INFORMATION_SCHEMA.TABLES T ON C.TABLE_NAME = T.TABLE_NAME AND C.TABLE_SCHEMA = T.TABLE_SCHEMA  
            WHERE T.TABLE_SCHEMA = '{self.DB_NAME}' 
            """ 
            mysql_connection_string = self.databaseConnectionString
            result = pd.read_sql_query(sql_query, mysql_connection_string)
            df = result.infer_objects()
            output=[]
            current_table = ''  
            columns = []  
            for index, row in df.iterrows():
                table_name = f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"  
                column_name = row['COLUMN_NAME']  
                data_type = row['DATA_TYPE']  
                if " " in table_name:
                    table_name= f"[{table_name}]" 
                column_name = row['COLUMN_NAME']  
                if " " in column_name:
                    column_name= f"[{column_name}]" 
                    # If the table name has changed, output the previous table's information  
                if current_table != table_name and current_table != '':  
                    output.append(f"table: {current_table}, columns: {', '.join(columns)}")  
                    columns = []  
                
                # Add the current column information to the list of columns for the current table  
                columns.append(f"{column_name} {data_type}")  
                
                # Update the current table name  
                current_table = table_name  

            # Output the last table's information  
            output.append(f"table: {current_table}, columns: {', '.join(columns)}")
            output = "\n ".join(output)

            return output       

    def getMYSQLConnectionObject(self):
        db_user = self.DB_USERNAME
        db_password  = self.DB_PASSWORD
        db_host = self.DB_HOST
        db_name = self.DB_NAME
        conn = connection.connect(host=db_host,user=db_user,password=db_password,
                                        database=db_name, use_pure=True) 
        if conn.is_connected():
            return conn
        else:
            return "Database connection can't be established"
    
    def defineFunction(self):
        database_schema_string = self.databaseSQLSchema
        function = [
            {
                "name": "ask_database",
                "description": "Use this function to answer user questions about product. Output should be a fully formed SQL query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": f"""
                                    SQL query extracting info to answer the user's question.
                                    SQL should be written using this database schema:
                                    {database_schema_string}
                                    The query should be returned in plain text, not in JSON.
                                    Do not use new lines chatacthers inside the query.
                                    If you are not able to find the answer only write "Found Nothing" in response.
                                    """,
                        }
                    },
                    "required": ["query"],
                },
            }
        ]
        return function
    
    def ask_database(self,query):
        """Function to query MySQL database with a provided SQL query."""
        try:
            conn = self.getMYSQLConnectionObject()
            # cursor=conn.cursor()   
            # cursor.execute(query)  
            # results = str(cursor.fetchall())
            # print(results)
            results  = pd.read_sql_query(query, conn)
            results.to_csv('filename.csv', index=False)
            if results.shape[0]<=100:
                conn.close()
                return str(results.values)
            else:
                return str(results.head(20).values)
        except Exception as e:
            results = f"query failed with error: {e}"
        
    
    def execute_function_call(self,message):
        if message["function_call"]["name"] == "ask_database":
            query = eval(message["function_call"]["arguments"])["query"]
            results = self.ask_database(query)
        else:
            results = f"Error: function {message['function_call']['name']} does not exist"
        return results
    
    def openai_functions_chain(self,query, function_calls,
                               gpt_model_name="gpt-3.5-turbo-0613"):
        messages = []
        messages.append({"role": "system", "content": "Answer user questions by generating SQL queries against the CanonDB Database."})
        messages.append({"role": "user", "content": query})
        while True:
            assistant_message = openai.ChatCompletion.create(
                temperature=0,
                model=gpt_model_name,
                messages=messages,
                functions=self.defineFunction(),
                function_call="auto",
            )["choices"][0]["message"]
            messages.append(assistant_message)

            if assistant_message.get("function_call"):
                print("Executing function: ", assistant_message["function_call"])
                function_calls.append(assistant_message["function_call"])
                results = self.execute_function_call(assistant_message)
                messages.append({"role": "function", "name": assistant_message["function_call"]["name"], "content": results})
            else:
                break

        return assistant_message['content'],function_calls
        

# question = "find the product names"
# sql_obj = SQLQuery()
# response = sql_obj.openai_functions_chain(question )
# print(response)